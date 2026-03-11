"""Latency metrics collection via AgentSession events.

Usage:
    mc = MetricsCollector(session_id="abc")
    session.on("metrics_collected", mc.on_metrics)
    # After session ends:
    summary = mc.session_summary()

In livekit-agents 1.4.x, ``metrics_collected`` fires a ``MetricsCollectedEvent``
whose ``.metrics`` attribute is a *union* type — one of ``STTMetrics``,
``LLMMetrics``, ``TTSMetrics``, ``VADMetrics``, ``EOUMetrics``, or
``RealtimeModelMetrics``.  Each event delivers a single metric type, so we
accumulate individual stage timings and assemble ``TurnMetrics`` on demand.
"""

from __future__ import annotations

import structlog
from livekit.agents.metrics import (
    LLMMetrics,
    STTMetrics,
    TTSMetrics,
)

from src.types import TurnMetrics

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collects per-turn and per-session latency metrics from AgentSession events.

    Each ``metrics_collected`` event delivers a single metric type.  We store
    the latest value for each stage and periodically assemble ``TurnMetrics``
    snapshots when a TTS metric arrives (chosen because TTS is the last stage
    in the STT -> LLM -> TTS pipeline).
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.turn_metrics: list[TurnMetrics] = []
        self._current_turn = 0

        # Accumulate latest values per stage (in seconds)
        self._latest_stt_duration: float = 0.0
        self._latest_llm_ttft: float = 0.0
        self._latest_tts_ttfb: float = 0.0

    def on_metrics(self, event) -> None:
        """Handle ``MetricsCollectedEvent`` emitted by ``AgentSession``.

        ``event.metrics`` is one of ``STTMetrics | LLMMetrics | TTSMetrics |
        VADMetrics | EOUMetrics | RealtimeModelMetrics``.  We extract the
        relevant timing from each and record a full ``TurnMetrics`` when the
        TTS metric arrives (last stage in the pipeline).
        """
        metrics = event.metrics

        if isinstance(metrics, STTMetrics):
            self._latest_stt_duration = metrics.duration
            logger.debug(
                "stt_metrics",
                session_id=self.session_id,
                duration_s=metrics.duration,
            )
        elif isinstance(metrics, LLMMetrics):
            self._latest_llm_ttft = metrics.ttft
            logger.debug(
                "llm_metrics",
                session_id=self.session_id,
                ttft_s=metrics.ttft,
                duration_s=metrics.duration,
            )
        elif isinstance(metrics, TTSMetrics):
            self._latest_tts_ttfb = metrics.ttfb

            # TTS is the last pipeline stage — assemble a full turn snapshot
            self._current_turn += 1
            turn = TurnMetrics(
                turn_number=self._current_turn,
                stt_ms=self._latest_stt_duration * 1000,
                llm_ttft_ms=self._latest_llm_ttft * 1000,
                tts_ttfb_ms=self._latest_tts_ttfb * 1000,
                total_e2e_ms=(
                    self._latest_stt_duration
                    + self._latest_llm_ttft
                    + self._latest_tts_ttfb
                ) * 1000,
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
        else:
            # VADMetrics, EOUMetrics, RealtimeModelMetrics — log but don't
            # incorporate into turn timing.
            logger.debug(
                "other_metrics",
                session_id=self.session_id,
                metrics_type=type(metrics).__name__,
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
