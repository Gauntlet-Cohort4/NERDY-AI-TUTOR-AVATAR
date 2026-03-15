"""CalculusTutorAgent — calculus Socratic tutor (12th grade)."""

import structlog

from src.agents.base import SubjectTutorAgent
from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject
from src.visuals.templates import get_templates_for_subject

logger = structlog.get_logger(__name__)


class CalculusTutorAgent(SubjectTutorAgent):
    """Socratic tutor for 12th-grade calculus using Deepgram Nova-3."""

    _subject = Subject.CALCULUS

    def __init__(self, grade: int | None = None) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.CALCULUS]
        templates = list(get_templates_for_subject("calculus"))
        super().__init__(instructions=get_system_prompt(
            Subject.CALCULUS, grade=grade, available_templates=templates,
        ))
        self._grade = grade
        logger.debug(
            "calculus_agent_created",
            grade_level=grade or subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student and ask what they need help with."""
        logger.info("calculus_greeting_triggered")
        self._update_stt_keyterms()
        self.session.generate_reply(
            instructions="Greet the student warmly (1 sentence). Then ask what specific "
            "topic within Calculus they'd like help with today. Keep it to 2 sentences total."
        )
