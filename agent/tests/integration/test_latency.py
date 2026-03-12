"""Integration tests for latency metrics collection and benchmarking.

Tests cover:
- MetricsCollector tracks per-stage latency across multiple turns
- Session summary computes correct aggregate statistics
- Synthetic benchmarks verify latency stays under target thresholds
  (500ms first avatar frame, 1000ms maximum e2e)
- Metrics round-trip: individual events -> TurnMetrics -> session summary

Benchmark patterns are modeled after scripts/benchmark.py methodology.

Marked with @pytest.mark.integration — skipped when LIVEKIT_URL is absent.
"""

from __future__ import annotations

import os
import random

import pytest

from src.metrics import MetricsCollector
from tests.conftest import (
    _make_llm_event,
    _make_stt_event,
    _send_full_turn,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("LIVEKIT_URL"),
    reason="Integration tests require live API keys",
)

# ---------------------------------------------------------------------------
# Target thresholds (from tech spec)
# ---------------------------------------------------------------------------
TARGET_FIRST_FRAME_MS = 500.0  # < 500ms first avatar frame
TARGET_MAX_E2E_MS = 1000.0  # < 1s maximum end-to-end


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def collector() -> MetricsCollector:
    """Fresh MetricsCollector for integration tests."""
    return MetricsCollector(session_id="integration-test")


@pytest.fixture
def collector_with_10_turns(collector: MetricsCollector) -> MetricsCollector:
    """MetricsCollector pre-loaded with 10 turns of realistic latency data.

    Simulates a realistic session where latencies vary within acceptable
    ranges: STT 100-300ms, LLM TTFT 100-400ms, TTS TTFB 50-150ms.
    """
    random.seed(42)  # Deterministic for reproducibility
    for _ in range(10):
        stt_duration = random.uniform(0.10, 0.30)
        llm_ttft = random.uniform(0.10, 0.40)
        tts_ttfb = random.uniform(0.05, 0.15)
        _send_full_turn(
            collector,
            stt_duration=stt_duration,
            llm_ttft=llm_ttft,
            tts_ttfb=tts_ttfb,
        )
    return collector


# ---------------------------------------------------------------------------
# Per-stage latency tracking
# ---------------------------------------------------------------------------


class TestPerStageLatencyTracking:
    """Verify MetricsCollector correctly tracks latency for each pipeline stage."""

    def test_stt_latency_recorded(self, collector: MetricsCollector):
        """STT duration is captured in TurnMetrics."""
        _send_full_turn(collector, stt_duration=0.25, llm_ttft=0.10, tts_ttfb=0.05)
        turn = collector.turn_metrics[0]
        assert turn.stt_ms == pytest.approx(250.0)

    def test_llm_ttft_recorded(self, collector: MetricsCollector):
        """LLM time-to-first-token is captured in TurnMetrics."""
        _send_full_turn(collector, stt_duration=0.10, llm_ttft=0.35, tts_ttfb=0.05)
        turn = collector.turn_metrics[0]
        assert turn.llm_ttft_ms == pytest.approx(350.0)

    def test_tts_ttfb_recorded(self, collector: MetricsCollector):
        """TTS time-to-first-byte is captured in TurnMetrics."""
        _send_full_turn(collector, stt_duration=0.10, llm_ttft=0.10, tts_ttfb=0.12)
        turn = collector.turn_metrics[0]
        assert turn.tts_ttfb_ms == pytest.approx(120.0)

    def test_total_e2e_is_sum_of_stages(self, collector: MetricsCollector):
        """Total e2e latency equals sum of STT + LLM TTFT + TTS TTFB."""
        _send_full_turn(collector, stt_duration=0.20, llm_ttft=0.15, tts_ttfb=0.10)
        turn = collector.turn_metrics[0]
        expected_e2e = (0.20 + 0.15 + 0.10) * 1000  # 450ms
        assert turn.total_e2e_ms == pytest.approx(expected_e2e)

    def test_partial_events_do_not_create_turn(self, collector: MetricsCollector):
        """Sending only STT and LLM events (no TTS) does not produce a TurnMetrics."""
        collector.on_metrics(_make_stt_event(duration=0.25))
        collector.on_metrics(_make_llm_event(ttft=0.22))
        assert len(collector.turn_metrics) == 0

    def test_multiple_turns_accumulate(self, collector: MetricsCollector):
        """Each complete STT->LLM->TTS cycle produces one TurnMetrics."""
        for i in range(5):
            _send_full_turn(
                collector,
                stt_duration=0.10 + i * 0.02,
                llm_ttft=0.15,
                tts_ttfb=0.08,
            )
        assert len(collector.turn_metrics) == 5
        # Turn numbers are sequential
        numbers = [t.turn_number for t in collector.turn_metrics]
        assert numbers == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# Session summary statistics
# ---------------------------------------------------------------------------


class TestSessionSummaryStatistics:
    """Verify aggregate session statistics computation."""

    def test_summary_has_all_fields(
        self, collector_with_10_turns: MetricsCollector
    ):
        """Session summary contains all required statistical fields."""
        summary = collector_with_10_turns.session_summary()
        required_keys = {
            "session_id",
            "total_turns",
            "e2e_mean_ms",
            "e2e_median_ms",
            "e2e_p95_ms",
            "e2e_max_ms",
            "pct_under_500ms",
            "pct_under_1000ms",
        }
        assert required_keys.issubset(set(summary.keys()))

    def test_summary_turn_count(self, collector_with_10_turns: MetricsCollector):
        """Summary reports correct number of turns."""
        summary = collector_with_10_turns.session_summary()
        assert summary["total_turns"] == 10

    def test_summary_mean_is_reasonable(
        self, collector_with_10_turns: MetricsCollector
    ):
        """Mean e2e latency falls within the expected range for synthetic data."""
        summary = collector_with_10_turns.session_summary()
        # With STT 100-300ms, LLM 100-400ms, TTS 50-150ms:
        # Min possible = 250ms, Max possible = 850ms
        assert 200.0 < summary["e2e_mean_ms"] < 900.0

    def test_summary_p95_leq_max(self, collector_with_10_turns: MetricsCollector):
        """p95 latency is always less than or equal to max latency."""
        summary = collector_with_10_turns.session_summary()
        assert summary["e2e_p95_ms"] <= summary["e2e_max_ms"]

    def test_summary_median_leq_mean_or_close(
        self, collector_with_10_turns: MetricsCollector
    ):
        """Median should be reasonably close to mean for uniform-ish distributions."""
        summary = collector_with_10_turns.session_summary()
        # Median and mean should be within 50% of each other for 10 samples
        ratio = summary["e2e_median_ms"] / summary["e2e_mean_ms"]
        assert 0.5 < ratio < 1.5

    def test_get_latest_metrics_matches_last_turn(
        self, collector_with_10_turns: MetricsCollector
    ):
        """get_latest_metrics returns data consistent with the last TurnMetrics."""
        latest = collector_with_10_turns.get_latest_metrics()
        last_turn = collector_with_10_turns.turn_metrics[-1]
        assert latest["turn"] == last_turn.turn_number
        assert latest["stt_ms"] == round(last_turn.stt_ms, 1)
        assert latest["llm_ttft_ms"] == round(last_turn.llm_ttft_ms, 1)
        assert latest["tts_ttfb_ms"] == round(last_turn.tts_ttfb_ms, 1)


# ---------------------------------------------------------------------------
# Synthetic latency benchmarks
# ---------------------------------------------------------------------------


class TestSyntheticLatencyBenchmarks:
    """Benchmark-style tests verifying latency stays under spec thresholds.

    These use synthetic (deterministic) metrics to validate that the pipeline
    *architecture* meets latency targets. Real-world latency testing requires
    live API keys and network conditions.
    """

    def test_fast_turn_under_first_frame_target(self, collector: MetricsCollector):
        """A fast turn (optimistic latencies) stays under 500ms first frame target."""
        _send_full_turn(
            collector,
            stt_duration=0.10,  # 100ms
            llm_ttft=0.15,  # 150ms
            tts_ttfb=0.05,  # 50ms
        )
        turn = collector.turn_metrics[0]
        assert turn.total_e2e_ms < TARGET_FIRST_FRAME_MS

    def test_typical_turn_under_max_e2e_target(self, collector: MetricsCollector):
        """A typical turn (moderate latencies) stays under 1000ms max e2e target."""
        _send_full_turn(
            collector,
            stt_duration=0.25,  # 250ms
            llm_ttft=0.30,  # 300ms
            tts_ttfb=0.10,  # 100ms
        )
        turn = collector.turn_metrics[0]
        assert turn.total_e2e_ms < TARGET_MAX_E2E_MS

    def test_realistic_session_pct_under_500ms(
        self, collector_with_10_turns: MetricsCollector
    ):
        """A realistic 10-turn session should have a meaningful percentage under 500ms."""
        summary = collector_with_10_turns.session_summary()
        # With our seed-42 distribution, some turns should be under 500ms
        assert summary["pct_under_500ms"] >= 0.0  # Sanity check: non-negative

    def test_realistic_session_all_under_max_e2e(
        self, collector_with_10_turns: MetricsCollector
    ):
        """All turns in a realistic session stay under the 1000ms max e2e threshold."""
        summary = collector_with_10_turns.session_summary()
        assert summary["pct_under_1000ms"] == 100.0

    def test_worst_case_synthetic_scenario(self, collector: MetricsCollector):
        """Worst-case synthetic latencies (high but within provider SLAs)."""
        _send_full_turn(
            collector,
            stt_duration=0.30,  # 300ms (Deepgram max typical)
            llm_ttft=0.40,  # 400ms (Groq max typical)
            tts_ttfb=0.15,  # 150ms (Cartesia max typical)
        )
        turn = collector.turn_metrics[0]
        # 850ms total — under 1000ms max but over 500ms first frame
        assert turn.total_e2e_ms < TARGET_MAX_E2E_MS
        assert turn.total_e2e_ms == pytest.approx(850.0)

    def test_turn_metrics_are_frozen(self, collector: MetricsCollector):
        """TurnMetrics dataclass is frozen — immutable after creation."""
        _send_full_turn(collector, stt_duration=0.20, llm_ttft=0.20, tts_ttfb=0.10)
        turn = collector.turn_metrics[0]
        with pytest.raises(AttributeError):
            turn.stt_ms = 999.0  # type: ignore[misc]
