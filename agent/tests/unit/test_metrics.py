"""Tests for MetricsCollector.

Requirement mapping:
- test_metrics_collector_initial_state → Clean initialization
- test_on_metrics_* → Per-turn metric capture
- test_get_latest_metrics_* → Frontend overlay data
- test_session_summary_* → Aggregate reporting
"""

from types import SimpleNamespace

import pytest
from src.metrics import MetricsCollector


class TestMetricsCollectorInitialState:
    def test_metrics_collector_initial_state(self, metrics_collector):
        assert metrics_collector.turn_metrics == []
        assert metrics_collector.session_id == "test-session"
        assert metrics_collector._current_turn == 0


class TestOnMetrics:
    def test_on_metrics_stores_turn(self, metrics_collector, mock_metrics_event):
        metrics_collector.on_metrics(mock_metrics_event)
        assert len(metrics_collector.turn_metrics) == 1
        turn = metrics_collector.turn_metrics[0]
        assert turn.turn_number == 1
        assert turn.stt_ms == pytest.approx(250.0)
        assert turn.llm_ttft_ms == pytest.approx(220.0)
        assert turn.tts_ttfb_ms == pytest.approx(90.0)
        assert turn.total_e2e_ms == pytest.approx(650.0)

    def test_on_metrics_increments_turn_number(self, metrics_collector, mock_metrics_event):
        for _ in range(3):
            metrics_collector.on_metrics(mock_metrics_event)
        turn_numbers = [t.turn_number for t in metrics_collector.turn_metrics]
        assert turn_numbers == [1, 2, 3]


class TestGetLatestMetrics:
    def test_get_latest_metrics_empty(self, metrics_collector):
        assert metrics_collector.get_latest_metrics() == {}

    def test_get_latest_metrics_returns_last(self, metrics_collector, mock_metrics_event):
        for _ in range(3):
            metrics_collector.on_metrics(mock_metrics_event)
        latest = metrics_collector.get_latest_metrics()
        assert latest["turn"] == 3

    def test_get_latest_metrics_values_rounded(self, metrics_collector):
        event = SimpleNamespace(
            stt_duration=0.12345,
            llm_ttft=0.22222,
            tts_ttfb=0.09876,
            e2e_duration=0.55555,
        )
        metrics_collector.on_metrics(event)
        latest = metrics_collector.get_latest_metrics()
        assert latest["stt_ms"] == 123.5
        assert latest["llm_ttft_ms"] == 222.2
        assert latest["tts_ttfb_ms"] == 98.8
        assert latest["total_e2e_ms"] == 555.5


class TestSessionSummary:
    def test_session_summary_empty(self, metrics_collector):
        assert metrics_collector.session_summary() == {}

    def test_session_summary_computes_stats(self, metrics_collector):
        for i in range(1, 11):
            event = SimpleNamespace(
                stt_duration=0.1,
                llm_ttft=0.1,
                tts_ttfb=0.1,
                e2e_duration=i * 0.1,  # 100ms, 200ms, ... 1000ms
            )
            metrics_collector.on_metrics(event)

        summary = metrics_collector.session_summary()
        assert summary["total_turns"] == 10
        assert summary["e2e_mean_ms"] == pytest.approx(550.0)
        assert summary["e2e_max_ms"] == pytest.approx(1000.0)
        assert summary["pct_under_500ms"] == pytest.approx(40.0)
        assert summary["pct_under_1000ms"] == pytest.approx(90.0)

    def test_session_summary_skips_zero_e2e(self, metrics_collector):
        # Add turns with zero e2e (should be excluded)
        for e2e_val in [0.0, 0.5, 0.0, 0.3]:
            event = SimpleNamespace(
                stt_duration=0.1,
                llm_ttft=0.1,
                tts_ttfb=0.1,
                e2e_duration=e2e_val,
            )
            metrics_collector.on_metrics(event)

        summary = metrics_collector.session_summary()
        # Only 2 non-zero e2e values: 500ms and 300ms
        assert summary["total_turns"] == 4
        assert summary["e2e_mean_ms"] == pytest.approx(400.0)
        assert summary["e2e_max_ms"] == pytest.approx(500.0)
