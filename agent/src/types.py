"""Shared types, protocols, and dataclasses for the Nerdy AI Tutor pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, runtime_checkable


class Subject(Enum):
    BIOLOGY = "biology"
    MATH = "math"
    PHYSICS = "physics"


@dataclass(frozen=True)
class SubjectConfig:
    subject: Subject
    grade_level: str
    keyterms: tuple[str, ...]
    system_prompt: str


@dataclass(frozen=True)
class TurnMetrics:
    turn_number: int
    stt_ms: float = 0.0
    llm_ttft_ms: float = 0.0
    llm_total_ms: float = 0.0
    tts_ttfb_ms: float = 0.0
    avatar_render_ms: float = 0.0
    total_e2e_ms: float = 0.0
    full_response_ms: float = 0.0
    tokens_generated: int = 0
    response_text: str = ""


@dataclass(frozen=True)
class ConversationTurn:
    role: str  # "student" or "tutor"
    content: str
    turn_number: int
    metrics: Optional[TurnMetrics] = None


@dataclass
class SessionState:
    session_id: str
    subject: SubjectConfig
    turns: list[ConversationTurn] = field(default_factory=list)
    is_active: bool = True
    summary: str = ""


@runtime_checkable
class AvatarRenderer(Protocol):
    async def start(self, session, room) -> None:
        """Attach avatar to an AgentSession and LiveKit room."""
        ...

    async def close(self) -> None:
        """Clean up avatar connection."""
        ...
