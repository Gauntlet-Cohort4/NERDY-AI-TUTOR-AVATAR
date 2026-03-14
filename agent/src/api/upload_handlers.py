"""Upload & Review HTTP handlers extracted from router.py.

These handlers manage file uploads, background classification,
document review chat, and flash card generation.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


def _parse_multipart(body: bytes, content_type: str) -> dict[str, Any]:
    """Parse multipart/form-data body into a dict of fields.

    Returns {field_name: value} where value is bytes for file fields
    and str for text fields.
    """
    from email.parser import BytesParser
    from email.policy import default as default_policy

    # Build a full MIME message so the email parser can handle it
    raw = b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body
    parser = BytesParser(policy=default_policy)
    msg = parser.parsebytes(raw)

    fields: dict[str, Any] = {}
    if msg.is_multipart():
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if name is None:
                continue
            filename = part.get_filename()
            payload = part.get_payload(decode=True)
            if filename:
                fields[name] = payload
                fields[f"{name}_filename"] = filename
                fields[f"{name}_content_type"] = part.get_content_type()
            else:
                fields[name] = payload.decode("utf-8", errors="replace") if payload else ""
    return fields


def _handle_create_upload(
    pool, body: bytes, handler=None,
    *, _json_response, _error_response, _parse_uuid, _run_async,
) -> tuple[bytes, int, str]:
    """Handle POST /api/uploads -- accept multipart form data."""
    content_type = ""
    if handler:
        content_type = handler.headers.get("Content-Type", "")

    if "multipart/form-data" not in content_type:
        return _error_response("Content-Type must be multipart/form-data", 400)

    try:
        fields = _parse_multipart(body, content_type)
    except Exception:
        logger.exception("multipart_parse_failed")
        return _error_response("Failed to parse multipart data", 400)

    user_id_str = fields.get("user_id", "")
    user_id = _parse_uuid(user_id_str)
    if user_id is None:
        return _error_response("user_id is required and must be a valid UUID", 400)

    file_data = fields.get("file")
    if not file_data or not isinstance(file_data, bytes):
        return _error_response("file is required", 400)

    _MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
    if len(file_data) > _MAX_UPLOAD_BYTES:
        return _error_response("File too large (max 10 MB)", 413)

    file_name = fields.get("file_filename", "upload")
    file_type = fields.get("file_content_type", "application/octet-stream")

    # Validate file type via magic bytes
    from src.uploads.processor import sniff_file_type

    _ALLOWED_UPLOAD_TYPES = {"application/pdf", "image/png", "image/jpeg"}
    sniffed = sniff_file_type(file_data)
    if sniffed is None or sniffed not in _ALLOWED_UPLOAD_TYPES:
        return _error_response(
            "Unsupported file type. Allowed: PDF, PNG, JPEG", 415,
        )

    session_id_str = fields.get("session_id", "")
    session_id = _parse_uuid(session_id_str) if session_id_str else None

    try:
        from src.db import uploads as uploads_db

        # Store the upload
        upload_id = _run_async(
            uploads_db.create_upload(
                pool,
                user_id=user_id,
                file_name=file_name,
                file_type=file_type,
                file_data=file_data,
                session_id=session_id,
            ),
        )

        # Kick off async classification (fire-and-forget on the event loop)
        _schedule_classification(
            pool, upload_id, file_data, file_type,
            _run_async=_run_async,
        )

        upload = _run_async(uploads_db.get_upload(pool, upload_id))
        result = {
            k: v for k, v in (upload or {}).items() if k != "file_data"
        }
        return _json_response(result, 201)

    except Exception:
        logger.exception("create_upload_failed")
        return _error_response("Internal server error", 500)


def _schedule_classification(
    pool, upload_id, file_data: bytes, file_type: str,
    *, _run_async,
) -> None:
    """Schedule upload classification as a background task on the event loop."""
    try:
        from src.api.router import get_event_loop
        from src.config import AppConfig
        from src.uploads.processor import process_upload

        config = AppConfig.from_env()

        async def _classify():
            try:
                await process_upload(
                    pool,
                    upload_id,
                    file_data=file_data,
                    file_type=file_type,
                    groq_model=config.groq_model,
                    groq_vision_model=config.groq_vision_model,
                )
            except Exception:
                logger.exception(
                    "background_classification_failed",
                    upload_id=str(upload_id),
                )

        event_loop = get_event_loop()
        if event_loop is not None:
            future = asyncio.run_coroutine_threadsafe(_classify(), event_loop)
            future.add_done_callback(
                lambda f: f.exception() if not f.cancelled() else None,
            )
        else:
            # Fallback: run synchronously (dev mode)
            _run_async(_classify())
    except Exception:
        logger.exception(
            "schedule_classification_failed",
            upload_id=str(upload_id),
        )


def _handle_upload_detail(
    pool, upload_id: UUID,
    *, _json_response, _error_response, _run_async,
) -> tuple[bytes, int, str]:
    """Handle GET /api/uploads/<id>."""
    try:
        from src.db import uploads as uploads_db

        upload = _run_async(uploads_db.get_upload(pool, upload_id))
        if upload is None:
            return _error_response("Upload not found", 404)
        # Strip binary file_data from JSON response
        result = {k: v for k, v in upload.items() if k != "file_data"}
        return _json_response(result)
    except Exception:
        logger.exception("get_upload_failed")
        return _error_response("Internal server error", 500)


def _handle_review_start(
    pool, upload_id: UUID,
    *, _error_response, _run_async,
) -> tuple[bytes, int, str]:
    """Handle GET /api/review/<upload_id>/start -- SSE stream."""
    try:
        from src.config import AppConfig
        from src.review.chat import start_review

        config = AppConfig.from_env()

        async def _collect():
            chunks: list[str] = []
            async for event in start_review(pool, upload_id, config.groq_model):
                chunks.append(event)
            return "".join(chunks)

        sse_body = _run_async(_collect())
        return (
            sse_body.encode(),
            200,
            "text/event-stream; charset=utf-8",
        )
    except Exception:
        logger.exception("review_start_failed")
        return _error_response("Internal server error", 500)


def _handle_review_message(
    pool, upload_id: UUID, body: bytes,
    *, _json_response, _error_response, _run_async,
) -> tuple[bytes, int, str]:
    """Handle POST /api/review/<upload_id>/message -- SSE stream."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return _error_response("Invalid JSON body", 400)

    message = payload.get("message", "").strip()
    if not message:
        return _error_response("message field is required", 400)

    _MAX_MESSAGE_LENGTH = 2000
    if len(message) > _MAX_MESSAGE_LENGTH:
        return _error_response(f"Message too long (max {_MAX_MESSAGE_LENGTH} chars)", 400)

    try:
        from src.config import AppConfig
        from src.review.chat import send_message

        config = AppConfig.from_env()

        async def _collect():
            chunks: list[str] = []
            async for event in send_message(
                pool, upload_id, message, config.groq_model,
            ):
                chunks.append(event)
            return "".join(chunks)

        sse_body = _run_async(_collect())
        return (
            sse_body.encode(),
            200,
            "text/event-stream; charset=utf-8",
        )
    except Exception:
        logger.exception("review_message_failed")
        return _error_response("Internal server error", 500)


def _handle_review_history(
    upload_id: UUID,
    *, _json_response, _error_response,
) -> tuple[bytes, int, str]:
    """Handle GET /api/review/<upload_id>/history."""
    try:
        from src.review.chat import get_history

        history = get_history(str(upload_id))
        # Filter out system messages for the client
        visible = [
            turn for turn in history if turn["role"] != "system"
        ]
        return _json_response(visible)
    except Exception:
        logger.exception("review_history_failed")
        return _error_response("Internal server error", 500)


def _handle_generate_flash_cards(
    pool, session_id: UUID, body: bytes,
    *, _json_response, _error_response, _parse_uuid, _run_async,
) -> tuple[bytes, int, str]:
    """Handle POST /api/sessions/<id>/flash-cards."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return _error_response("Invalid JSON body", 400)

    user_id_str = payload.get("user_id", "")
    user_id = _parse_uuid(user_id_str)
    if user_id is None:
        return _error_response("user_id is required and must be a valid UUID", 400)

    try:
        from src.artifacts.generator import generate_flash_cards
        from src.config import AppConfig

        config = AppConfig.from_env()
        cards = _run_async(
            generate_flash_cards(
                pool,
                session_id=session_id,
                user_id=user_id,
                groq_model=config.groq_model,
                artifact_context_turns=config.artifact_context_turns,
            ),
        )
        return _json_response({"flash_cards": cards}, 201)
    except ValueError:
        return _error_response("Session not found", 404)
    except Exception:
        logger.exception("generate_flash_cards_failed")
        return _error_response("Internal server error", 500)
