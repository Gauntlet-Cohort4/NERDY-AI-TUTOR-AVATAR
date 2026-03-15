"""WorldHistoryTutorAgent — world history Socratic tutor (10th grade)."""

import structlog

from src.agents.base import SubjectTutorAgent
from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject
from src.visuals.templates import get_templates_for_subject

logger = structlog.get_logger(__name__)


class WorldHistoryTutorAgent(SubjectTutorAgent):
    """Socratic tutor for 10th-grade world history using Deepgram Nova-3."""

    _subject = Subject.WORLD_HISTORY

    def __init__(self, grade: int | None = None) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.WORLD_HISTORY]
        templates = list(get_templates_for_subject("world_history"))
        super().__init__(instructions=get_system_prompt(
            Subject.WORLD_HISTORY, grade=grade, available_templates=templates,
        ))
        self._grade = grade
        logger.debug(
            "world_history_agent_created",
            grade_level=grade or subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student and ask what they need help with."""
        logger.info("world_history_greeting_triggered")
        self._update_stt_keyterms()
        self.session.generate_reply(
            instructions="Greet the student warmly (1 sentence). Then ask what specific "
            "topic within World History they'd like help with today. Keep it to 2 sentences total."
        )
