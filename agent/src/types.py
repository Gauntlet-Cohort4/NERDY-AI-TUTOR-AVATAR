"""Shared types, protocols, and dataclasses for the Nerdy AI Tutor pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, runtime_checkable


class Subject(Enum):
    # Middle School (6th-8th)
    BIOLOGY = "biology"
    MATH = "math"
    EARTH_SCIENCE = "earth_science"
    INTRO_ALGEBRA = "intro_algebra"
    # High School Lower (9th-10th)
    ALGEBRA_II = "algebra_ii"
    CHEMISTRY = "chemistry"
    CELL_BIOLOGY = "cell_biology"
    WORLD_HISTORY = "world_history"
    # High School Upper (11th-12th)
    CALCULUS = "calculus"
    PHYSICS = "physics"
    AP_BIOLOGY = "ap_biology"


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
