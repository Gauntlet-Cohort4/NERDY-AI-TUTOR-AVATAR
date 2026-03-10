"""Latency metrics collection via AgentSession events.

Usage:
    mc = MetricsCollector(session_id="abc")
    session.on("metrics_collected", mc.on_metrics)
    # After session ends:
    summary = mc.session_summary()
"""

import structlog

from src.types import TurnMetrics

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collects per-turn and per-session latency metrics from AgentSession events."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.turn_metrics: list[TurnMetrics] = []
        self._current_turn = 0

    def on_metrics(self, metrics_event) -> None:
        """Handle metrics events emitted by AgentSession.

        Extracts per-stage timings and stores as TurnMetrics.
        Converts seconds to milliseconds.
        """
        self._current_turn += 1
        turn = TurnMetrics(
            turn_number=self._current_turn,
            stt_ms=getattr(metrics_event, "stt_duration", 0.0) * 1000,
            llm_ttft_ms=getattr(metrics_event, "llm_ttft", 0.0) * 1000,
            tts_ttfb_ms=getattr(metrics_event, "tts_ttfb", 0.0) * 1000,
            total_e2e_ms=getattr(metrics_event, "e2e_duration", 0.0) * 1000,
        )
        self.turn_metrics.append(turn)

        logger.info(
            "turn_metrics",
            session_id=self.session_id,
            turn=turn.turn_number,
            stt_ms=turn.stt_ms,
            llm_ttft_ms=turn.llm_ttft_ms,
            tts_ttfb_ms=turn.tts_ttfb_ms,
            total_ms=turn.total_e2e_ms,
        )

    def get_latest_metrics(self) -> dict:
        """Return latest turn metrics as dict for frontend overlay."""
        if not self.turn_metrics:
            return {}
        latest = self.turn_metrics[-1]
        return {
            "turn": latest.turn_number,
            "stt_ms": round(latest.stt_ms, 1),
            "llm_ttft_ms": round(latest.llm_ttft_ms, 1),
            "tts_ttfb_ms": round(latest.tts_ttfb_ms, 1),
            "total_e2e_ms": round(latest.total_e2e_ms, 1),
        }

    def session_summary(self) -> dict:
        """Return aggregate stats for the session."""
        if not self.turn_metrics:
            return {}
        e2e = [t.total_e2e_ms for t in self.turn_metrics if t.total_e2e_ms > 0]
        if not e2e:
            return {}
        s = sorted(e2e)
        p95_idx = int(len(s) * 0.95)
        return {
            "session_id": self.session_id,
            "total_turns": len(self.turn_metrics),
            "e2e_mean_ms": round(sum(e2e) / len(e2e), 1),
            "e2e_median_ms": round(s[len(s) // 2], 1),
            "e2e_p95_ms": round(s[min(p95_idx, len(s) - 1)], 1),
            "e2e_max_ms": round(max(e2e), 1),
            "pct_under_500ms": round(
                sum(1 for v in e2e if v < 500) / len(e2e) * 100, 1
            ),
            "pct_under_1000ms": round(
                sum(1 for v in e2e if v < 1000) / len(e2e) * 100, 1
            ),
        }
