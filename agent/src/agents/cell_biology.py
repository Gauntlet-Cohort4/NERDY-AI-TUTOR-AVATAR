"""CellBiologyTutorAgent — cell biology Socratic tutor (9th grade)."""

import structlog

from src.agents.base import SubjectTutorAgent
from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject

logger = structlog.get_logger(__name__)


class CellBiologyTutorAgent(SubjectTutorAgent):
    """Socratic tutor for 9th-grade cell biology using Deepgram Nova-3."""

    _subject = Subject.CELL_BIOLOGY

    def __init__(self, grade: int | None = None) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.CELL_BIOLOGY]
        super().__init__(instructions=get_system_prompt(Subject.CELL_BIOLOGY, grade=grade))
        self._grade = grade
        logger.debug(
            "cell_biology_agent_created",
            grade_level=grade or subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student with a cell biology-specific welcome."""
        logger.info("cell_biology_greeting_triggered")
        self._update_stt_keyterms()
        self.session.generate_reply(
            instructions="Welcome the student to the cell biology session. "
            "Ask an opening Socratic question to get them thinking about what "
            "structures inside a cell keep it alive and functioning."
        )
