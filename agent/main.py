"""Nerdy AI Tutor Agent — LiveKit AgentServer entrypoint.

This module starts the LiveKit AgentServer and wires together:
- AgentSession with STT, LLM, TTS plugins
- Simli AvatarSession for video rendering
- MetricsCollector for latency tracking
- SubjectRouterAgent as the initial agent
- Lightweight HTTP health check server on port 8080
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import structlog
from livekit.agents import Agent, AgentSession
from livekit.plugins import cartesia, deepgram, groq, silero, simli  # noqa: F401

from src.agents.algebra_ii import AlgebraIITutorAgent
from src.agents.ap_biology import APBiologyTutorAgent
from src.agents.biology import BiologyTutorAgent
from src.agents.calculus import CalculusTutorAgent
from src.agents.cell_biology import CellBiologyTutorAgent
from src.agents.chemistry import ChemistryTutorAgent
from src.agents.earth_science import EarthScienceTutorAgent
from src.agents.intro_algebra import IntroAlgebraTutorAgent
from src.agents.math import MathTutorAgent
from src.agents.physics import PhysicsTutorAgent
from src.agents.router import SubjectRouterAgent
from src.agents.world_history import WorldHistoryTutorAgent
from src.avatar.renderer import SimliAvatarAdapter
from src.config import AppConfig
from src.education.history import ConversationHistory
from src.education.tracker import ConversationTracker
from src.errors import ErrorSeverity, PipelineError, PipelineStage, handle_pipeline_error
from src.logging_setup import setup_logging
from src.metrics import MetricsCollector

logger = structlog.get_logger(__name__)

# ── Health check HTTP server ────────────────────────────────────────────────

HEALTH_PORT = 8080


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that responds to GET /health."""

    def do_GET(self) -> None:
        if self.path == "/health":
            body = json.dumps(health_check()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args) -> None:
        """Suppress default access logs — structlog handles our logging."""
        pass


def _start_health_server() -> None:
    """Start the health check HTTP server in a daemon thread."""
    server = HTTPServer(("0.0.0.0", HEALTH_PORT), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("health_server_started", port=HEALTH_PORT)


# ── Agent session config ────────────────────────────────────────────────────


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


_SUBJECT_AGENTS = {
    "biology": BiologyTutorAgent,
    "math": MathTutorAgent,
    "earth_science": EarthScienceTutorAgent,
    "intro_algebra": IntroAlgebraTutorAgent,
    "algebra_ii": AlgebraIITutorAgent,
    "chemistry": ChemistryTutorAgent,
    "cell_biology": CellBiologyTutorAgent,
    "world_history": WorldHistoryTutorAgent,
    "calculus": CalculusTutorAgent,
    "physics": PhysicsTutorAgent,
    "ap_biology": APBiologyTutorAgent,
}


def _parse_grade(parts: list[str]) -> int | None:
    """Extract grade from room name parts like ['tutor', 'biology', 'g7', '12345']."""
    for part in parts:
        match = re.fullmatch(r"g(\d{1,2})", part)
        if match:
            grade = int(match.group(1))
            if 6 <= grade <= 12:
                return grade
    return None


def _resolve_agent(room_name: str) -> Agent:
    """Parse subject and grade from room name and return the matching agent.

    Room name format: tutor-{subject}-g{grade}-{timestamp}
    Falls back to the router if subject is unrecognized.
    """
    logger.info("resolve_agent_called", room_name=room_name)
    parts = room_name.split("-")
    grade = _parse_grade(parts)

    if len(parts) >= 2:
        subject_key = parts[1].lower()
        agent_cls = _SUBJECT_AGENTS.get(subject_key)
        if agent_cls is not None:
            logger.info("direct_subject_routing", subject=subject_key, grade=grade)
            return agent_cls(grade=grade)

    logger.warning("falling_back_to_router", room_name=room_name, parts=parts, grade=grade)
    return SubjectRouterAgent(grade=grade)


# ── LiveKit entrypoint ──────────────────────────────────────────────────────


async def entrypoint(ctx) -> None:
    """LiveKit AgentServer entrypoint — called for each new room connection.

    Wires STT → LLM → TTS pipeline with Simli avatar and metrics collection.
    """
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
    # WORKAROUND: groq.LLM inherits OpenAILLM._strict_tool_schema but doesn't
    # expose it as a constructor arg. Llama models reject OpenAI strict tool schemas
    # (required + empty properties). Pinned: livekit-agents~=1.4.4 in requirements.txt.
    # Track: https://github.com/livekit/agents — remove once groq plugin exposes this.
    llm._strict_tool_schema = False

    tts = cartesia.TTS(
        model=config.cartesia_model,
        voice=config.cartesia_voice_id,
        speed=0.9,  # sonic-3 requires float 0.6–2.0; 1.0 = normal
        text_pacing=True,
    )

    # Avatar
    avatar = SimliAvatarAdapter(
        api_key=config.simli_api_key,
        face_id=config.simli_face_id,
        max_session_length=config.simli_max_session_length,
        max_idle_time=config.simli_max_idle_time,
    )

    # Metrics — pass the room so metrics are published to the data channel
    metrics = MetricsCollector(session_id=session_id, room=ctx.room)

    # Create and start session
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=silero.VAD.load(
            activation_threshold=0.65,
            min_speech_duration=0.1,
        ),
    )

    session.on("metrics_collected", metrics.on_metrics)

    def _on_session_error(error_event) -> None:
        """Handle session-level errors via the pipeline error handler."""
        raw_error = error_event.error
        pipeline_error = PipelineError(
            stage=PipelineStage.SESSION,
            severity=ErrorSeverity.DEGRADED,
            message=str(raw_error),
            original_exception=raw_error if isinstance(raw_error, Exception) else None,
        )
        handle_pipeline_error(pipeline_error)

    session.on("error", _on_session_error)

    # Conversation tracker — hooks session events for background summarization
    history = ConversationHistory(
        max_turns=config.max_conversation_turns,
        summarization_threshold=config.summarization_threshold,
        token_budget=config.token_budget,
    )

    async def llm_summarizer(messages: list[dict]) -> str:
        """Background summarization via Groq — fire-and-forget, non-blocking."""
        from groq import AsyncGroq

        client = AsyncGroq()
        response = await client.chat.completions.create(
            model=config.groq_model,
            messages=messages,
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    tracker = ConversationTracker(history=history, llm_callable=llm_summarizer)
    session.on("conversation_item_added", tracker.on_conversation_item)

    # Start avatar
    await avatar.start(session, ctx.room)

    # Resolve agent from room name — goes directly to the subject tutor
    # when the frontend already selected a subject, falls back to router otherwise.
    agent = _resolve_agent(session_id)

    await session.start(
        room=ctx.room,
        agent=agent,
    )

    # Initial greeting is triggered by the agent's on_enter() hook,
    # which the framework calls once the session activity is fully ready.

    logger.info("session_started", session_id=session_id)


if __name__ == "__main__":
    from livekit.agents import WorkerOptions, cli

    setup_logging()
    _start_health_server()
    logger.info("agent_server_starting")

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )
