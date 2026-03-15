"""Nerdy AI Tutor Agent — LiveKit AgentServer entrypoint.

This module starts the LiveKit AgentServer and wires together:
- AgentSession with STT, LLM, TTS plugins
- Avatar rendering (Simli, Hedra, or Beyond Presence, via AVATAR_PROVIDER env var)
- MetricsCollector for latency tracking
- SubjectRouterAgent as the initial agent
- HTTP server on port 8080 for health checks and REST API endpoints
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from uuid import UUID

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
        if body is None:
            return
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
        if body is None:
            return
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

    def _read_body(self) -> bytes | None:
        """Read the request body, rejecting oversized payloads.

        Returns None if a 413 response was already sent (caller must return).
        """
        length = int(self.headers.get("Content-Length", 0))
        if length > self._MAX_BODY_BYTES:
            self.send_response(413)
            self.end_headers()
            return None
        return self.rfile.read(length) if length > 0 else b""

    def log_message(self, format, *args) -> None:
        """Suppress default access logs — structlog handles our logging."""
        pass


class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer that handles each request in a new thread.

    Prevents long-running API requests (e.g. LLM-backed artifact generation)
    from blocking health checks and other endpoints.
    """
    daemon_threads = True


def _start_health_server() -> None:
    """Start the health check HTTP server in a daemon thread."""
    server = _ThreadedHTTPServer(("0.0.0.0", HEALTH_PORT), _HealthHandler)
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


def _resolve_agent(subject_key: str | None, grade: int | None) -> Agent:
    """Return the matching agent for a subject/grade pair.

    Falls back to the router if subject is unrecognized.
    """
    if subject_key is not None:
        agent_cls = _SUBJECT_AGENTS.get(subject_key)
        if agent_cls is not None:
            logger.info("direct_subject_routing", subject=subject_key, grade=grade)
            return agent_cls(grade=grade)

    logger.warning("falling_back_to_router", subject_key=subject_key, grade=grade)
    return SubjectRouterAgent(grade=grade)


def _parse_room_name(room_name: str) -> tuple[str | None, int | None]:
    """Extract subject_key and grade from a room name.

    Room name format: tutor-{subject}-g{grade}-{timestamp}
    Returns (subject_key, grade) — either may be None.
    """
    parts = room_name.split("-")
    grade = _parse_grade(parts)
    subject_key = parts[1].lower() if len(parts) >= 2 else None
    return subject_key, grade


# ── DB session persistence helpers ───────────────────────────────────────────

_DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def _run_db_async(coro):
    """Dispatch a coroutine to the DB event loop and await the result.

    The DB pool lives on a separate event loop (_loop in __main__).
    This bridges the LiveKit worker loop to the DB loop safely.
    """
    from src.api.router import get_event_loop

    loop = get_event_loop()
    if loop is None:
        raise RuntimeError("No DB event loop available")
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return await asyncio.wrap_future(future)


# ── Dedicated LLM event loop ─────────────────────────────────────────────────
# Mirrors the DB loop pattern. Keeps long-running Groq API calls (2-5 s each)
# off the DB loop so they don't block asyncpg writes at high concurrency.

_llm_loop: asyncio.AbstractEventLoop | None = None
_llm_thread: threading.Thread | None = None


def _start_llm_loop() -> None:
    """Create and start the dedicated LLM event loop in a daemon thread."""
    global _llm_loop, _llm_thread
    _llm_loop = asyncio.new_event_loop()
    _llm_thread = threading.Thread(target=_llm_loop.run_forever, daemon=True)
    _llm_thread.start()
    logger.info("llm_event_loop_started")


async def _run_llm_async(coro):
    """Dispatch a coroutine to the LLM event loop and await the result.

    Identical to _run_db_async but targets the dedicated LLM loop so that
    long-running Groq API calls don't block database operations.
    """
    if _llm_loop is None:
        raise RuntimeError("No LLM event loop available")
    future = asyncio.run_coroutine_threadsafe(coro, _llm_loop)
    return await asyncio.wrap_future(future)


async def _get_or_create_demo_user(pool) -> UUID:
    """Ensure the demo user exists and return their UUID."""
    await pool.execute(
        "INSERT INTO users (id, display_name) VALUES ($1, 'Demo Student') "
        "ON CONFLICT (id) DO NOTHING",
        _DEMO_USER_ID,
    )
    return _DEMO_USER_ID


class _CrossLoopPool:
    """Proxy that dispatches asyncpg pool operations to the DB event loop.

    The asyncpg pool is bound to the event loop it was created on.
    The ConversationTracker runs on the LiveKit worker loop, so direct
    awaits on the pool would fail. This proxy transparently bridges the
    two loops using ``asyncio.wrap_future(run_coroutine_threadsafe(...))``.
    """

    def __init__(self, real_pool, db_loop: asyncio.AbstractEventLoop) -> None:
        self._pool = real_pool
        self._db_loop = db_loop

    async def fetchrow(self, *args, **kwargs):
        future = asyncio.run_coroutine_threadsafe(
            self._pool.fetchrow(*args, **kwargs), self._db_loop,
        )
        return await asyncio.wrap_future(future)

    async def fetch(self, *args, **kwargs):
        future = asyncio.run_coroutine_threadsafe(
            self._pool.fetch(*args, **kwargs), self._db_loop,
        )
        return await asyncio.wrap_future(future)

    async def execute(self, *args, **kwargs):
        future = asyncio.run_coroutine_threadsafe(
            self._pool.execute(*args, **kwargs), self._db_loop,
        )
        return await asyncio.wrap_future(future)


# ── LiveKit entrypoint ──────────────────────────────────────────────────────


async def entrypoint(ctx) -> None:
    """LiveKit AgentServer entrypoint — called for each new room connection.

    Wires STT → LLM → TTS pipeline with avatar and metrics collection.
    """
    config = AppConfig.from_env()
    room_name = ctx.room.name if hasattr(ctx, "room") else "unknown"

    logger.info("session_starting", session_id=room_name)

    # Parse subject and grade from room name — used for both routing and DB
    subject_key, grade = _parse_room_name(room_name)

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
        speed=1.0,
        # text_pacing disabled: Cartesia plugin's EOS packet sends only " "
        # with continue=False, which clips the final word when pacing buffers it.
        # See: https://github.com/livekit/agents/issues/4171
    )

    # Avatar — provider selected by AVATAR_PROVIDER env var
    avatar = create_avatar(config)

    # Metrics — pass the room so metrics are published to the data channel
    metrics = MetricsCollector(session_id=room_name, room=ctx.room)

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

    # ── DB session persistence (graceful degradation) ────────────────────
    from src.api.router import get_event_loop, get_pool

    pool = get_pool()
    db_loop = get_event_loop()
    db_session_id: UUID | None = None

    if pool is not None and db_loop is not None and subject_key is not None:
        try:
            demo_user_id = await _run_db_async(
                _get_or_create_demo_user(pool),
            )

            from src.db.sessions import create_session

            db_session_id = await _run_db_async(
                create_session(
                    pool, demo_user_id, subject_key, grade or 7, room_name,
                ),
            )
            logger.info(
                "db_session_created",
                db_session_id=str(db_session_id),
                subject=subject_key,
            )
        except Exception:
            logger.warning("db_session_creation_failed", exc_info=True)

    # Wire tracker to DB — use a cross-loop proxy so the tracker's
    # fire-and-forget awaits on the LiveKit loop reach the DB loop.
    if pool is not None and db_loop is not None and db_session_id is not None:
        tracker._db_pool = _CrossLoopPool(pool, db_loop)
        tracker._session_id = db_session_id

    # Start avatar
    await avatar.start(session, ctx.room)

    # Resolve agent from room name — goes directly to the subject tutor
    # when the frontend already selected a subject, falls back to router otherwise.
    agent = _resolve_agent(subject_key, grade)

    await session.start(
        room=ctx.room,
        agent=agent,
    )

    # ── End session on disconnect ────────────────────────────────────────
    _session_ended = False

    async def _end_db_session() -> None:
        nonlocal _session_ended
        if _session_ended or db_session_id is None or pool is None:
            return
        # Safe: no await between guard and flag — asyncio cooperative scheduling
        _session_ended = True
        try:
            # Flush pending tracker writes before ending session
            await tracker.flush()

            from src.db.sessions import end_session

            summary = tracker.summary if tracker.summary else None
            await _run_db_async(
                end_session(pool, db_session_id, summary_cache=summary),
            )
            logger.info("db_session_ended", db_session_id=str(db_session_id))

            # Fire-and-forget artifact generation after session ends.
            # Records are created only when we have data to populate them.
            async def _generate_artifacts() -> None:
                try:
                    from src.artifacts.generator import (
                        generate_cheat_sheet,
                        generate_summary,
                        generate_worksheet,
                    )
                    from src.db.artifacts import create_artifact

                    # The generator functions run on the LLM loop but need
                    # DB access internally.  Wrap the raw pool so asyncpg
                    # calls are bridged back to the DB loop transparently.
                    llm_pool = _CrossLoopPool(pool, db_loop)

                    summary_text = await _run_llm_async(
                        generate_summary(
                            llm_pool,
                            db_session_id,
                            summary_cache=summary,
                            groq_model=config.groq_model,
                            artifact_context_turns=config.artifact_context_turns,
                        ),
                    )
                    if not summary_text or not summary_text.strip():
                        logger.warning(
                            "artifacts_skipped_insufficient_data",
                            db_session_id=str(db_session_id),
                        )
                        return

                    # Create artifact records only when we have data.
                    # Summary record is created first and populated here
                    # (generate_summary only produces text, it doesn't
                    # know whether the record exists yet).
                    from src.db.artifacts import update_content

                    summary_id = await _run_db_async(
                        create_artifact(pool, db_session_id, "summary",
                                        "Session Summary"),
                    )
                    await _run_db_async(
                        update_content(pool, summary_id,
                                       content_json={"text": summary_text},
                                       status="ready"),
                    )

                    await _run_db_async(
                        create_artifact(pool, db_session_id, "cheat_sheet",
                                        f"Cheat Sheet: {subject_key}"),
                    )
                    await _run_db_async(
                        create_artifact(pool, db_session_id, "worksheet",
                                        f"Practice Worksheet: {subject_key}"),
                    )

                    await _run_llm_async(
                        generate_cheat_sheet(
                            llm_pool,
                            db_session_id,
                            summary_text,
                            subject_key,
                            grade or 7,
                            groq_model=config.groq_model,
                            artifact_context_turns=config.artifact_context_turns,
                        ),
                    )
                    await _run_llm_async(
                        generate_worksheet(
                            llm_pool,
                            db_session_id,
                            summary_text,
                            subject_key,
                            grade or 7,
                            groq_model=config.groq_model,
                            artifact_context_turns=config.artifact_context_turns,
                        ),
                    )
                    logger.info(
                        "artifacts_generated",
                        db_session_id=str(db_session_id),
                    )
                except Exception:
                    logger.warning("artifact_generation_failed", exc_info=True)

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_generate_artifacts())
            except RuntimeError:
                logger.warning("no_event_loop_for_artifact_generation")
        except Exception:
            logger.warning("db_session_end_failed", exc_info=True)

    @ctx.room.on("participant_disconnected")
    def _on_participant_left(participant) -> None:
        # Only end when the student leaves, not the agent.
        # Convention: agent identity starts with "agent", student with "student-"
        # (set in frontend/app/api/token/route.ts)
        identity = getattr(participant, "identity", "")
        if identity.startswith("agent"):
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_end_db_session())
        except RuntimeError:
            pass

    @ctx.room.on("disconnected")
    def _on_room_disconnected() -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_end_db_session())
        except RuntimeError:
            pass

    # Handle typed text input from the frontend (accessibility alternative to mic).
    # The frontend publishes UTF-8 text on the "chat_input" data channel topic.
    # We feed it into the agent session as user input via generate_reply().
    _MAX_CHAT_INPUT_BYTES = 4096

    @ctx.room.on("data_received")
    def _on_data_received(data_packet) -> None:
        topic = getattr(data_packet, "topic", None)
        if topic != "chat_input":
            return
        try:
            raw = data_packet.data
            if isinstance(raw, (bytes, bytearray)) and len(raw) > _MAX_CHAT_INPUT_BYTES:
                logger.warning(
                    "chat_input_too_large",
                    session_id=room_name,
                    byte_length=len(raw),
                    max_bytes=_MAX_CHAT_INPUT_BYTES,
                )
                return
            text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
            text = text.strip()
            if not text:
                return
            logger.info("text_input_received", session_id=room_name, length=len(text))
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                loop.create_task(session.generate_reply(user_input=text))
            else:
                logger.warning("no_event_loop_for_chat_input", session_id=room_name)
        except Exception as exc:
            error = PipelineError(
                stage=PipelineStage.SESSION,
                severity=ErrorSeverity.DEGRADED,
                message=f"Text input handling failed: {exc}",
                original_exception=exc,
            )
            handle_pipeline_error(error)

    # Initial greeting is triggered by the agent's on_enter() hook,
    # which the framework calls once the session activity is fully ready.

    logger.info("session_started", session_id=room_name)


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

    # Start dedicated LLM event loop — keeps Groq API calls off the DB loop
    _start_llm_loop()

    _start_health_server()
    logger.info("agent_server_starting")

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )
