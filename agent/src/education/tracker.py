"""ConversationTracker — hooks AgentSession events to trigger background summarization.

Listens to conversation_item_added events, tracks turns, and triggers
async summarization when the turn count reaches the configured threshold.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import structlog

from src.education.history import ConversationHistory
from src.types import ConversationTurn

logger = structlog.get_logger(__name__)


class ConversationTracker:
    """Listens to AgentSession conversation events and triggers summarization.

    This class is wired to session.on("conversation_item_added", tracker.on_conversation_item)
    in the entrypoint. It filters for user/assistant messages, tracks turn count,
    updates the immutable ConversationHistory, and triggers background summarization
    at the configured threshold.
    """

    def __init__(
        self,
        history: ConversationHistory,
        llm_callable: Callable[[list[dict]], Awaitable[str]],
    ) -> None:
        self._history = history
        self._llm_callable = llm_callable
        self._turn_count = 0
        self._summarization_task: asyncio.Task | None = None
        self._pending_tasks: set[asyncio.Task] = set()
        self._db_pool = None  # set externally when DB is available
        self._session_id = None  # set when session starts

    @property
    def history(self) -> ConversationHistory:
        """Return the current (immutable) conversation history."""
        return self._history

    @property
    def summary(self) -> str:
        """Return the current summary text."""
        return self._history._summary

    @property
    def turn_count(self) -> int:
        """Return the number of tracked conversation turns."""
        return self._turn_count

    async def flush(self) -> None:
        """Await all pending fire-and-forget tasks before session teardown.

        Call this in the disconnect handler before generating artifacts so that
        all DB writes are committed and readable by the artifact queries.
        """
        # Snapshot and clear to avoid set-mutation during gather
        pending = set(self._pending_tasks)
        self._pending_tasks.clear()
        pending_count = len(pending)

        if pending:
            results = await asyncio.gather(*pending, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError):
                    logger.warning("pending_task_flush_error", error=str(r))

        if self._summarization_task is not None and not self._summarization_task.done():
            results = await asyncio.gather(self._summarization_task, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError):
                    logger.warning("summarization_flush_error", error=str(r))

        logger.debug("tracker_flushed", flushed_tasks=pending_count)

    def on_conversation_item(self, event) -> None:
        """Handle conversation_item_added events from AgentSession.

        Filters for user/assistant messages only (ignores tool calls, function
        calls, system messages). Increments turn count and triggers
        summarization at threshold.
        """
        item = event.item if hasattr(event, "item") else event
        role = getattr(item, "role", None)
        if role not in ("user", "assistant"):
            return

        # Extract content — prefer text_content, fall back to content
        content = getattr(item, "text_content", "") or ""
        if not content:
            raw = getattr(item, "content", "")
            if isinstance(raw, list):
                content = " ".join(str(c) for c in raw)
            elif isinstance(raw, str):
                content = raw

        role_map = {"user": "student", "assistant": "tutor"}
        mapped_role = role_map.get(role, role)

        self._turn_count += 1
        turn = ConversationTurn(
            role=mapped_role,
            content=content,
            turn_number=self._turn_count,
        )
        self._history = self._history.add_turn(turn)

        # Fire-and-forget DB write — never blocks the pipeline.
        # Check for a running loop *before* creating the coroutine to avoid
        # "coroutine was never awaited" warnings in synchronous tests.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            task = loop.create_task(self._persist_turn(turn))
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)
        else:
            logger.warning("turn_persist_skipped_no_event_loop", turn_number=turn.turn_number)

        logger.debug("conversation_tracked", turn=self._turn_count, role=mapped_role)

        # Trigger summarization at threshold
        threshold = self._history.summarization_threshold
        if (
            self._turn_count >= threshold
            and self._turn_count % threshold == 0
            and (self._summarization_task is None or self._summarization_task.done())
        ):
            logger.info("summarization_triggered", turn_count=self._turn_count)
            if loop is not None:
                self._summarization_task = loop.create_task(
                    self._run_summarization()
                )

    async def _persist_turn(self, turn: ConversationTurn) -> None:
        """Fire-and-forget DB write — never blocks the pipeline."""
        if self._db_pool is None or self._session_id is None:
            return
        try:
            from src.db.sessions import add_turn

            await add_turn(
                self._db_pool,
                self._session_id,
                turn.turn_number,
                turn.role,
                turn.content,
                metrics=turn.metrics.__dict__ if turn.metrics else None,
            )
        except Exception:
            logger.warning(
                "turn_persist_failed", turn=turn.turn_number, exc_info=True,
            )

    async def _run_summarization(self) -> None:
        """Background task: summarize older turns via LLM."""
        try:
            new_history = await self._history.summarize(self._llm_callable)
            self._history = new_history
            logger.info(
                "summarization_complete",
                summary_length=len(new_history._summary),
            )
        except Exception:
            logger.warning("summarization_failed", exc_info=True)
