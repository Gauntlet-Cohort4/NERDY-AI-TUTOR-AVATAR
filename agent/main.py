"""Nerdy AI Tutor Agent — LiveKit AgentServer entrypoint.

This module starts the LiveKit AgentServer and wires together:
- AgentSession with STT, LLM, TTS plugins
- Simli AvatarSession for video rendering
- MetricsCollector for latency tracking
- SubjectRouterAgent as the initial agent
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

from src.config import AppConfig
from src.logging_setup import setup_logging

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AgentSessionConfig:
    """Describes how an AgentSession should be wired — testable without LiveKit."""

    agent_name: str
    stt_provider: str
    stt_model: str
    stt_language: str
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    tts_provider: str
    tts_model: str
    tts_voice_id: str
    simli_api_key: str
    simli_face_id: str


def create_agent_session(config: AppConfig) -> AgentSessionConfig:
    """Build an AgentSessionConfig from AppConfig — pure function, no side effects."""
    return AgentSessionConfig(
        agent_name="SubjectRouterAgent",
        stt_provider="deepgram",
        stt_model=config.deepgram_model,
        stt_language=config.deepgram_language,
        llm_provider="groq",
        llm_model=config.groq_model,
        llm_temperature=config.groq_temperature,
        llm_max_tokens=config.groq_max_tokens,
        tts_provider="cartesia",
        tts_model=config.cartesia_model,
        tts_voice_id=config.cartesia_voice_id,
        simli_api_key=config.simli_api_key,
        simli_face_id=config.simli_face_id,
    )


def health_check() -> dict:
    """Return a health status dict for the agent service."""
    return {
        "status": "healthy",
        "service": "nerdy-ai-tutor-agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def entrypoint(ctx) -> None:
    """LiveKit AgentServer entrypoint — called for each new room connection.

    Wires STT → LLM → TTS pipeline with Simli avatar and metrics collection.
    """
    from livekit.agents import AgentSession
    from livekit.plugins import deepgram, groq, cartesia, simli, silero

    from src.agents.router import SubjectRouterAgent
    from src.avatar.renderer import SimliAvatarAdapter
    from src.metrics import MetricsCollector

    setup_logging()
    config = AppConfig.from_env()
    session_id = ctx.room.name if hasattr(ctx, "room") else "unknown"

    logger.info("session_starting", session_id=session_id)

    # Build pipeline components
    stt = deepgram.STT(
        model=config.deepgram_model,
        language=config.deepgram_language,
    )
    llm = groq.LLM(
        model=config.groq_model,
        temperature=config.groq_temperature,
    )
    tts = cartesia.TTS(
        model=config.cartesia_model,
        voice=config.cartesia_voice_id,
    )

    # Avatar
    avatar = SimliAvatarAdapter(
        api_key=config.simli_api_key,
        face_id=config.simli_face_id,
        max_session_length=config.simli_max_session_length,
        max_idle_time=config.simli_max_idle_time,
    )

    # Metrics
    metrics = MetricsCollector(session_id=session_id)

    # Create and start session
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=silero.VAD.load(),
        chat_ctx=None,
    )

    session.on("metrics_collected", metrics.on_metrics)

    # Start avatar
    await avatar.start(session, ctx.room)

    # Start the session with the router agent
    await session.start(
        room=ctx.room,
        agent=SubjectRouterAgent(),
    )

    logger.info("session_started", session_id=session_id)


if __name__ == "__main__":
    from livekit.agents import WorkerOptions, cli

    setup_logging()
    logger.info("agent_server_starting")

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )
