"""Custom exceptions and error handler for the pipeline.

Every error is categorized by stage and severity. Errors recover gracefully
with Socratic fallback responses that feel like natural tutoring moments.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class PipelineStage(Enum):
    STT = "stt"
    LLM = "llm"
    TTS = "tts"
    AVATAR = "avatar"
    SESSION = "session"


class ErrorSeverity(Enum):
    RECOVERABLE = "recoverable"
    DEGRADED = "degraded"
    FATAL = "fatal"


@dataclass
class PipelineError:
    stage: PipelineStage
    severity: ErrorSeverity
    message: str
    original_exception: Optional[Exception] = None
    retry_count: int = 0

    def to_log_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "severity": self.severity.value,
            "message": self.message,
            "retry_count": self.retry_count,
            "exception_type": (
                type(self.original_exception).__name__
                if self.original_exception
                else None
            ),
        }


# Socratic fallback responses — error recovery that feels like tutoring
FALLBACK_RESPONSES: dict[PipelineStage, str] = {
    PipelineStage.STT: "Could you say that again? I want to make sure I understand your thinking.",
    PipelineStage.LLM: "Give me just a moment to think about that...",
    PipelineStage.TTS: "",  # Brief silence, retry next turn
    PipelineStage.AVATAR: "",  # Audio continues without video
}

MAX_RETRIES: dict[PipelineStage, int] = {
    PipelineStage.STT: 1,
    PipelineStage.LLM: 2,
    PipelineStage.TTS: 1,
    PipelineStage.AVATAR: 3,
}


def handle_pipeline_error(error: PipelineError) -> str:
    """Central error handler. Logs the error and returns the fallback response."""
    logger.error("pipeline_error", **error.to_log_dict())
    if error.retry_count < MAX_RETRIES.get(error.stage, 1):
        logger.info(
            "will_retry", stage=error.stage.value, attempt=error.retry_count + 1
        )
    return FALLBACK_RESPONSES.get(
        error.stage, "Let me think about that for a moment..."
    )
