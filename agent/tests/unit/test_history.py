"""Tests for ConversationHistory in education/history.py.

Requirement mapping:
- test_add_turn_immutability       → add_turn returns new instance, original unchanged
- test_get_context_window          → returns recent turns within budget
- test_to_chat_context             → converts turns to [{"role": ..., "content": ...}]
- test_to_chat_context_role_map    → "student" → "user", "tutor" → "assistant"
- test_summarize                   → async summarize reduces old turns, returns new instance
- test_empty_history               → edge cases with no turns
"""

import pytest

from src.types import ConversationTurn


def make_turn(role: str, content: str, turn_number: int) -> ConversationTurn:
    return ConversationTurn(role=role, content=content, turn_number=turn_number)


class TestConversationHistoryInit:
    def test_instantiation(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        assert history is not None

    def test_initial_state_is_empty(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        assert history.get_context_window() == []
        assert history.to_chat_context() == []


class TestAddTurnImmutability:
    def test_add_turn_returns_new_instance(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        turn = make_turn("student", "What is photosynthesis?", 1)
        new_history = history.add_turn(turn)

        assert new_history is not history, "add_turn must return a new instance"

    def test_original_history_unchanged_after_add_turn(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        turn = make_turn("student", "What is photosynthesis?", 1)
        _ = history.add_turn(turn)

        # Original must remain empty
        assert history.get_context_window() == []

    def test_new_history_contains_added_turn(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        turn = make_turn("student", "What is photosynthesis?", 1)
        new_history = history.add_turn(turn)

        window = new_history.get_context_window()
        assert len(window) == 1
        assert window[0].content == "What is photosynthesis?"

    def test_chained_add_turns(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        history = history.add_turn(make_turn("student", "Hello", 1))
        history = history.add_turn(make_turn("tutor", "Hi there!", 2))
        history = history.add_turn(make_turn("student", "Help me", 3))

        window = history.get_context_window()
        assert len(window) == 3


class TestGetContextWindow:
    def test_returns_all_turns_within_budget(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        for i in range(5):
            history = history.add_turn(make_turn("student", f"Question {i}", i + 1))

        window = history.get_context_window()
        assert len(window) == 5

    def test_respects_token_budget(self):
        from src.education.history import ConversationHistory

        # Very tight budget — only a few short messages fit
        history = ConversationHistory(max_turns=100, summarization_threshold=50, token_budget=20)
        for i in range(10):
            content = "a" * 50  # ~12 tokens each
            history = history.add_turn(make_turn("student", content, i + 1))

        # Should not return all 10 turns when budget is tight
        window = history.get_context_window()
        assert len(window) < 10

    def test_returns_most_recent_turns(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=100, summarization_threshold=50, token_budget=20)
        for i in range(5):
            content = "a" * 50
            history = history.add_turn(make_turn("student", content, i + 1))

        window = history.get_context_window()
        # Most recent turns should be included
        if window:
            last_turn = window[-1]
            assert last_turn.turn_number == 5


class TestToChatContext:
    def test_empty_history_returns_empty_list(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        assert history.to_chat_context() == []

    def test_student_role_maps_to_user(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        history = history.add_turn(make_turn("student", "Hello", 1))
        ctx = history.to_chat_context()

        assert len(ctx) == 1
        assert ctx[0]["role"] == "user"
        assert ctx[0]["content"] == "Hello"

    def test_tutor_role_maps_to_assistant(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        history = history.add_turn(make_turn("tutor", "Great question!", 1))
        ctx = history.to_chat_context()

        assert len(ctx) == 1
        assert ctx[0]["role"] == "assistant"
        assert ctx[0]["content"] == "Great question!"

    def test_mixed_roles_are_mapped_correctly(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        history = history.add_turn(make_turn("student", "Question", 1))
        history = history.add_turn(make_turn("tutor", "Answer", 2))
        history = history.add_turn(make_turn("student", "Follow up", 3))
        ctx = history.to_chat_context()

        assert ctx[0]["role"] == "user"
        assert ctx[1]["role"] == "assistant"
        assert ctx[2]["role"] == "user"

    def test_chat_context_has_role_and_content_keys(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=8, token_budget=2000)
        history = history.add_turn(make_turn("student", "Test", 1))
        ctx = history.to_chat_context()

        assert "role" in ctx[0]
        assert "content" in ctx[0]


class TestSummarize:
    @pytest.mark.asyncio
    async def test_summarize_returns_new_instance(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=3, token_budget=2000)
        for i in range(5):
            history = history.add_turn(make_turn("student", f"Question {i}", i + 1))

        async def mock_llm(messages: list[dict]) -> str:
            return "Summary of conversation so far."

        new_history = await history.summarize(mock_llm)
        assert new_history is not history

    @pytest.mark.asyncio
    async def test_summarize_reduces_turn_count(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=3, token_budget=2000)
        for i in range(6):
            history = history.add_turn(make_turn("student", f"Question number {i}", i + 1))

        original_count = len(history.get_context_window())

        async def mock_llm(messages: list[dict]) -> str:
            return "Summary of the first few turns."

        new_history = await history.summarize(mock_llm)
        new_count = len(new_history.get_context_window())
        assert new_count < original_count

    @pytest.mark.asyncio
    async def test_summarize_original_unchanged(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=3, token_budget=2000)
        for i in range(5):
            history = history.add_turn(make_turn("student", f"Question {i}", i + 1))
        original_window = history.get_context_window()

        async def mock_llm(messages: list[dict]) -> str:
            return "Summary text."

        await history.summarize(mock_llm)

        # Original history's window must be unchanged
        assert history.get_context_window() == original_window

    @pytest.mark.asyncio
    async def test_summarize_empty_history_returns_same(self):
        from src.education.history import ConversationHistory

        history = ConversationHistory(max_turns=10, summarization_threshold=3, token_budget=2000)

        async def mock_llm(messages: list[dict]) -> str:
            return "No content to summarize."

        new_history = await history.summarize(mock_llm)
        assert new_history.get_context_window() == []
