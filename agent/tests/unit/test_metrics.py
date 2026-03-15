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
from tests.conftest import _make_eou_event, _make_stt_event, _send_full_turn, _make_llm_event, _make_tts_event


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
        # STT latency = stt_timestamp - eou_timestamp = 1.15 - 1.0 = 0.15s = 150ms
        assert turn.stt_ms == pytest.approx(150.0)
        assert turn.llm_ttft_ms == pytest.approx(220.0)
        assert turn.tts_ttfb_ms == pytest.approx(90.0)
        # total_e2e_ms is sum of stage timings: 150 + 220 + 90 = 460
        assert turn.total_e2e_ms == pytest.approx(460.0)

    def test_on_metrics_increments_turn_number(self, metrics_collector, mock_metrics_event):
        for _ in range(3):
            for event in mock_metrics_event:
                metrics_collector.on_metrics(event)
        turn_numbers = [t.turn_number for t in metrics_collector.turn_metrics]
        assert turn_numbers == [1, 2, 3]

    def test_on_metrics_uses_eou_transcription_delay(self, metrics_collector):
        """STT latency uses EOUMetrics.transcription_delay when available."""
        collector = metrics_collector
        collector.on_metrics(_make_eou_event(transcription_delay=0.3))
        collector.on_metrics(_make_stt_event(duration=0.5))
        # Should use transcription_delay (0.3), not audio_duration (0.5)
        assert collector._latest_stt_duration == pytest.approx(0.3)

    def test_on_metrics_falls_back_to_audio_duration_without_eou(self, metrics_collector):
        """Without a preceding EOU event, STT latency falls back to audio_duration."""
        collector = metrics_collector
        collector.on_metrics(_make_stt_event(duration=0.42))
        assert collector._latest_stt_duration == pytest.approx(0.42)

    def test_eou_consumed_after_stt_prevents_cross_turn_reuse(self, metrics_collector):
        """EOU transcription_delay is consumed by the next STT and not reused."""
        collector = metrics_collector
        # Turn 1: EOU + STT — uses transcription_delay
        collector.on_metrics(_make_eou_event(transcription_delay=0.2))
        collector.on_metrics(_make_stt_event(duration=0.5))
        assert collector._latest_stt_duration == pytest.approx(0.2)
        # Turn 2: STT without EOU — should fall back to audio_duration, not reuse 0.2
        collector.on_metrics(_make_stt_event(duration=0.6))
        assert collector._latest_stt_duration == pytest.approx(0.6)


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
        # EOU transcription_delay = 0.12345s = 123.45ms
        _send_full_turn(
            metrics_collector,
            llm_ttft=0.22222,
            tts_ttfb=0.09876,
            eou_transcription_delay=0.12345,
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
            # With stt=0ms (eou_transcription_delay=0) and llm=0.0
            _send_full_turn(
                metrics_collector,
                stt_duration=0.0,
                llm_ttft=0.0,
                tts_ttfb=i * 0.1,
                eou_transcription_delay=0.0,
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
                eou_transcription_delay=0.0,
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
        # STT latency = stt_timestamp - eou_timestamp = 1.15 - 1.0 = 150ms
        assert payload["stt_ms"] == 150.0
        assert payload["llm_ttft_ms"] == 220.0
        assert payload["tts_ttfb_ms"] == 90.0
        assert payload["total_e2e_ms"] == 460.0
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

        # EOU transcription_delay = 0.12345s = 123.45ms
        _send_full_turn(
            collector,
            llm_ttft=0.22222,
            tts_ttfb=0.09876,
            eou_transcription_delay=0.12345,
        )
        await asyncio.sleep(0)

        payload = json.loads(
            room.local_participant.publish_data.call_args[0][0]
        )
        assert payload["stt_ms"] == 123.5
        assert payload["llm_ttft_ms"] == 222.2
        assert payload["tts_ttfb_ms"] == 98.8
        assert payload["total_e2e_ms"] == 444.4
