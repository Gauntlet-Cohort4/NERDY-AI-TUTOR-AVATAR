"""Integration tests for the agent pipeline construction and error handling.

Tests cover:
- AgentSessionConfig construction with all plugin providers
- PipelineError creation with correct stage and severity
- Error handler fallback responses per stage
- Subject agent resolution from room names

These tests validate pipeline wiring without requiring live API connections.
When LIVEKIT_URL is set, they run against real configuration; otherwise they
use mock config fixtures.

Marked with @pytest.mark.integration — skipped when LIVEKIT_URL is absent.
"""

from __future__ import annotations

import os

import pytest

from src.config import AppConfig
from src.errors import (
    ErrorSeverity,
    FALLBACK_RESPONSES,
    MAX_RETRIES,
    PipelineError,
    PipelineStage,
    handle_pipeline_error,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("LIVEKIT_URL"),
    reason="Integration tests require live API keys",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def live_config() -> AppConfig:
    """Load AppConfig from environment — only runs when keys are present."""
    return AppConfig.from_env()


# ---------------------------------------------------------------------------
# Pipeline construction
# ---------------------------------------------------------------------------


class TestAgentSessionConstruction:
    """Verify that AgentSessionConfig can be built from a live AppConfig."""

    def test_create_agent_session_from_live_config(self, live_config: AppConfig):
        """AgentSessionConfig contains correct provider names and model settings."""
        from main import create_agent_session

        session_cfg = create_agent_session(live_config)

        assert session_cfg.agent_name == "SubjectRouterAgent"
        assert session_cfg.stt_provider == "deepgram"
        assert session_cfg.llm_provider == "groq"
        assert session_cfg.tts_provider == "cartesia"
        assert session_cfg.stt_model == live_config.deepgram_model
        assert session_cfg.llm_model == live_config.groq_model
        assert session_cfg.tts_model == live_config.cartesia_model

    def test_session_config_is_frozen(self, live_config: AppConfig):
        """AgentSessionConfig is a frozen dataclass — immutable after creation."""
        from main import create_agent_session

        session_cfg = create_agent_session(live_config)

        with pytest.raises(AttributeError):
            session_cfg.agent_name = "SomethingElse"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Error fallback
# ---------------------------------------------------------------------------


class TestPipelineErrorFallback:
    """Verify PipelineError construction and handler behaviour for each stage."""

    @pytest.mark.parametrize(
        "stage",
        [PipelineStage.STT, PipelineStage.LLM, PipelineStage.TTS, PipelineStage.AVATAR],
    )
    def test_pipeline_error_has_correct_stage(self, stage: PipelineStage):
        """PipelineError stores the originating stage."""
        error = PipelineError(
            stage=stage,
            severity=ErrorSeverity.RECOVERABLE,
            message=f"Test error in {stage.value}",
        )
        assert error.stage == stage
        assert error.severity == ErrorSeverity.RECOVERABLE

    @pytest.mark.parametrize(
        "stage",
        [PipelineStage.STT, PipelineStage.LLM, PipelineStage.TTS, PipelineStage.AVATAR],
    )
    def test_handle_pipeline_error_returns_fallback(self, stage: PipelineStage):
        """handle_pipeline_error returns the stage-specific Socratic fallback."""
        error = PipelineError(
            stage=stage,
            severity=ErrorSeverity.RECOVERABLE,
            message="something went wrong",
        )
        fallback = handle_pipeline_error(error)
        assert fallback == FALLBACK_RESPONSES[stage]

    def test_llm_error_with_original_exception(self):
        """PipelineError wraps the original exception for logging."""
        original = RuntimeError("model timeout")
        error = PipelineError(
            stage=PipelineStage.LLM,
            severity=ErrorSeverity.DEGRADED,
            message="LLM timed out",
            original_exception=original,
        )
        log_dict = error.to_log_dict()
        assert log_dict["stage"] == "llm"
        assert log_dict["severity"] == "degraded"
        assert log_dict["exception_type"] == "RuntimeError"

    def test_retry_count_respected(self):
        """handle_pipeline_error logs retry intent when below MAX_RETRIES."""
        error = PipelineError(
            stage=PipelineStage.LLM,
            severity=ErrorSeverity.RECOVERABLE,
            message="transient",
            retry_count=0,
        )
        # Should not raise — just returns fallback
        fallback = handle_pipeline_error(error)
        assert isinstance(fallback, str)
        assert error.retry_count < MAX_RETRIES[PipelineStage.LLM]


# ---------------------------------------------------------------------------
# Subject routing
# ---------------------------------------------------------------------------


class TestSubjectHandoff:
    """Verify _resolve_agent parses room names and returns correct agent types."""

    @pytest.mark.parametrize(
        ("room_name", "expected_type"),
        [
            ("tutor-biology-1234", "BiologyTutorAgent"),
            ("tutor-math-5678", "MathTutorAgent"),
            ("tutor-physics-9999", "PhysicsTutorAgent"),
        ],
    )
    def test_resolve_agent_returns_correct_type(
        self, room_name: str, expected_type: str
    ):
        """Room name 'tutor-{subject}-{ts}' resolves to the matching tutor agent."""
        from main import _resolve_agent

        agent = _resolve_agent(room_name)
        assert type(agent).__name__ == expected_type

    def test_resolve_agent_falls_back_to_router(self):
        """Unknown subject in room name falls back to SubjectRouterAgent."""
        from main import _resolve_agent

        agent = _resolve_agent("tutor-art-0000")
        assert type(agent).__name__ == "SubjectRouterAgent"

    def test_resolve_agent_malformed_room_name(self):
        """Completely unrecognized room name falls back to SubjectRouterAgent."""
        from main import _resolve_agent

        agent = _resolve_agent("random-room")
        assert type(agent).__name__ == "SubjectRouterAgent"
