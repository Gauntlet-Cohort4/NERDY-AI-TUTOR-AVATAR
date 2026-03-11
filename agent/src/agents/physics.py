"""PhysicsTutorAgent — Newton's Third Law Socratic tutor (9th grade)."""

import structlog

from src.agents.base import SubjectTutorAgent
from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject

logger = structlog.get_logger(__name__)


class PhysicsTutorAgent(SubjectTutorAgent):
    """Socratic tutor for 9th-grade Newton's Third Law using Deepgram Nova-3."""

    _subject = Subject.PHYSICS

    def __init__(self) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.PHYSICS]
        super().__init__(instructions=get_system_prompt(Subject.PHYSICS))
        logger.debug(
            "physics_agent_created",
            grade_level=subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student with a physics-specific welcome."""
        logger.info("physics_greeting_triggered")
        self._update_stt_keyterms()
        self.session.generate_reply(
            instructions="Welcome the student to the physics session about Newton's Third Law. "
            "Ask an opening Socratic question about what happens when they push on something."
        )
