"""BiologyTutorAgent — photosynthesis Socratic tutor (7th grade)."""

import structlog
from livekit.agents import Agent

from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject

logger = structlog.get_logger(__name__)


class BiologyTutorAgent(Agent):
    """Socratic tutor for 7th-grade photosynthesis using Deepgram Nova-3."""

    def __init__(self) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.BIOLOGY]
        super().__init__(instructions=get_system_prompt(Subject.BIOLOGY))
        logger.debug(
            "biology_agent_created",
            grade_level=subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student with a biology-specific welcome."""
        logger.info("biology_greeting_triggered")
        self.session.generate_reply(
            instructions="Welcome the student to the biology session about photosynthesis. "
            "Ask an opening Socratic question to get them thinking about how plants make food."
        )
