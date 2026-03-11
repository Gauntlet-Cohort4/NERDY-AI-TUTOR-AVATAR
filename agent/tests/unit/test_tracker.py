"""Tests for ConversationTracker in education/tracker.py.

Requirement mapping:
- test_user_role_increments_turn_count      → on_conversation_item with user role
- test_assistant_role_increments_turn_count → on_conversation_item with assistant role
- test_tool_call_ignored                     → tool_call/function roles are ignored
- test_history_updated_immutably            → new history instance each time
- test_summarization_triggered_at_threshold → summarization fires at threshold
- test_summarization_not_triggered_below    → no summarization below threshold
- test_summarization_not_retriggered_inflight → skip if one already running
- test_failed_summarization_no_crash        → exception caught gracefully
- test_history_property                      → history property returns current history
- test_summary_property                      → summary property returns current summary
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.education.history import ConversationHistory


def _make_event(role: str, content: str = "test content"):
    """Build a SimpleNamespace mimicking a conversation_item_added event."""
    return SimpleNamespace(
        item=SimpleNamespace(
            role=role,
            text_content=content,
            content=content,
        ),
    )


def _make_tracker(threshold: int = 6):
    """Build a ConversationTracker with a mock LLM callable."""
    from src.education.tracker import ConversationTracker

    history = ConversationHistory(
        max_turns=20,
        summarization_threshold=threshold,
        token_budget=2000,
    )
    mock_llm = AsyncMock(return_value="Summary of conversation.")
    return ConversationTracker(history=history, llm_callable=mock_llm), mock_llm


class TestTurnCounting:
    def test_user_role_increments_turn_count(self):
        tracker, _ = _make_tracker()
        assert tracker.turn_count == 0

        tracker.on_conversation_item(_make_event("user", "Hello"))
        assert tracker.turn_count == 1

    def test_assistant_role_increments_turn_count(self):
        tracker, _ = _make_tracker()
        tracker.on_conversation_item(_make_event("assistant", "Hi there!"))
        assert tracker.turn_count == 1

    def test_multiple_turns_increment(self):
        tracker, _ = _make_tracker()
        tracker.on_conversation_item(_make_event("user", "Q1"))
        tracker.on_conversation_item(_make_event("assistant", "A1"))
        tracker.on_conversation_item(_make_event("user", "Q2"))
        assert tracker.turn_count == 3

    def test_tool_call_role_ignored(self):
        tracker, _ = _make_tracker()
        tracker.on_conversation_item(_make_event("tool"))
        assert tracker.turn_count == 0

    def test_function_call_role_ignored(self):
        tracker, _ = _make_tracker()
        tracker.on_conversation_item(_make_event("function"))
        assert tracker.turn_count == 0

    def test_system_role_ignored(self):
        tracker, _ = _make_tracker()
        tracker.on_conversation_item(_make_event("system"))
        assert tracker.turn_count == 0

    def test_none_role_ignored(self):
        tracker, _ = _make_tracker()
        event = SimpleNamespace(item=SimpleNamespace(role=None, text_content="x", content="x"))
        tracker.on_conversation_item(event)
        assert tracker.turn_count == 0


class TestHistoryImmutability:
    def test_history_updated_immutably(self):
        tracker, _ = _make_tracker()
        original_history = tracker.history

        tracker.on_conversation_item(_make_event("user", "Hello"))
        new_history = tracker.history

        assert new_history is not original_history
        assert len(original_history.get_context_window()) == 0
        assert len(new_history.get_context_window()) == 1

    def test_each_turn_produces_new_history(self):
        tracker, _ = _make_tracker()
        histories = [tracker.history]

        for i in range(3):
            tracker.on_conversation_item(_make_event("user", f"Turn {i}"))
            histories.append(tracker.history)

        # Each should be a distinct instance
        for i in range(len(histories) - 1):
            assert histories[i] is not histories[i + 1]


class TestSummarizationTrigger:
    def test_summarization_triggered_at_threshold(self):
        threshold = 4
        tracker, _ = _make_tracker(threshold=threshold)

        with patch("asyncio.create_task") as mock_create_task:
            mock_create_task.return_value = MagicMock(done=MagicMock(return_value=True))
            for i in range(threshold):
                tracker.on_conversation_item(_make_event("user", f"Turn {i}"))

            mock_create_task.assert_called_once()

    def test_summarization_not_triggered_below_threshold(self):
        threshold = 6
        tracker, _ = _make_tracker(threshold=threshold)

        with patch("asyncio.create_task") as mock_create_task:
            for i in range(threshold - 1):
                tracker.on_conversation_item(_make_event("user", f"Turn {i}"))

            mock_create_task.assert_not_called()

    def test_summarization_not_retriggered_while_inflight(self):
        threshold = 4
        tracker, _ = _make_tracker(threshold=threshold)

        with patch("asyncio.create_task") as mock_create_task:
            # First task still in flight
            mock_task = MagicMock(done=MagicMock(return_value=False))
            mock_create_task.return_value = mock_task

            # Reach first threshold
            for i in range(threshold):
                tracker.on_conversation_item(_make_event("user", f"Turn {i}"))

            # Reach second threshold — task still in flight
            for i in range(threshold):
                tracker.on_conversation_item(_make_event("user", f"Turn {threshold + i}"))

            # Should only have been called once (first threshold)
            assert mock_create_task.call_count == 1

    def test_summarization_retriggered_after_previous_done(self):
        threshold = 4
        tracker, _ = _make_tracker(threshold=threshold)

        with patch("asyncio.create_task") as mock_create_task:
            # First task completes
            mock_task = MagicMock(done=MagicMock(return_value=True))
            mock_create_task.return_value = mock_task

            # Reach first threshold
            for i in range(threshold):
                tracker.on_conversation_item(_make_event("user", f"Turn {i}"))

            # Reach second threshold — previous task done
            for i in range(threshold):
                tracker.on_conversation_item(_make_event("user", f"Turn {threshold + i}"))

            # Should have been called twice
            assert mock_create_task.call_count == 2


class TestSummarizationExecution:
    @pytest.mark.asyncio
    async def test_run_summarization_updates_history(self):
        tracker, mock_llm = _make_tracker(threshold=3)

        # Add enough turns to summarize
        for i in range(5):
            tracker.on_conversation_item(_make_event("user", f"Turn {i}" * 20))

        await tracker._run_summarization()

        # LLM should have been called
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_summarization_no_crash(self):
        from src.education.tracker import ConversationTracker

        history = ConversationHistory(
            max_turns=20,
            summarization_threshold=3,
            token_budget=2000,
        )
        failing_llm = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        tracker = ConversationTracker(history=history, llm_callable=failing_llm)

        # Add turns
        for i in range(5):
            tracker.on_conversation_item(_make_event("user", f"Turn {i}" * 20))

        # Should not raise
        await tracker._run_summarization()


class TestProperties:
    def test_history_property(self):
        tracker, _ = _make_tracker()
        assert isinstance(tracker.history, ConversationHistory)

    def test_summary_property_initially_empty(self):
        tracker, _ = _make_tracker()
        assert tracker.summary == ""

    def test_turn_count_property(self):
        tracker, _ = _make_tracker()
        assert tracker.turn_count == 0
        tracker.on_conversation_item(_make_event("user", "Hello"))
        assert tracker.turn_count == 1


class TestContentExtraction:
    def test_extracts_text_content(self):
        tracker, _ = _make_tracker()
        event = _make_event("user", "Hello world")
        tracker.on_conversation_item(event)

        window = tracker.history.get_context_window()
        assert window[0].content == "Hello world"

    def test_falls_back_to_content_string(self):
        tracker, _ = _make_tracker()
        event = SimpleNamespace(
            item=SimpleNamespace(
                role="user",
                text_content="",
                content="fallback content",
            ),
        )
        tracker.on_conversation_item(event)

        window = tracker.history.get_context_window()
        assert window[0].content == "fallback content"

    def test_falls_back_to_content_list(self):
        tracker, _ = _make_tracker()
        event = SimpleNamespace(
            item=SimpleNamespace(
                role="user",
                text_content="",
                content=["part1", "part2"],
            ),
        )
        tracker.on_conversation_item(event)

        window = tracker.history.get_context_window()
        assert "part1" in window[0].content
        assert "part2" in window[0].content

    def test_role_mapping_user_to_student(self):
        tracker, _ = _make_tracker()
        tracker.on_conversation_item(_make_event("user", "Hi"))

        window = tracker.history.get_context_window()
        assert window[0].role == "student"

    def test_role_mapping_assistant_to_tutor(self):
        tracker, _ = _make_tracker()
        tracker.on_conversation_item(_make_event("assistant", "Welcome!"))

        window = tracker.history.get_context_window()
        assert window[0].role == "tutor"

    def test_event_without_item_attribute(self):
        """When event has no .item, use the event itself."""
        tracker, _ = _make_tracker()
        # Event IS the item (no .item wrapper)
        event = SimpleNamespace(
            role="user",
            text_content="direct content",
            content="direct content",
        )
        tracker.on_conversation_item(event)

        assert tracker.turn_count == 1
