"""Artifact generation: summary, cheat sheet, worksheet, review quiz.

All generators read from the database (summary_cache + recent turns),
NOT from in-memory ConversationHistory which may only hold a rolling window.

Uses Claude Sonnet (via Anthropic API) for higher-quality artifact generation.
Falls back to Groq/Llama if ANTHROPIC_API_KEY is not set.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from src.db import artifacts as artifacts_db
from src.db import flash_cards as flash_cards_db
from src.db import sessions as sessions_db
from src.utils.llm import extract_json, get_anthropic_client, get_groq_client

logger = structlog.get_logger(__name__)


_MAX_TURN_CHARS = 500


async def _llm_generate(prompt: str, provider: str, model: str, max_tokens: int) -> str:
    """Call the configured artifact LLM provider.

    Supports "anthropic" and "groq". Falls back to Groq on Anthropic failure.
    """
    if provider == "anthropic":
        anthropic = get_anthropic_client()
        if anthropic is not None:
            try:
                response = await anthropic.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                logger.debug("artifact_llm_call", provider="anthropic", model=model)
                return response.content[0].text
            except Exception:
                logger.warning("anthropic_artifact_failed_falling_back_to_groq", exc_info=True)
        # Fall through to groq

    client = get_groq_client()
    groq_model = model if provider == "groq" else "llama-3.3-70b-versatile"
    response = await client.chat.completions.create(
        model=groq_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    logger.debug("artifact_llm_call", provider="groq", model=groq_model)
    return response.choices[0].message.content or ""

# Minimum student (user) turns required before artifact generation is useful.
_MIN_STUDENT_TURNS = 2


def _format_turns(turns: list[dict[str, Any]]) -> str:
    """Format transcript turn dicts into readable text, truncating long turns."""
    return "\n".join(
        f"{t['role']}: {t['content'][:_MAX_TURN_CHARS]}" for t in turns
    )


def _count_student_turns(turns: list[dict[str, Any]]) -> int:
    """Count turns from the student/user role."""
    return sum(1 for t in turns if t.get("role") in ("student", "user"))


def _not_enough_data_response(session_id: str, artifact_type: str) -> dict[str, Any]:
    """Return a standard 'not enough conversation' error dict."""
    logger.info(
        "artifact_skipped_insufficient_turns",
        session_id=str(session_id),
        artifact_type=artifact_type,
        min_required=_MIN_STUDENT_TURNS,
    )
    return {
        "error": "Not enough conversation yet",
        "detail": f"At least {_MIN_STUDENT_TURNS} student messages are needed "
        "before generating study materials.",
    }


async def generate_summary(
    pool,
    session_id,
    summary_cache: str | None,
    artifact_llm_provider: str = "anthropic",
    artifact_llm_model: str = "claude-sonnet-4-5-20250929",
    artifact_context_turns: int = 20,
) -> str:
    """Generate a session summary from summary_cache + recent turns."""
    recent_turns = await sessions_db.get_recent_turns(
        pool, session_id, limit=artifact_context_turns,
    )
    recent_turns.reverse()  # chronological order

    if _count_student_turns(recent_turns) < _MIN_STUDENT_TURNS:
        _not_enough_data_response(session_id, "summary")  # logs the skip
        return ""

    prompt = f"""Summarize this AI tutoring session.

Rolling summary of earlier conversation:
{summary_cache or "No earlier context."}

Most recent exchanges:
{_format_turns(recent_turns)}

Produce:
1. **Key Topics Covered** — 2-4 bullet points
2. **Student Understanding** — where student showed strong grasp vs. struggled
3. **Recommended Next Steps** — what to study or practice next

Under 200 words. Write for the student ("you learned...", "you should review...")."""

    summary_text = await _llm_generate(prompt, artifact_llm_provider, artifact_llm_model, max_tokens=500)

    logger.info(
        "summary_generated",
        session_id=str(session_id),
        length=len(summary_text),
    )
    return summary_text


async def generate_cheat_sheet(
    pool,
    session_id,
    summary: str,
    subject: str,
    grade: int,
    artifact_llm_provider: str = "anthropic",
    artifact_llm_model: str = "claude-sonnet-4-5-20250929",
    artifact_context_turns: int = 20,
) -> dict[str, Any]:
    """Generate a structured cheat sheet from session content."""
    recent_turns = await sessions_db.get_recent_turns(
        pool, session_id, limit=artifact_context_turns,
    )
    recent_turns.reverse()

    if _count_student_turns(recent_turns) < _MIN_STUDENT_TURNS:
        return _not_enough_data_response(session_id, "cheat_sheet")

    prompt = f"""Based on this {subject} tutoring session (grade {grade}), create a study cheat sheet.

Summary: {summary}
Recent exchanges: {_format_turns(recent_turns)}

Format as JSON:
{{
  "title": "Cheat Sheet: [Topic]",
  "session_label": "{subject} — Grade {grade}",
  "key_concepts": [{{"term": "...", "definition": "...", "example": "..."}}],
  "formulas": [{{"name": "...", "latex": "...", "when_to_use": "..."}}],
  "common_mistakes": ["..."],
  "memory_aids": ["..."],
  "quick_reference_steps": [{{"step": 1, "description": "..."}}]
}}

Include ONLY content actually covered. Respond with valid JSON only."""

    content_text = await _llm_generate(prompt, artifact_llm_provider, artifact_llm_model, max_tokens=1000)
    try:
        content_json: dict[str, Any] = extract_json(content_text)
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "cheat_sheet_json_parse_failed",
            session_id=str(session_id),
            raw_text=content_text[:200],
        )
        # Mark pre-created artifact as error
        artifacts = await artifacts_db.list_artifacts(pool, session_id)
        cs_artifact = next(
            (a for a in artifacts if a["artifact_type"] == "cheat_sheet"), None,
        )
        if cs_artifact:
            await artifacts_db.update_content(
                pool, cs_artifact["id"],
                content_json={"error": "Failed to parse LLM output"}, status="error",
            )
        return {"error": "Failed to parse LLM output"}

    artifacts = await artifacts_db.list_artifacts(pool, session_id)
    cs_artifact = next(
        (a for a in artifacts if a["artifact_type"] == "cheat_sheet"), None,
    )
    if cs_artifact:
        await artifacts_db.update_content(
            pool, cs_artifact["id"], content_json=content_json, status="ready",
        )
    else:
        logger.warning("cheat_sheet_artifact_not_found", session_id=str(session_id))

    logger.info("cheat_sheet_generated", session_id=str(session_id))
    return content_json


async def generate_worksheet(
    pool,
    session_id,
    summary: str,
    subject: str,
    grade: int,
    artifact_llm_provider: str = "anthropic",
    artifact_llm_model: str = "claude-sonnet-4-5-20250929",
    artifact_context_turns: int = 20,
) -> dict[str, Any]:
    """Generate a practice worksheet with 8-12 problems."""
    recent_turns = await sessions_db.get_recent_turns(
        pool, session_id, limit=artifact_context_turns,
    )
    recent_turns.reverse()  # chronological order
    if _count_student_turns(recent_turns) < _MIN_STUDENT_TURNS:
        return _not_enough_data_response(session_id, "worksheet")

    prompt = f"""Based on this {subject} tutoring session (grade {grade}), create a practice worksheet.

Summary: {summary}

Create 8-12 problems. Format as JSON:
{{
  "title": "Practice Worksheet: [Topic]",
  "instructions": "...",
  "problems": [{{
    "number": 1,
    "question": "...",
    "question_latex": null,
    "type": "multiple_choice",
    "options": ["A) ...", "B) ..."],
    "answer": "...",
    "explanation": "...",
    "difficulty": "easy"
  }}],
  "difficulty_distribution": "Start easy, build to harder."
}}

Mix: ~30% easy, ~50% medium, ~20% hard. Include LaTeX for math. Valid JSON only."""

    content_text = await _llm_generate(prompt, artifact_llm_provider, artifact_llm_model, max_tokens=2000)
    try:
        content_json: dict[str, Any] = extract_json(content_text)
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "worksheet_json_parse_failed",
            session_id=str(session_id),
            raw_text=content_text[:200],
        )
        # Mark pre-created artifact as error
        artifacts = await artifacts_db.list_artifacts(pool, session_id)
        ws_artifact = next(
            (a for a in artifacts if a["artifact_type"] == "worksheet"), None,
        )
        if ws_artifact:
            await artifacts_db.update_content(
                pool, ws_artifact["id"],
                content_json={"error": "Failed to parse LLM output"}, status="error",
            )
        return {"error": "Failed to parse LLM output"}

    artifacts = await artifacts_db.list_artifacts(pool, session_id)
    ws_artifact = next(
        (a for a in artifacts if a["artifact_type"] == "worksheet"), None,
    )
    if ws_artifact:
        await artifacts_db.update_content(
            pool, ws_artifact["id"], content_json=content_json, status="ready",
        )
    else:
        logger.warning("worksheet_artifact_not_found", session_id=str(session_id))

    logger.info("worksheet_generated", session_id=str(session_id))
    return content_json


async def generate_review_quiz(
    pool,
    session_id,
    artifact_llm_provider: str = "anthropic",
    artifact_llm_model: str = "claude-sonnet-4-5-20250929",
    artifact_context_turns: int = 20,
) -> dict[str, Any]:
    """Generate an on-demand review quiz from a past session."""
    session = await sessions_db.get_session(pool, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    recent_turns = await sessions_db.get_recent_turns(
        pool, session_id, limit=artifact_context_turns,
    )
    recent_turns.reverse()

    if _count_student_turns(recent_turns) < _MIN_STUDENT_TURNS:
        return _not_enough_data_response(session_id, "review_quiz")

    prompt = f"""Based on this {session['subject']} session (grade {session['grade']}), create a quick review quiz.

Session summary: {session.get('summary_cache', 'No summary available.')}
Key exchanges: {_format_turns(recent_turns)}

Create 8-12 questions. Format as JSON:
{{
  "questions": [{{
    "id": "q1",
    "question": "...",
    "question_latex": null,
    "type": "multiple_choice",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "...",
    "accept_also": [],
    "source_turn": 1,
    "topic": "...",
    "difficulty": "easy",
    "hint": "Think about..."
  }}]
}}

Mix difficulty. Valid JSON only."""

    content_text = await _llm_generate(prompt, artifact_llm_provider, artifact_llm_model, max_tokens=2000)
    try:
        content_json: dict[str, Any] = extract_json(content_text)
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "review_quiz_json_parse_failed",
            session_id=str(session_id),
            raw_text=content_text[:200],
        )
        artifact_id = await artifacts_db.create_artifact(
            pool, session_id, "review_quiz", f"Review Quiz: {session['subject']}",
        )
        await artifacts_db.update_content(
            pool, artifact_id, content_json={"error": "Failed to parse LLM output"}, status="error",
        )
        return {"error": "Failed to parse LLM output"}

    # Create artifact record
    artifact_id = await artifacts_db.create_artifact(
        pool, session_id, "review_quiz", f"Review Quiz: {session['subject']}",
    )
    await artifacts_db.update_content(
        pool, artifact_id, content_json=content_json, status="ready",
    )

    logger.info(
        "review_quiz_generated",
        session_id=str(session_id),
        question_count=len(content_json.get("questions", [])),
    )
    return content_json


async def generate_flash_cards(
    pool,
    session_id,
    user_id,
    artifact_llm_provider: str = "anthropic",
    artifact_llm_model: str = "claude-sonnet-4-5-20250929",
    artifact_context_turns: int = 20,
) -> list[dict[str, Any]]:
    """Generate flash cards from recent session transcript turns.

    Asks Groq to identify key terms/concepts discussed, then upserts
    each card into the database (deduplicating via ON CONFLICT).

    Returns the list of generated flash card dicts.
    """
    session = await sessions_db.get_session(pool, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    recent_turns = await sessions_db.get_recent_turns(
        pool, session_id, limit=artifact_context_turns,
    )
    recent_turns.reverse()

    if _count_student_turns(recent_turns) < _MIN_STUDENT_TURNS:
        return []

    subject = session.get("subject", "general")
    grade = session.get("grade", 8)

    prompt = f"""Based on this {subject} tutoring session (grade {grade}), identify 5-10 key terms or concepts that were discussed.

Conversation:
{_format_turns(recent_turns)}

For each concept, create a flash card. Format as JSON:
{{
  "flash_cards": [
    {{
      "term": "the key term or concept name",
      "definition": "clear, student-friendly definition (1-2 sentences)",
      "example": "a concrete example that illustrates the concept"
    }}
  ]
}}

Rules:
- Only include terms actually discussed in the conversation
- Definitions should be grade-{grade}-appropriate
- Each example should be specific and helpful for studying
- Respond with valid JSON only"""

    content_text = await _llm_generate(prompt, artifact_llm_provider, artifact_llm_model, max_tokens=1500)

    try:
        content_json: dict[str, Any] = extract_json(content_text)
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "flash_cards_json_parse_failed",
            session_id=str(session_id),
            raw_text=content_text[:200],
        )
        return []

    cards_data = content_json.get("flash_cards", [])
    if not isinstance(cards_data, list):
        logger.warning(
            "flash_cards_invalid_format",
            session_id=str(session_id),
        )
        return []

    created_cards: list[dict[str, Any]] = []
    for card in cards_data:
        term = card.get("term", "").strip()
        definition = card.get("definition", "").strip()
        if not term or not definition:
            continue

        example = card.get("example")
        if isinstance(example, str):
            example = example.strip() or None

        inserted = await flash_cards_db.upsert_flash_card(
            pool,
            user_id=user_id,
            subject=subject,
            term=term,
            definition=definition,
            example=example,
            grade=grade if isinstance(grade, int) else 8,
            session_id=session_id,
        )

        created_cards.append({
            "term": term,
            "definition": definition,
            "example": example,
            "subject": subject,
            "is_new": inserted,
        })

    logger.info(
        "flash_cards_generated",
        session_id=str(session_id),
        total=len(created_cards),
        new_count=sum(1 for c in created_cards if c["is_new"]),
    )
    return created_cards
