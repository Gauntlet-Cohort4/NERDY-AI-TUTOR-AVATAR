"""Upload processing: extract text and classify student-uploaded files.

Supports images (via Groq vision model) and PDFs (via PyMuPDF text extraction
then Groq LLM classification). Updates the uploads table with results.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import structlog

from src.db import uploads as uploads_db
from src.utils.llm import extract_json, get_groq_client

logger = structlog.get_logger(__name__)

# ── File type validation via magic bytes ────────────────────────────────────

_PDF_MAGIC = b"%PDF"
_PNG_MAGIC = b"\x89PNG"
_JPEG_MAGIC = b"\xff\xd8\xff"

_ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg"}

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def sniff_file_type(data: bytes) -> str | None:
    """Detect file type from magic bytes. Returns MIME type or None."""
    if data[:4] == _PDF_MAGIC:
        return "application/pdf"
    if data[:4] == _PNG_MAGIC:
        return "image/png"
    if data[:3] == _JPEG_MAGIC:
        return "image/jpeg"
    return None


# ── Valid subjects for classification output ─────────────────────────────────

_VALID_SUBJECTS = {
    "math", "biology", "physics", "chemistry",
    "earth_science", "world_history", "general",
}

_CLASSIFICATION_PROMPT = """Analyze this student's homework/assignment.  Return ONLY valid JSON with this structure:

{
  "subject": "math",
  "grade": 8,
  "overall_topic": "linear equations",
  "problems_found": [
    {
      "number": 1,
      "question_text": "...",
      "student_answer": "...",
      "answer_is_correct": null,
      "topic": "..."
    }
  ],
  "notes": "..."
}

Rules:
- "subject" must be one of: "math", "biology", "physics", or "general"
- "grade" is the estimated US grade level (1-12)
- For each problem, include the question text and the student's written answer if visible
- Set "answer_is_correct" to true, false, or null if you cannot determine
- "notes" is a brief summary of what you see

Respond with valid JSON only. No markdown fences."""


async def _classify_with_vision(
    file_data: bytes,
    file_type: str,
    groq_vision_model: str,
) -> dict[str, Any]:
    """Send an image to Groq vision model for text extraction and classification."""
    if len(file_data) > _MAX_UPLOAD_BYTES:
        raise ValueError(f"Image too large for vision classification ({len(file_data)} bytes)")

    media_type = "image/png" if "png" in file_type.lower() else "image/jpeg"
    b64_data = base64.b64encode(file_data).decode("ascii")

    client = get_groq_client()
    response = await client.chat.completions.create(
        model=groq_vision_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _CLASSIFICATION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{b64_data}",
                        },
                    },
                ],
            },
        ],
        max_tokens=2000,
    )
    raw_text = response.choices[0].message.content or "{}"
    return extract_json(raw_text)


def _extract_pdf_text_sync(file_data: bytes) -> str:
    """Extract text from a PDF using PyMuPDF (fitz). Synchronous."""
    import fitz  # PyMuPDF

    pages: list[str] = []
    with fitz.open(stream=file_data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text.strip())
    return "\n\n".join(pages)


async def _extract_pdf_text(file_data: bytes) -> str:
    """Extract text from a PDF, offloaded to a thread to avoid blocking."""
    return await asyncio.to_thread(_extract_pdf_text_sync, file_data)


async def _classify_text(
    extracted_text: str,
    groq_model: str,
) -> dict[str, Any]:
    """Send extracted text to Groq LLM for classification."""
    prompt = f"""Here is text extracted from a student's uploaded document:

---
{extracted_text[:4000]}
---

{_CLASSIFICATION_PROMPT}"""

    client = get_groq_client()
    response = await client.chat.completions.create(
        model=groq_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    raw_text = response.choices[0].message.content or "{}"
    return extract_json(raw_text)


async def process_upload(
    pool,
    upload_id,
    file_data: bytes,
    file_type: str,
    groq_model: str,
    groq_vision_model: str,
) -> dict[str, Any]:
    """Process an uploaded file: extract text, classify, and update the DB.

    Returns the classification dict on success, or an error dict on failure.
    """
    logger.info(
        "upload_processing_started",
        upload_id=str(upload_id),
        file_type=file_type,
    )

    # Reject files that exceed size limit
    if len(file_data) > _MAX_UPLOAD_BYTES:
        logger.warning("upload_too_large", upload_id=str(upload_id), size=len(file_data))
        await uploads_db.update_classification(
            pool, upload_id,
            extracted_text="(file too large)",
            detected_subject="general",
            detected_grade=0,
            status="error",
        )
        return {"error": "File too large (max 10 MB)"}

    # Validate file type via magic bytes
    sniffed = sniff_file_type(file_data)
    if sniffed is None or sniffed not in _ALLOWED_TYPES:
        logger.warning(
            "upload_invalid_file_type",
            upload_id=str(upload_id),
            sniffed=sniffed,
        )
        await uploads_db.update_classification(
            pool, upload_id,
            extracted_text="(unsupported file type)",
            detected_subject="general",
            detected_grade=0,
            status="error",
        )
        return {"error": "Unsupported file type"}

    try:
        is_pdf = "pdf" in file_type.lower()

        if is_pdf:
            extracted_text = await _extract_pdf_text(file_data)
            if not extracted_text.strip():
                logger.warning("pdf_no_text_extracted", upload_id=str(upload_id))
                extracted_text = "(No readable text found in PDF)"
            classification = await _classify_text(extracted_text, groq_model)
        else:
            # Image — use vision model
            classification = await _classify_with_vision(
                file_data, file_type, groq_vision_model,
            )
            # Build extracted text from the classification for storage
            problems = classification.get("problems_found", [])
            parts = [
                f"Subject: {classification.get('subject', 'unknown')}",
                f"Topic: {classification.get('overall_topic', 'unknown')}",
                "",
            ]
            for p in problems:
                parts.append(
                    f"Q{p.get('number', '?')}: {p.get('question_text', '')} "
                    f"— Student answer: {p.get('student_answer', 'N/A')}"
                )
            extracted_text = "\n".join(parts)

        # Update the DB record (validate subject against whitelist)
        detected_subject = classification.get("subject", "general")
        if detected_subject not in _VALID_SUBJECTS:
            detected_subject = "general"
        detected_grade = classification.get("grade", 0)
        if not isinstance(detected_grade, int):
            try:
                detected_grade = int(detected_grade)
            except (ValueError, TypeError):
                detected_grade = 0

        await uploads_db.update_classification(
            pool,
            upload_id,
            extracted_text=extracted_text,
            detected_subject=detected_subject,
            detected_grade=detected_grade,
            status="classified",
        )

        logger.info(
            "upload_processing_complete",
            upload_id=str(upload_id),
            detected_subject=detected_subject,
            detected_grade=detected_grade,
            problems_found=len(classification.get("problems_found", [])),
        )
        return classification

    except json.JSONDecodeError:
        logger.exception("upload_classification_json_failed", upload_id=str(upload_id))
        await uploads_db.update_classification(
            pool, upload_id,
            extracted_text="(classification failed — invalid LLM output)",
            detected_subject="general",
            detected_grade=0,
            status="error",
        )
        return {"error": "Failed to parse classification output"}

    except Exception:
        logger.exception("upload_processing_failed", upload_id=str(upload_id))
        try:
            await uploads_db.update_classification(
                pool, upload_id,
                extracted_text="(processing failed)",
                detected_subject="general",
                detected_grade=0,
                status="error",
            )
        except Exception:
            logger.exception("upload_error_update_failed", upload_id=str(upload_id))
        return {"error": "Upload processing failed"}
