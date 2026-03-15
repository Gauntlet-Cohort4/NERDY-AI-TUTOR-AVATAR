"""Nerdy AI Tutor Agent — LiveKit AgentServer entrypoint.

This module starts the LiveKit AgentServer and wires together:
- AgentSession with STT, LLM, TTS plugins
- Avatar rendering (Simli, Hedra, or Beyond Presence, via AVATAR_PROVIDER env var)
- MetricsCollector for latency tracking
- SubjectRouterAgent as the initial agent
- HTTP server on port 8080 for health checks and REST API endpoints
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import structlog
from livekit.agents import Agent, AgentSession
from livekit.plugins import cartesia, deepgram, groq, silero, simli  # noqa: F401

try:
    from livekit.plugins import hedra  # noqa: F401
except ImportError:
    hedra = None  # Hedra plugin optional; only needed when AVATAR_PROVIDER=hedra

try:
    from livekit.plugins import bey  # noqa: F401
except ImportError:
    bey = None  # Bey plugin optional; only needed when AVATAR_PROVIDER=beyondpresence

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
from src.avatar.renderer import create_avatar
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
    """HTTP handler for health checks and REST API endpoints."""

    def do_GET(self) -> None:
        if self.path == "/health":
            body = json.dumps(health_check()).encode()
            self._send(200, body, "application/json")
            return

        # Delegate to API router
        from src.api.router import handle_get

        result = handle_get(self.path, self)
        if result is not None:
            body, status, content_type = result
            self._send(status, body, content_type)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        from src.api.router import handle_post

        body = self._read_body()
        result = handle_post(self.path, body, self)
        if result is not None:
            resp_body, status, content_type = result
            self._send(status, resp_body, content_type)
            return

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self) -> None:
        from src.api.router import handle_patch

        body = self._read_body()
        result = handle_patch(self.path, body, self)
        if result is not None:
            resp_body, status, content_type = result
            self._send(status, resp_body, content_type)
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        """Send a response with proper headers including CORS."""
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self) -> None:
        """Add CORS headers for frontend access."""
        origin = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")

    _MAX_BODY_BYTES = 15 * 1024 * 1024  # 15 MB (includes multipart overhead)

    def _read_body(self) -> bytes:
        """Read the request body, rejecting oversized payloads."""
        length = int(self.headers.get("Content-Length", 0))
        if length > self._MAX_BODY_BYTES:
            return b""  # will be caught downstream
        return self.rfile.read(length) if length > 0 else b""

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
    avatar_provider: str


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
        avatar_provider=config.avatar_provider,
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

    Wires STT → LLM → TTS pipeline with avatar and metrics collection.
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

    # Avatar — provider selected by AVATAR_PROVIDER env var
    avatar = create_avatar(config)

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

    # Handle typed text input from the frontend (accessibility alternative to mic).
    # The frontend publishes UTF-8 text on the "chat_input" data channel topic.
    # We feed it into the agent session as user input via generate_reply().
    @ctx.room.on("data_received")
    def _on_data_received(data_packet) -> None:
        topic = getattr(data_packet, "topic", None)
        if topic != "chat_input":
            return
        try:
            raw = data_packet.data
            text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
            text = text.strip()
            if not text:
                return
            logger.info("text_input_received", session_id=session_id, length=len(text))
            import asyncio

            asyncio.ensure_future(session.generate_reply(user_input=text))
        except Exception:
            logger.warning("text_input_handling_failed", session_id=session_id, exc_info=True)

    # Initial greeting is triggered by the agent's on_enter() hook,
    # which the framework calls once the session activity is fully ready.

    logger.info("session_started", session_id=session_id)


if __name__ == "__main__":
    import asyncio as _asyncio

    from livekit.agents import WorkerOptions, cli

    setup_logging()

    # Initialize DB if configured — pool is shared via api.router module
    _config = AppConfig.from_env()
    if _config.database_url:
        from src.api.router import set_db, set_event_loop
        from src.db import Database

        _db = Database()
        _loop = _asyncio.new_event_loop()

        _loop.run_until_complete(_db.connect(_config.database_url))
        set_db(_db)
        set_event_loop(_loop)

        # Run the event loop in a background thread so coroutines can execute
        _loop_thread = threading.Thread(target=_loop.run_forever, daemon=True)
        _loop_thread.start()

        logger.info("database_initialized_for_api")

    _start_health_server()
    logger.info("agent_server_starting")

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )
