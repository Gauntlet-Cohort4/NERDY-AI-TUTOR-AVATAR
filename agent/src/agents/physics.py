"""PhysicsTutorAgent — Newton's Third Law Socratic tutor (9th grade)."""

import structlog
from livekit.agents import Agent

from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject

logger = structlog.get_logger(__name__)


class PhysicsTutorAgent(Agent):
    """Socratic tutor for 9th-grade Newton's Third Law using Deepgram Nova-3."""

    def __init__(self) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.PHYSICS]
        super().__init__(instructions=get_system_prompt(Subject.PHYSICS))
        logger.debug(
            "physics_agent_created",
            grade_level=subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )
