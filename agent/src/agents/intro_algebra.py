"""IntroAlgebraTutorAgent — introductory algebra Socratic tutor (8th grade)."""

import structlog

from src.agents.base import SubjectTutorAgent
from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject

logger = structlog.get_logger(__name__)


class IntroAlgebraTutorAgent(SubjectTutorAgent):
    """Socratic tutor for 8th-grade introductory algebra using Deepgram Nova-3."""

    _subject = Subject.INTRO_ALGEBRA

    def __init__(self, grade: int | None = None) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.INTRO_ALGEBRA]
        super().__init__(instructions=get_system_prompt(Subject.INTRO_ALGEBRA, grade=grade))
        self._grade = grade
        logger.debug(
            "intro_algebra_agent_created",
            grade_level=grade or subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student and ask what they need help with."""
        logger.info("intro_algebra_greeting_triggered")
        self._update_stt_keyterms()
        self.session.generate_reply(
            instructions="Greet the student warmly (1 sentence). Then ask what specific "
            "topic within Intro Algebra they'd like help with today. Keep it to 2 sentences total."
        )
