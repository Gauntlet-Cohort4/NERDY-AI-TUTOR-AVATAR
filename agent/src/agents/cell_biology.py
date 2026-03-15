"""CellBiologyTutorAgent — cell biology Socratic tutor (9th grade)."""

import structlog

from src.agents.base import SubjectTutorAgent
from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject
from src.visuals.templates import get_templates_for_subject

logger = structlog.get_logger(__name__)


class CellBiologyTutorAgent(SubjectTutorAgent):
    """Socratic tutor for 9th-grade cell biology using Deepgram Nova-3."""

    _subject = Subject.CELL_BIOLOGY

    def __init__(self, grade: int | None = None) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.CELL_BIOLOGY]
        templates = list(get_templates_for_subject("cell_biology"))
        super().__init__(instructions=get_system_prompt(
            Subject.CELL_BIOLOGY, grade=grade, available_templates=templates,
        ))
        self._grade = grade
        logger.debug(
            "cell_biology_agent_created",
            grade_level=grade or subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student and ask what they need help with."""
        logger.info("cell_biology_greeting_triggered")
        self._update_stt_keyterms()
        self.session.generate_reply(
            instructions="Greet the student warmly (1 sentence). Then ask what specific "
            "topic within Cell Biology they'd like help with today. Keep it to 2 sentences total."
        )
