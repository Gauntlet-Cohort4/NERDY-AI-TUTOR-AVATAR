"""BiologyTutorAgent — photosynthesis Socratic tutor (7th grade)."""

import structlog

from src.agents.base import SubjectTutorAgent
from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject

logger = structlog.get_logger(__name__)


class BiologyTutorAgent(SubjectTutorAgent):
    """Socratic tutor for 7th-grade photosynthesis using Deepgram Nova-3."""

    _subject = Subject.BIOLOGY

    def __init__(self, grade: int | None = None) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.BIOLOGY]
        super().__init__(instructions=get_system_prompt(Subject.BIOLOGY, grade=grade))
        self._grade = grade
        logger.debug(
            "biology_agent_created",
            grade_level=grade or subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student with a biology-specific welcome."""
        logger.info("biology_greeting_triggered")
        self._update_stt_keyterms()
        self.session.generate_reply(
            instructions="Welcome the student to the biology session about photosynthesis. "
            "Ask an opening Socratic question to get them thinking about how plants make food."
        )
