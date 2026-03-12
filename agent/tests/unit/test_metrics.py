"""Tests for MetricsCollector.

Requirement mapping:
- test_metrics_collector_initial_state -> Clean initialization
- test_on_metrics_* -> Per-turn metric capture
- test_get_latest_metrics_* -> Frontend overlay data
- test_session_summary_* -> Aggregate reporting

In livekit-agents 1.4.x, ``metrics_collected`` fires individual metric events
(STTMetrics, LLMMetrics, TTSMetrics, etc.).  The collector assembles a full
``TurnMetrics`` snapshot each time a TTS metric arrives (last pipeline stage).
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.metrics import _METRICS_TOPIC, MetricsCollector
from tests.conftest import _send_full_turn


class TestMetricsCollectorInitialState:
    def test_metrics_collector_initial_state(self, metrics_collector):
        assert metrics_collector.turn_metrics == []
        assert metrics_collector.session_id == "test-session"
        assert metrics_collector._current_turn == 0


class TestOnMetrics:
    def test_on_metrics_stores_turn(self, metrics_collector, mock_metrics_event):
        for event in mock_metrics_event:
            metrics_collector.on_metrics(event)
        assert len(metrics_collector.turn_metrics) == 1
        turn = metrics_collector.turn_metrics[0]
        assert turn.turn_number == 1
        assert turn.stt_ms == pytest.approx(250.0)
        assert turn.llm_ttft_ms == pytest.approx(220.0)
        assert turn.tts_ttfb_ms == pytest.approx(90.0)
        # total_e2e_ms is sum of stage timings: 250 + 220 + 90 = 560
        assert turn.total_e2e_ms == pytest.approx(560.0)

    def test_on_metrics_increments_turn_number(self, metrics_collector, mock_metrics_event):
        for _ in range(3):
            for event in mock_metrics_event:
                metrics_collector.on_metrics(event)
        turn_numbers = [t.turn_number for t in metrics_collector.turn_metrics]
        assert turn_numbers == [1, 2, 3]


class TestGetLatestMetrics:
    def test_get_latest_metrics_empty(self, metrics_collector):
        assert metrics_collector.get_latest_metrics() == {}

    def test_get_latest_metrics_returns_last(self, metrics_collector, mock_metrics_event):
        for _ in range(3):
            for event in mock_metrics_event:
                metrics_collector.on_metrics(event)
        latest = metrics_collector.get_latest_metrics()
        assert latest["turn"] == 3

    def test_get_latest_metrics_values_rounded(self, metrics_collector):
        _send_full_turn(
            metrics_collector,
            stt_duration=0.12345,
            llm_ttft=0.22222,
            tts_ttfb=0.09876,
        )
        latest = metrics_collector.get_latest_metrics()
        assert latest["stt_ms"] == 123.5
        assert latest["llm_ttft_ms"] == 222.2
        assert latest["tts_ttfb_ms"] == 98.8
        # total = 123.45 + 222.22 + 98.76 = 444.43 -> rounded to 444.4
        assert latest["total_e2e_ms"] == 444.4


class TestSessionSummary:
    def test_session_summary_empty(self, metrics_collector):
        assert metrics_collector.session_summary() == {}

    def test_session_summary_computes_stats(self, metrics_collector):
        for i in range(1, 11):
            # Vary the tts_ttfb so each turn has a different total e2e
            # total_e2e = (stt + llm + tts) * 1000
            # We want totals of 100ms, 200ms, ... 1000ms
            # With stt=0.0 and llm=0.0 and tts_ttfb = i * 0.1
            _send_full_turn(
                metrics_collector,
                stt_duration=0.0,
                llm_ttft=0.0,
                tts_ttfb=i * 0.1,
            )

        summary = metrics_collector.session_summary()
        assert summary["total_turns"] == 10
        assert summary["e2e_mean_ms"] == pytest.approx(550.0)
        assert summary["e2e_max_ms"] == pytest.approx(1000.0)
        assert summary["pct_under_500ms"] == pytest.approx(40.0)
        assert summary["pct_under_1000ms"] == pytest.approx(90.0)

    def test_session_summary_skips_zero_e2e(self, metrics_collector):
        # Add turns with zero and non-zero e2e
        for tts_val in [0.0, 0.5, 0.0, 0.3]:
            _send_full_turn(
                metrics_collector,
                stt_duration=0.0,
                llm_ttft=0.0,
                tts_ttfb=tts_val,
            )

        summary = metrics_collector.session_summary()
        # 4 turns recorded, but only 2 non-zero e2e values: 500ms and 300ms
        assert summary["total_turns"] == 4
        assert summary["e2e_mean_ms"] == pytest.approx(400.0)
        assert summary["e2e_max_ms"] == pytest.approx(500.0)


def _make_mock_room():
    """Create a mock Room with a local_participant that records publish_data calls."""
    room = MagicMock()
    room.local_participant = MagicMock()
    room.local_participant.publish_data = AsyncMock()
    return room


class TestPublishMetrics:
    """Tests for data channel publishing (async — create_task needs a running loop)."""

    @pytest.mark.asyncio
    async def test_publish_called_on_tts_event(self):
        """Completing a turn (TTS event) publishes metrics to the data channel."""
        room = _make_mock_room()
        collector = MetricsCollector(session_id="pub-test", room=room)

        _send_full_turn(collector, stt_duration=0.25, llm_ttft=0.22, tts_ttfb=0.09)
        await asyncio.sleep(0)  # let create_task fire

        room.local_participant.publish_data.assert_called_once()
        call_args = room.local_participant.publish_data.call_args
        payload = json.loads(call_args[0][0])

        assert payload["turn"] == 1
        assert payload["stt_ms"] == 250.0
        assert payload["llm_ttft_ms"] == 220.0
        assert payload["tts_ttfb_ms"] == 90.0
        assert payload["total_e2e_ms"] == 560.0
        assert call_args[1]["reliable"] is True
        assert call_args[1]["topic"] == _METRICS_TOPIC

    def test_publish_skipped_when_no_room(self):
        """Without a room reference, publishing is silently skipped."""
        collector = MetricsCollector(session_id="no-room")
        _send_full_turn(collector, stt_duration=0.25, llm_ttft=0.22, tts_ttfb=0.09)
        assert len(collector.turn_metrics) == 1

    @pytest.mark.asyncio
    async def test_publish_failure_does_not_crash_pipeline(self):
        """If publish_data raises, the turn is still recorded."""
        room = _make_mock_room()
        room.local_participant.publish_data.side_effect = RuntimeError("network down")
        collector = MetricsCollector(session_id="fail-test", room=room)

        _send_full_turn(collector, stt_duration=0.1, llm_ttft=0.1, tts_ttfb=0.1)
        await asyncio.sleep(0)

        assert len(collector.turn_metrics) == 1
        assert collector.turn_metrics[0].turn_number == 1

    @pytest.mark.asyncio
    async def test_publish_multiple_turns(self):
        """Each completed turn triggers a separate publish call."""
        room = _make_mock_room()
        collector = MetricsCollector(session_id="multi-test", room=room)

        for _ in range(3):
            _send_full_turn(collector, stt_duration=0.1, llm_ttft=0.1, tts_ttfb=0.1)
        await asyncio.sleep(0)

        assert room.local_participant.publish_data.call_count == 3

        for i, call in enumerate(
            room.local_participant.publish_data.call_args_list, 1
        ):
            payload = json.loads(call[0][0])
            assert payload["turn"] == i

    @pytest.mark.asyncio
    async def test_publish_payload_values_rounded(self):
        """Published payload values are rounded to 1 decimal place."""
        room = _make_mock_room()
        collector = MetricsCollector(session_id="round-test", room=room)

        _send_full_turn(
            collector, stt_duration=0.12345, llm_ttft=0.22222, tts_ttfb=0.09876
        )
        await asyncio.sleep(0)

        payload = json.loads(
            room.local_participant.publish_data.call_args[0][0]
        )
        assert payload["stt_ms"] == 123.5
        assert payload["llm_ttft_ms"] == 222.2
        assert payload["tts_ttfb_ms"] == 98.8
        assert payload["total_e2e_ms"] == 444.4
