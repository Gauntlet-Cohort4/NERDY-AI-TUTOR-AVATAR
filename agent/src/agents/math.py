"""MathTutorAgent — fractions Socratic tutor (6th grade)."""

import structlog
from livekit.agents import Agent

from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject

logger = structlog.get_logger(__name__)


class MathTutorAgent(Agent):
    """Socratic tutor for 6th-grade fractions using Deepgram Nova-3."""

    def __init__(self) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.MATH]
        super().__init__(instructions=get_system_prompt(Subject.MATH))
        logger.debug(
            "math_agent_created",
            grade_level=subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )
