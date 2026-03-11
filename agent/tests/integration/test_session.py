"""Integration tests for multi-turn session management.

Tests cover:
- 5-turn conversation flow using ConversationHistory
- Subject switch mid-session (router delegates to subject tutor)
- Conversation context window respects token budget
- Summarization produces a new immutable history instance

Marked with @pytest.mark.integration — skipped when LIVEKIT_URL is absent.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

from src.education.history import ConversationHistory
from src.education.subjects import SUBJECT_CONFIGS
from src.types import ConversationTurn, Subject

pytestmark = pytest.mark.skipif(
    not os.environ.get("LIVEKIT_URL"),
    reason="Integration tests require live API keys",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_history() -> ConversationHistory:
    """Fresh conversation history with reasonable defaults."""
    return ConversationHistory(
        max_turns=10,
        summarization_threshold=6,
        token_budget=2000,
    )


@pytest.fixture
def five_turn_history(empty_history: ConversationHistory) -> ConversationHistory:
    """ConversationHistory pre-loaded with 5 student-tutor exchanges."""
    history = empty_history
    exchanges = [
        ("student", "What is photosynthesis?"),
        ("tutor", "Great question! What do you think plants need to grow?"),
        ("student", "Sunlight and water?"),
        ("tutor", "Exactly! Can you think of what else they use from the air?"),
        ("student", "Carbon dioxide?"),
    ]
    for i, (role, content) in enumerate(exchanges, start=1):
        turn = ConversationTurn(role=role, content=content, turn_number=i)
        history = history.add_turn(turn)
    return history


# ---------------------------------------------------------------------------
# Multi-turn conversation flow
# ---------------------------------------------------------------------------


class TestFiveTurnConversation:
    """Verify a 5-turn conversation is tracked correctly."""

    def test_five_turns_recorded(self, five_turn_history: ConversationHistory):
        """All 5 turns are present in the history."""
        window = five_turn_history.get_context_window()
        assert len(window) == 5

    def test_turns_are_chronological(self, five_turn_history: ConversationHistory):
        """Context window returns turns in chronological order."""
        window = five_turn_history.get_context_window()
        turn_numbers = [t.turn_number for t in window]
        assert turn_numbers == [1, 2, 3, 4, 5]

    def test_roles_alternate(self, five_turn_history: ConversationHistory):
        """Roles alternate between student and tutor."""
        window = five_turn_history.get_context_window()
        roles = [t.role for t in window]
        assert roles == ["student", "tutor", "student", "tutor", "student"]

    def test_to_chat_context_maps_roles(self, five_turn_history: ConversationHistory):
        """to_chat_context maps student->user, tutor->assistant."""
        context = five_turn_history.to_chat_context()
        mapped_roles = [msg["role"] for msg in context]
        assert mapped_roles == ["user", "assistant", "user", "assistant", "user"]

    def test_immutability_after_add_turn(self, empty_history: ConversationHistory):
        """Adding a turn returns a new instance; the original is unchanged."""
        turn = ConversationTurn(role="student", content="Hello", turn_number=1)
        new_history = empty_history.add_turn(turn)

        assert len(empty_history.get_context_window()) == 0
        assert len(new_history.get_context_window()) == 1
        assert empty_history is not new_history


# ---------------------------------------------------------------------------
# Subject switch mid-session
# ---------------------------------------------------------------------------


class TestSubjectSwitchMidSession:
    """Verify subject configuration changes work correctly during a session."""

    def test_all_subjects_have_configs(self):
        """Every Subject enum member has an entry in SUBJECT_CONFIGS."""
        for subject in Subject:
            assert subject in SUBJECT_CONFIGS
            cfg = SUBJECT_CONFIGS[subject]
            assert cfg.subject == subject
            assert len(cfg.keyterms) > 0
            assert len(cfg.system_prompt) > 0

    def test_subject_configs_are_frozen(self):
        """SubjectConfig is frozen — cannot be mutated."""
        cfg = SUBJECT_CONFIGS[Subject.BIOLOGY]
        with pytest.raises(AttributeError):
            cfg.grade_level = "12th grade"  # type: ignore[misc]

    def test_switch_subject_preserves_history_immutability(
        self, five_turn_history: ConversationHistory
    ):
        """Switching subject mid-session: old history untouched, new one starts fresh."""
        # Simulate switch: create new history for the new subject
        new_subject_history = ConversationHistory(
            max_turns=five_turn_history.max_turns,
            summarization_threshold=five_turn_history.summarization_threshold,
            token_budget=five_turn_history.token_budget,
        )
        new_turn = ConversationTurn(
            role="student", content="I want to study math now", turn_number=1
        )
        new_subject_history = new_subject_history.add_turn(new_turn)

        # Old history is unmodified
        assert len(five_turn_history.get_context_window()) == 5
        # New history has 1 turn
        assert len(new_subject_history.get_context_window()) == 1

    @pytest.mark.parametrize("subject", list(Subject))
    def test_router_recognizes_all_subjects(self, subject: Subject):
        """SubjectRouterAgent.select_subject handles all known subjects."""
        from main import _resolve_agent

        room_name = f"tutor-{subject.value}-12345"
        agent = _resolve_agent(room_name)
        # Should NOT be the router — should be a subject-specific agent
        assert type(agent).__name__ != "SubjectRouterAgent"


# ---------------------------------------------------------------------------
# Context window and summarization
# ---------------------------------------------------------------------------


class TestContextWindowAndSummarization:
    """Verify token-budget context window and summarization."""

    def test_context_window_respects_token_budget(self):
        """When turns exceed token budget, oldest turns are dropped."""
        history = ConversationHistory(
            max_turns=20,
            summarization_threshold=10,
            token_budget=50,  # Very small budget (~200 chars)
        )
        for i in range(1, 11):
            turn = ConversationTurn(
                role="student" if i % 2 else "tutor",
                content=f"Turn {i}: " + "x" * 100,  # ~100 chars each
                turn_number=i,
            )
            history = history.add_turn(turn)

        window = history.get_context_window()
        # With ~100 chars per turn and budget of 50 tokens (~200 chars),
        # only the most recent turns should fit
        assert len(window) < 10
        # Most recent turn should always be included
        assert window[-1].turn_number == 10

    @pytest.mark.asyncio
    async def test_summarize_returns_new_instance(
        self, five_turn_history: ConversationHistory
    ):
        """Summarization returns a new ConversationHistory with summary text."""
        mock_llm = AsyncMock(return_value="Student learned about photosynthesis basics.")

        # Need enough turns to trigger summarization (> keep_count)
        history = five_turn_history
        for i in range(6, 12):
            turn = ConversationTurn(
                role="student" if i % 2 else "tutor",
                content=f"Follow-up question {i}",
                turn_number=i,
            )
            history = history.add_turn(turn)

        summarized = await history.summarize(mock_llm)

        assert summarized is not history
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_empty_history_returns_self(
        self, empty_history: ConversationHistory
    ):
        """Summarizing an empty history returns the same instance."""
        mock_llm = AsyncMock()
        result = await empty_history.summarize(mock_llm)

        assert result is empty_history
        mock_llm.assert_not_called()
