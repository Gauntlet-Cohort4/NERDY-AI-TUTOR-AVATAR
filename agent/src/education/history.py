"""Conversation history manager with rolling window and async summarization.

ConversationHistory is fully immutable: every mutating operation returns a
new instance, leaving the original unchanged.

Token estimation: ~4 characters per token (rough English average).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

import structlog

from src.types import ConversationTurn

logger = structlog.get_logger(__name__)

_CHARS_PER_TOKEN = 4
_ROLE_MAP: dict[str, str] = {
    "student": "user",
    "tutor": "assistant",
}


@dataclass(frozen=True)
class ConversationHistory:
    """Immutable rolling conversation history with token-budget context window."""

    max_turns: int
    summarization_threshold: int
    token_budget: int
    _turns: tuple[ConversationTurn, ...] = field(default_factory=tuple)
    _summary: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_turn(self, turn: ConversationTurn) -> "ConversationHistory":
        """Return a new ConversationHistory with *turn* appended.

        The original instance is never modified (immutability contract).
        """
        new_turns = self._turns + (turn,)
        return ConversationHistory(
            max_turns=self.max_turns,
            summarization_threshold=self.summarization_threshold,
            token_budget=self.token_budget,
            _turns=new_turns,
            _summary=self._summary,
        )

    def get_context_window(self) -> list[ConversationTurn]:
        """Return the most-recent turns that fit within the token budget.

        Iterates from newest to oldest, accumulating turns until the
        estimated token count would exceed *token_budget*.  Returns the
        turns in chronological order.
        """
        if not self._turns:
            return []

        selected: list[ConversationTurn] = []
        tokens_used = _estimate_tokens(self._summary)

        for turn in reversed(self._turns):
            turn_tokens = _estimate_tokens(turn.content)
            if tokens_used + turn_tokens > self.token_budget:
                break
            selected.append(turn)
            tokens_used += turn_tokens

        return list(reversed(selected))

    async def summarize(
        self,
        llm_callable: Callable[[list[dict]], Awaitable[str]],
    ) -> "ConversationHistory":
        """Summarize older turns and return a new ConversationHistory.

        When there are no turns the original (empty) instance is returned
        unchanged.  Otherwise the oldest turns (beyond the keep window) are
        summarised via *llm_callable*, and a new instance is built that
        holds only the recent keep-window turns plus the summary text.

        The original instance is never modified.
        """
        if not self._turns:
            return self

        keep_count = max(1, self.summarization_threshold // 2)
        turns_to_summarize = self._turns[:-keep_count] if len(self._turns) > keep_count else ()
        turns_to_keep = self._turns[-keep_count:] if len(self._turns) > keep_count else self._turns

        if not turns_to_summarize:
            return self

        messages = _turns_to_chat_dicts(turns_to_summarize)
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "Summarize this tutoring conversation in 2-3 sentences, "
                    "capturing what the student has learned and the key questions asked."
                ),
            },
        )

        logger.info(
            "summarizing_turns",
            turns_to_summarize=len(turns_to_summarize),
            turns_to_keep=len(turns_to_keep),
        )

        summary_text = await llm_callable(messages)

        return ConversationHistory(
            max_turns=self.max_turns,
            summarization_threshold=self.summarization_threshold,
            token_budget=self.token_budget,
            _turns=turns_to_keep,
            _summary=summary_text,
        )

    def to_chat_context(self) -> list[dict]:
        """Convert the context window to the LLM chat format.

        Returns a list of dicts with "role" and "content" keys.
        Roles are mapped: "student" → "user", "tutor" → "assistant".
        If a summary exists it is prepended as a system message.
        """
        context: list[dict] = []

        if self._summary:
            context.append({"role": "system", "content": self._summary})

        context.extend(_turns_to_chat_dicts(self.get_context_window()))
        return context


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    """Rough token count: len(text) / 4."""
    return max(1, len(text) // _CHARS_PER_TOKEN) if text else 0


def _turns_to_chat_dicts(
    turns: tuple[ConversationTurn, ...] | list[ConversationTurn],
) -> list[dict]:
    result = []
    for turn in turns:
        role = _ROLE_MAP.get(turn.role, turn.role)
        result.append({"role": role, "content": turn.content})
    return result
