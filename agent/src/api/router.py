"""HTTP API route handler for session records, artifacts, and flash cards.

Bridges the synchronous BaseHTTPRequestHandler to async DB operations
using asyncio.run() per request (safe because each request runs in its own thread).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

# Module-level DB reference — set during startup
_db = None

# Event loop shared with the DB pool — set during startup
_event_loop = None

# Shared-secret auth — set via set_api_secret(), falls back to env var
_api_secret: str | None = None


def set_event_loop(loop) -> None:
    """Capture the event loop that owns the DB pool."""
    global _event_loop
    _event_loop = loop


def set_db(db) -> None:
    """Set the module-level database reference."""
    global _db
    _db = db


def get_event_loop():
    """Return the current event loop (lazy read of module-level _event_loop)."""
    return _event_loop


def set_api_secret(secret: str | None) -> None:
    """Set the API secret for request authentication."""
    global _api_secret
    _api_secret = secret


def _check_auth(handler) -> bool:
    """Check X-API-Key header against API_SECRET. Skip if API_SECRET is unset (dev mode)."""
    effective_secret = _api_secret if _api_secret is not None else os.getenv("API_SECRET")
    if not effective_secret:
        return True
    token = handler.headers.get("X-API-Key", "") if handler else ""
    return token == effective_secret


def get_pool():
    """Return the DB pool or None if DB is not configured."""
    if _db is None:
        return None
    try:
        return _db.pool
    except RuntimeError:
        return None


def _json_serializer(obj: Any) -> Any:
    """JSON serializer for types not handled by default."""
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return None  # skip binary fields in JSON
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _parse_jsonb_strings(obj: Any) -> Any:
    """Pre-parse stringified JSONB fields returned by asyncpg.

    asyncpg returns ``jsonb`` columns as raw JSON strings instead of dicts.
    Without this step, ``json.dumps`` would double-encode them.
    """
    if isinstance(obj, dict):
        return {k: _parse_jsonb_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_parse_jsonb_strings(item) for item in obj]
    if isinstance(obj, str) and obj.startswith(("{", "[")):
        try:
            return json.loads(obj)
        except (json.JSONDecodeError, ValueError):
            pass
    return obj


def _json_response(data: Any, status: int = 200) -> tuple[bytes, int, str]:
    """Return (body_bytes, status_code, content_type)."""
    body = json.dumps(_parse_jsonb_strings(data), default=_json_serializer).encode()
    return body, status, "application/json"


def _error_response(message: str, status: int) -> tuple[bytes, int, str]:
    """Return a JSON error response."""
    return _json_response({"error": message}, status)


def _no_db_response() -> tuple[bytes, int, str]:
    """Return 503 when DB is not configured."""
    return _error_response("Database not configured", 503)


def _parse_uuid(value: str) -> UUID | None:
    """Safely parse a UUID string, returning None on failure."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


def _run_async(coro):
    """Run an async coroutine on the shared event loop that owns the DB pool."""
    if _event_loop is None:
        return asyncio.run(coro)
    future = asyncio.run_coroutine_threadsafe(coro, _event_loop)
    return future.result(timeout=30)


# ── Route patterns ──────────────────────────────────────────────────────────

_SESSIONS_LIST = re.compile(r"^/api/sessions$")
_SESSION_EVENTS = re.compile(r"^/api/sessions/([^/]+)/events$")
_SESSION_DETAIL = re.compile(r"^/api/sessions/([^/]+)$")
_SESSION_SUMMARY = re.compile(r"^/api/sessions/([^/]+)/summary$")
_SESSION_WORKSHEET = re.compile(r"^/api/sessions/([^/]+)/worksheet$")
_SESSION_CHEAT_SHEET = re.compile(r"^/api/sessions/([^/]+)/cheat-sheet$")
_SESSION_ARTIFACTS = re.compile(r"^/api/sessions/([^/]+)/artifacts$")
_SESSION_TRANSCRIPT = re.compile(r"^/api/sessions/([^/]+)/transcript$")
_SESSION_QUIZ_CHECK = re.compile(r"^/api/sessions/([^/]+)/review-quiz/check$")
_SESSION_REVIEW_QUIZ = re.compile(r"^/api/sessions/([^/]+)/review-quiz$")
_ARTIFACT_DETAIL = re.compile(r"^/api/artifacts/([^/]+)$")
_ARTIFACT_PDF = re.compile(r"^/api/artifacts/([^/]+)/pdf$")
_FLASH_CARDS_LIST = re.compile(r"^/api/flash-cards$")
_FLASH_CARDS_STATS = re.compile(r"^/api/flash-cards/stats$")
_FLASH_CARD_UPDATE = re.compile(r"^/api/flash-cards/([^/]+)$")
_UPLOADS_LIST = re.compile(r"^/api/uploads$")
_UPLOAD_DETAIL = re.compile(r"^/api/uploads/([^/]+)$")
_REVIEW_START = re.compile(r"^/api/review/([^/]+)/start$")
_REVIEW_MESSAGE = re.compile(r"^/api/review/([^/]+)/message$")
_REVIEW_HISTORY = re.compile(r"^/api/review/([^/]+)/history$")
_SESSION_FLASH_CARDS = re.compile(r"^/api/sessions/([^/]+)/flash-cards$")


def handle_get(path: str, handler=None) -> tuple[bytes, int, str] | None:
    """Handle GET requests. Returns (body, status, content_type) or None if unmatched."""
    if not _check_auth(handler):
        return _error_response("Unauthorized", 401)

    parsed = urlparse(path)
    url_path = parsed.path
    query = parse_qs(parsed.query)

    pool = get_pool()

    # GET /api/sessions?user_id=...
    match = _SESSIONS_LIST.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        user_id_str = query.get("user_id", [None])[0]
        if not user_id_str:
            return _error_response("user_id query parameter required", 400)
        user_id = _parse_uuid(user_id_str)
        if user_id is None:
            return _error_response("Invalid user_id UUID", 400)
        subject = query.get("subject", [None])[0]
        return _handle_list_sessions(pool, user_id, subject)

    # GET /api/flash-cards/stats?user_id=...
    match = _FLASH_CARDS_STATS.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        user_id_str = query.get("user_id", [None])[0]
        if not user_id_str:
            return _error_response("user_id query parameter required", 400)
        user_id = _parse_uuid(user_id_str)
        if user_id is None:
            return _error_response("Invalid user_id UUID", 400)
        return _handle_flash_card_stats(pool, user_id)

    # GET /api/flash-cards?user_id=...&subject=...
    match = _FLASH_CARDS_LIST.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        user_id_str = query.get("user_id", [None])[0]
        if not user_id_str:
            return _error_response("user_id query parameter required", 400)
        user_id = _parse_uuid(user_id_str)
        if user_id is None:
            return _error_response("Invalid user_id UUID", 400)
        subject = query.get("subject", [None])[0]
        return _handle_list_flash_cards(pool, user_id, subject)

    # GET /api/sessions/<id>/artifacts
    match = _SESSION_ARTIFACTS.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_session_artifacts(pool, session_id)

    # GET /api/sessions/<id>/transcript
    match = _SESSION_TRANSCRIPT.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_session_transcript(pool, session_id)

    # GET /api/artifacts/<id>/pdf
    match = _ARTIFACT_PDF.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        artifact_id = _parse_uuid(match.group(1))
        if artifact_id is None:
            return _error_response("Invalid artifact_id UUID", 400)
        return _handle_artifact_pdf(pool, artifact_id)

    # GET /api/artifacts/<id>
    match = _ARTIFACT_DETAIL.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        artifact_id = _parse_uuid(match.group(1))
        if artifact_id is None:
            return _error_response("Invalid artifact_id UUID", 400)
        return _handle_artifact_detail(pool, artifact_id)

    # GET /api/review/<upload_id>/start (SSE stream)
    match = _REVIEW_START.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        upload_id = _parse_uuid(match.group(1))
        if upload_id is None:
            return _error_response("Invalid upload_id UUID", 400)
        from src.api.upload_handlers import _handle_review_start
        return _handle_review_start(
            pool, upload_id,
            _error_response=_error_response, _run_async=_run_async,
        )

    # GET /api/review/<upload_id>/history
    match = _REVIEW_HISTORY.match(url_path)
    if match:
        upload_id = _parse_uuid(match.group(1))
        if upload_id is None:
            return _error_response("Invalid upload_id UUID", 400)
        from src.api.upload_handlers import _handle_review_history
        return _handle_review_history(
            upload_id,
            _json_response=_json_response, _error_response=_error_response,
        )

    # GET /api/uploads/<id>
    match = _UPLOAD_DETAIL.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        upload_id = _parse_uuid(match.group(1))
        if upload_id is None:
            return _error_response("Invalid upload_id UUID", 400)
        from src.api.upload_handlers import _handle_upload_detail
        return _handle_upload_detail(
            pool, upload_id,
            _json_response=_json_response, _error_response=_error_response,
            _run_async=_run_async,
        )

    # GET /api/sessions/<id>/review-quiz (SSE stream)
    match = _SESSION_REVIEW_QUIZ.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_review_quiz_stream(pool, session_id)

    # GET /api/sessions/<id>/events (JSON — artifact status snapshot)
    match = _SESSION_EVENTS.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_session_events(pool, session_id)

    # GET /api/sessions/<id>
    match = _SESSION_DETAIL.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_session_detail(pool, session_id)

    return None  # Not an API route


def handle_post(path: str, body: bytes, handler=None) -> tuple[bytes, int, str] | None:
    """Handle POST requests. Returns (body, status, content_type) or None if unmatched."""
    if not _check_auth(handler):
        return _error_response("Unauthorized", 401)

    parsed = urlparse(path)
    url_path = parsed.path

    pool = get_pool()

    # POST /api/sessions/<id>/review-quiz/check (must be before review-quiz)
    match = _SESSION_QUIZ_CHECK.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_quiz_check(pool, session_id, body)

    # POST /api/sessions/<id>/review-quiz
    match = _SESSION_REVIEW_QUIZ.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_review_quiz(pool, session_id)

    # POST /api/sessions/<id>/summary
    match = _SESSION_SUMMARY.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_generate_summary(pool, session_id)

    # POST /api/sessions/<id>/worksheet
    match = _SESSION_WORKSHEET.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_generate_worksheet(pool, session_id)

    # POST /api/sessions/<id>/cheat-sheet
    match = _SESSION_CHEAT_SHEET.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        return _handle_generate_cheat_sheet(pool, session_id)

    # POST /api/uploads
    match = _UPLOADS_LIST.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        from src.api.upload_handlers import _handle_create_upload
        return _handle_create_upload(
            pool, body, handler,
            _json_response=_json_response, _error_response=_error_response,
            _parse_uuid=_parse_uuid, _run_async=_run_async,
        )

    # POST /api/review/<upload_id>/message
    match = _REVIEW_MESSAGE.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        upload_id = _parse_uuid(match.group(1))
        if upload_id is None:
            return _error_response("Invalid upload_id UUID", 400)
        from src.api.upload_handlers import _handle_review_message
        return _handle_review_message(
            pool, upload_id, body,
            _json_response=_json_response, _error_response=_error_response,
            _run_async=_run_async,
        )

    # POST /api/sessions/<id>/flash-cards
    match = _SESSION_FLASH_CARDS.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        session_id = _parse_uuid(match.group(1))
        if session_id is None:
            return _error_response("Invalid session_id UUID", 400)
        from src.api.upload_handlers import _handle_generate_flash_cards
        return _handle_generate_flash_cards(
            pool, session_id, body,
            _json_response=_json_response, _error_response=_error_response,
            _parse_uuid=_parse_uuid, _run_async=_run_async,
        )

    return None


def handle_patch(path: str, body: bytes, handler=None) -> tuple[bytes, int, str] | None:
    """Handle PATCH requests. Returns (body, status, content_type) or None if unmatched."""
    if not _check_auth(handler):
        return _error_response("Unauthorized", 401)

    parsed = urlparse(path)
    url_path = parsed.path

    pool = get_pool()

    # PATCH /api/flash-cards/<id>
    match = _FLASH_CARD_UPDATE.match(url_path)
    if match:
        if pool is None:
            return _no_db_response()
        card_id = _parse_uuid(match.group(1))
        if card_id is None:
            return _error_response("Invalid card_id UUID", 400)
        return _handle_update_flash_card(pool, card_id, body)

    return None


# ── Handler implementations ────────────────────────────────────────────────


def _handle_list_sessions(
    pool, user_id: UUID, subject: str | None,
) -> tuple[bytes, int, str]:
    """List sessions for a user."""
    try:
        from src.db import sessions as sessions_db

        sessions = _run_async(
            sessions_db.list_sessions(pool, user_id, subject=subject),
        )
        return _json_response(sessions)
    except Exception:
        logger.exception("list_sessions_failed")
        return _error_response("Internal server error", 500)


def _handle_session_detail(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """Get session detail by id."""
    try:
        from src.db import sessions as sessions_db

        session = _run_async(sessions_db.get_session(pool, session_id))
        if session is None:
            return _error_response("Session not found", 404)
        return _json_response(session)
    except Exception:
        logger.exception("get_session_failed")
        return _error_response("Internal server error", 500)


def _handle_session_artifacts(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """List artifacts for a session."""
    try:
        from src.db import artifacts as artifacts_db

        artifacts = _run_async(artifacts_db.list_artifacts(pool, session_id))
        # Strip binary PDF data from list view
        cleaned = []
        for a in artifacts:
            row = {k: v for k, v in a.items() if k != "content_pdf"}
            cleaned.append(row)
        return _json_response(cleaned)
    except Exception:
        logger.exception("list_artifacts_failed")
        return _error_response("Internal server error", 500)


def _handle_session_transcript(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """Get transcript turns for a session."""
    try:
        from src.db import sessions as sessions_db

        turns = _run_async(sessions_db.get_turns(pool, session_id))
        return _json_response(turns)
    except Exception:
        logger.exception("get_transcript_failed")
        return _error_response("Internal server error", 500)


def _handle_session_events(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """Return current artifact statuses for a session."""
    try:
        from src.db import artifacts as artifacts_db

        artifacts = _run_async(artifacts_db.list_artifacts(pool, session_id))
        statuses = [
            {
                "artifact_type": a.get("artifact_type", "unknown"),
                "status": a.get("status", "unknown"),
            }
            for a in artifacts
        ]
        return _json_response(statuses)
    except Exception:
        logger.exception("session_events_failed")
        return _error_response("Internal server error", 500)


def _handle_artifact_detail(
    pool, artifact_id: UUID,
) -> tuple[bytes, int, str]:
    """Get a single artifact by id (without PDF binary)."""
    try:
        from src.db import artifacts as artifacts_db

        artifact = _run_async(artifacts_db.get_artifact(pool, artifact_id))
        if artifact is None:
            return _error_response("Artifact not found", 404)
        # Strip binary PDF from JSON response
        result = {k: v for k, v in artifact.items() if k != "content_pdf"}
        result["has_pdf"] = artifact.get("content_pdf") is not None
        return _json_response(result)
    except Exception:
        logger.exception("get_artifact_failed")
        return _error_response("Internal server error", 500)


def _handle_artifact_pdf(
    pool, artifact_id: UUID,
) -> tuple[bytes, int, str]:
    """Download artifact PDF."""
    try:
        from src.db import artifacts as artifacts_db

        artifact = _run_async(artifacts_db.get_artifact(pool, artifact_id))
        if artifact is None:
            return _error_response("Artifact not found", 404)
        pdf_bytes = artifact.get("content_pdf")
        if pdf_bytes is None:
            return _error_response("PDF not available for this artifact", 404)
        return pdf_bytes, 200, "application/pdf"
    except Exception:
        logger.exception("get_artifact_pdf_failed")
        return _error_response("Internal server error", 500)


def _handle_list_flash_cards(
    pool, user_id: UUID, subject: str | None,
) -> tuple[bytes, int, str]:
    """List flash cards for a user."""
    try:
        from src.db import flash_cards as flash_cards_db

        cards = _run_async(
            flash_cards_db.list_flash_cards(pool, user_id, subject=subject),
        )
        return _json_response(cards)
    except Exception:
        logger.exception("list_flash_cards_failed")
        return _error_response("Internal server error", 500)


def _handle_flash_card_stats(
    pool, user_id: UUID,
) -> tuple[bytes, int, str]:
    """Get flash card counts grouped by subject and mastery."""
    try:
        from src.db import flash_cards as flash_cards_db

        stats = _run_async(flash_cards_db.count_by_subject(pool, user_id))
        return _json_response(stats)
    except Exception:
        logger.exception("flash_card_stats_failed")
        return _error_response("Internal server error", 500)


def _handle_review_quiz(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """Generate a review quiz for a session."""
    try:
        from src.artifacts.generator import generate_review_quiz
        from src.config import AppConfig

        config = AppConfig.from_env()
        quiz = _run_async(
            generate_review_quiz(
                pool,
                session_id,
                artifact_llm_provider=config.artifact_llm_provider,
                artifact_llm_model=config.artifact_llm_model,
                artifact_context_turns=config.artifact_context_turns,
            ),
        )
        return _json_response(quiz, 201)
    except ValueError:
        return _error_response("Session not found", 404)
    except Exception:
        logger.exception("review_quiz_generation_failed")
        return _error_response("Internal server error", 500)


def _handle_generate_summary(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """Generate a session summary on demand."""
    try:
        from src.artifacts.generator import generate_summary
        from src.config import AppConfig
        from src.db import artifacts as artifacts_db
        from src.db import sessions as sessions_db

        config = AppConfig.from_env()
        session = _run_async(sessions_db.get_session(pool, session_id))
        if session is None:
            return _error_response("Session not found", 404)

        # Ensure artifact record exists before generating
        existing = _run_async(artifacts_db.list_artifacts(pool, session_id))
        if not any(a["artifact_type"] == "summary" for a in existing):
            _run_async(artifacts_db.create_artifact(
                pool, session_id, "summary", "Session Summary",
            ))

        summary_text = _run_async(
            generate_summary(
                pool, session_id,
                summary_cache=session.get("summary_cache"),
                artifact_llm_provider=config.artifact_llm_provider,
                artifact_llm_model=config.artifact_llm_model,
                artifact_context_turns=config.artifact_context_turns,
            ),
        )
        if not summary_text or not summary_text.strip():
            return _error_response("Not enough conversation data to generate summary", 400)
        return _json_response({"summary": summary_text}, 201)
    except ValueError:
        return _error_response("Session not found", 404)
    except Exception:
        logger.exception("summary_generation_failed")
        return _error_response("Internal server error", 500)


def _handle_generate_worksheet(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """Generate a worksheet for a session on demand."""
    try:
        from src.artifacts.generator import generate_summary, generate_worksheet
        from src.config import AppConfig
        from src.db import artifacts as artifacts_db
        from src.db import sessions as sessions_db

        config = AppConfig.from_env()

        session = _run_async(sessions_db.get_session(pool, session_id))
        if session is None:
            return _error_response("Session not found", 404)
        subject = session.get("subject", "general")
        grade = session.get("grade", 7)

        # Ensure artifact records exist
        existing = _run_async(artifacts_db.list_artifacts(pool, session_id))
        existing_types = {a["artifact_type"] for a in existing}
        if "summary" not in existing_types:
            _run_async(artifacts_db.create_artifact(
                pool, session_id, "summary", "Session Summary",
            ))
        if "worksheet" not in existing_types:
            _run_async(artifacts_db.create_artifact(
                pool, session_id, "worksheet", f"Practice Worksheet: {subject}",
            ))

        # Reuse existing summary if ready, else generate
        summary_art = next(
            (a for a in existing if a["artifact_type"] == "summary" and a.get("status") == "ready"),
            None,
        )
        if summary_art and isinstance(summary_art.get("content_json"), dict):
            summary_text = summary_art["content_json"].get("text", "")
        else:
            summary_text = _run_async(
                generate_summary(
                    pool, session_id,
                    summary_cache=session.get("summary_cache"),
                    artifact_llm_provider=config.artifact_llm_provider,
                    artifact_llm_model=config.artifact_llm_model,
                    artifact_context_turns=config.artifact_context_turns,
                ),
            )
        if not summary_text or not summary_text.strip():
            return _error_response("Not enough conversation data to generate worksheet", 400)

        worksheet = _run_async(
            generate_worksheet(
                pool, session_id, summary_text, subject, grade,
                artifact_llm_provider=config.artifact_llm_provider,
                artifact_llm_model=config.artifact_llm_model,
                artifact_context_turns=config.artifact_context_turns,
            ),
        )
        return _json_response(worksheet, 201)
    except ValueError:
        return _error_response("Session not found", 404)
    except Exception:
        logger.exception("worksheet_generation_failed")
        return _error_response("Internal server error", 500)


def _handle_generate_cheat_sheet(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """Generate a cheat sheet for a session on demand."""
    try:
        from src.artifacts.generator import generate_cheat_sheet, generate_summary
        from src.config import AppConfig
        from src.db import artifacts as artifacts_db
        from src.db import sessions as sessions_db

        config = AppConfig.from_env()

        session = _run_async(sessions_db.get_session(pool, session_id))
        if session is None:
            return _error_response("Session not found", 404)
        subject = session.get("subject", "general")
        grade = session.get("grade", 7)

        # Ensure artifact records exist
        existing = _run_async(artifacts_db.list_artifacts(pool, session_id))
        existing_types = {a["artifact_type"] for a in existing}
        if "summary" not in existing_types:
            _run_async(artifacts_db.create_artifact(
                pool, session_id, "summary", "Session Summary",
            ))
        if "cheat_sheet" not in existing_types:
            _run_async(artifacts_db.create_artifact(
                pool, session_id, "cheat_sheet", f"Cheat Sheet: {subject}",
            ))

        # Reuse existing summary if ready, else generate
        summary_art = next(
            (a for a in existing if a["artifact_type"] == "summary" and a.get("status") == "ready"),
            None,
        )
        if summary_art and isinstance(summary_art.get("content_json"), dict):
            summary_text = summary_art["content_json"].get("text", "")
        else:
            summary_text = _run_async(
                generate_summary(
                    pool, session_id,
                    summary_cache=session.get("summary_cache"),
                    artifact_llm_provider=config.artifact_llm_provider,
                    artifact_llm_model=config.artifact_llm_model,
                    artifact_context_turns=config.artifact_context_turns,
                ),
            )
        if not summary_text or not summary_text.strip():
            return _error_response("Not enough conversation data to generate cheat sheet", 400)

        cheat_sheet = _run_async(
            generate_cheat_sheet(
                pool, session_id, summary_text, subject, grade,
                artifact_llm_provider=config.artifact_llm_provider,
                artifact_llm_model=config.artifact_llm_model,
                artifact_context_turns=config.artifact_context_turns,
            ),
        )
        return _json_response(cheat_sheet, 201)
    except ValueError:
        return _error_response("Session not found", 404)
    except Exception:
        logger.exception("cheat_sheet_generation_failed")
        return _error_response("Internal server error", 500)


def _handle_review_quiz_stream(
    pool, session_id: UUID,
) -> tuple[bytes, int, str]:
    """Handle GET /api/sessions/<id>/review-quiz — SSE stream for quiz generation."""
    try:
        from src.artifacts.generator import generate_review_quiz
        from src.config import AppConfig
        from src.sse.events import format_sse_done

        config = AppConfig.from_env()
        quiz = _run_async(
            generate_review_quiz(
                pool,
                session_id=session_id,
                artifact_llm_provider=config.artifact_llm_provider,
                artifact_llm_model=config.artifact_llm_model,
                artifact_context_turns=config.artifact_context_turns,
            ),
        )
        # Emit the full quiz as a single "done" event
        import json as json_mod
        full_text = json_mod.dumps(quiz, default=_json_serializer)
        body = format_sse_done(full_text)
        return body.encode(), 200, "text/event-stream; charset=utf-8"
    except ValueError:
        return _error_response("Session not found", 404)
    except Exception:
        logger.exception("review_quiz_stream_failed")
        return _error_response("Internal server error", 500)


def _handle_quiz_check(
    pool, session_id: UUID, body: bytes,
) -> tuple[bytes, int, str]:
    """Check submitted quiz answers against the review quiz for a session."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return _error_response("Invalid JSON body", 400)

    answers: dict[str, str] = payload.get("answers", {})
    if not isinstance(answers, dict) or not answers:
        return _error_response("answers dict (question_id -> answer) is required", 400)

    try:
        from src.db import artifacts as artifacts_db

        artifacts = _run_async(artifacts_db.list_artifacts(pool, session_id))

        # Find the ready review_quiz artifact
        quiz_artifact = None
        for a in artifacts:
            if a.get("artifact_type") == "review_quiz" and a.get("status") == "ready":
                quiz_artifact = a
                break

        if quiz_artifact is None:
            return _error_response("No ready review quiz found for this session", 404)

        # Parse the quiz content
        content_json = quiz_artifact.get("content_json")
        if isinstance(content_json, str):
            content = json.loads(content_json)
        elif isinstance(content_json, dict):
            content = content_json
        else:
            return _error_response("Invalid quiz content", 500)

        _MAX_QUESTIONS = 100
        _MAX_ACCEPT_ALSO = 20

        questions = content.get("questions", [])[:_MAX_QUESTIONS]
        if not questions:
            return _error_response("Quiz has no questions", 500)

        # Check each answer
        results: list[dict[str, Any]] = []
        score = 0
        for q in questions:
            q_id = str(q.get("id", ""))
            correct_answer = str(q.get("correct_answer", ""))
            accept_also: list[str] = q.get("accept_also", [])

            student_answer = answers.get(q_id, "").strip().lower()

            # Build list of acceptable answers (case-insensitive, stripped)
            acceptable = {correct_answer.strip().lower()}
            for alt in accept_also[:_MAX_ACCEPT_ALSO]:
                acceptable.add(str(alt).strip().lower())

            is_correct = student_answer in acceptable
            if is_correct:
                score += 1

            results.append({
                "id": q_id,
                "correct": is_correct,
                "correct_answer": correct_answer,
            })

        return _json_response({
            "score": score,
            "total": len(questions),
            "results": results,
        })

    except Exception:
        logger.exception("quiz_check_failed")
        return _error_response("Internal server error", 500)


def _handle_update_flash_card(
    pool, card_id: UUID, body: bytes,
) -> tuple[bytes, int, str]:
    """Update flash card mastery."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return _error_response("Invalid JSON body", 400)

    mastery = payload.get("mastery")
    valid_levels = {"new", "learning", "known"}
    if mastery not in valid_levels:
        return _error_response(
            f"mastery must be one of: {', '.join(sorted(valid_levels))}", 400,
        )

    try:
        from src.db import flash_cards as flash_cards_db

        _run_async(flash_cards_db.update_mastery(pool, card_id, mastery))
        return _json_response({"ok": True, "card_id": str(card_id), "mastery": mastery})
    except Exception:
        logger.exception("update_flash_card_failed")
        return _error_response("Internal server error", 500)
