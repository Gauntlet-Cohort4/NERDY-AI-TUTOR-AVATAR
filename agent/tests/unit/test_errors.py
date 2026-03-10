"""Tests for error handling infrastructure.

Requirement mapping:
- test_fallback_response_* → Plan §4.2 error recovery
- test_pipeline_error_to_log_dict → Structured error logging
- test_max_retries_per_stage → Retry budget per stage
"""

import pytest
from src.errors import (
    ErrorSeverity,
    FALLBACK_RESPONSES,
    MAX_RETRIES,
    PipelineError,
    PipelineStage,
    handle_pipeline_error,
)


class TestFallbackResponses:
    def test_fallback_response_stt(self):
        error = PipelineError(
            stage=PipelineStage.STT,
            severity=ErrorSeverity.RECOVERABLE,
            message="timeout",
        )
        result = handle_pipeline_error(error)
        assert result == "Could you say that again? I want to make sure I understand your thinking."

    def test_fallback_response_llm(self):
        error = PipelineError(
            stage=PipelineStage.LLM,
            severity=ErrorSeverity.RECOVERABLE,
            message="timeout",
        )
        result = handle_pipeline_error(error)
        assert result == "Give me just a moment to think about that..."

    def test_fallback_response_tts(self):
        error = PipelineError(
            stage=PipelineStage.TTS,
            severity=ErrorSeverity.RECOVERABLE,
            message="audio error",
        )
        result = handle_pipeline_error(error)
        assert result == ""

    def test_fallback_response_avatar(self):
        error = PipelineError(
            stage=PipelineStage.AVATAR,
            severity=ErrorSeverity.RECOVERABLE,
            message="render error",
        )
        result = handle_pipeline_error(error)
        assert result == ""

    def test_fallback_response_session_default(self):
        error = PipelineError(
            stage=PipelineStage.SESSION,
            severity=ErrorSeverity.FATAL,
            message="session error",
        )
        result = handle_pipeline_error(error)
        assert result == "Let me think about that for a moment..."


class TestPipelineErrorLogDict:
    def test_pipeline_error_to_log_dict(self):
        error = PipelineError(
            stage=PipelineStage.LLM,
            severity=ErrorSeverity.DEGRADED,
            message="slow response",
            original_exception=ValueError("bad value"),
            retry_count=1,
        )
        log_dict = error.to_log_dict()
        assert log_dict["stage"] == "llm"
        assert log_dict["severity"] == "degraded"
        assert log_dict["message"] == "slow response"
        assert log_dict["retry_count"] == 1
        assert log_dict["exception_type"] == "ValueError"

    def test_pipeline_error_to_log_dict_no_exception(self):
        error = PipelineError(
            stage=PipelineStage.STT,
            severity=ErrorSeverity.RECOVERABLE,
            message="timeout",
        )
        log_dict = error.to_log_dict()
        assert log_dict["exception_type"] is None


class TestMaxRetries:
    def test_max_retries_per_stage(self):
        assert MAX_RETRIES[PipelineStage.STT] == 1
        assert MAX_RETRIES[PipelineStage.LLM] == 2
        assert MAX_RETRIES[PipelineStage.TTS] == 1
        assert MAX_RETRIES[PipelineStage.AVATAR] == 3
