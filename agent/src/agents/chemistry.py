"""ChemistryTutorAgent — chemistry Socratic tutor (10th grade)."""

import structlog

from src.agents.base import SubjectTutorAgent
from src.education.prompts import get_system_prompt
from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject

logger = structlog.get_logger(__name__)


class ChemistryTutorAgent(SubjectTutorAgent):
    """Socratic tutor for 10th-grade chemistry using Deepgram Nova-3."""

    _subject = Subject.CHEMISTRY

    def __init__(self, grade: int | None = None) -> None:
        subject_config = SUBJECT_CONFIGS[Subject.CHEMISTRY]
        super().__init__(instructions=get_system_prompt(Subject.CHEMISTRY, grade=grade))
        self._grade = grade
        logger.debug(
            "chemistry_agent_created",
            grade_level=grade or subject_config.grade_level,
            keyterm_count=len(subject_config.keyterms),
        )

    async def on_enter(self) -> None:
        """Greet the student with a chemistry-specific welcome."""
        logger.info("chemistry_greeting_triggered")
        self._update_stt_keyterms()
        self.session.generate_reply(
            instructions="Welcome the student to the chemistry session. "
            "Ask an opening Socratic question to get them thinking about what "
            "happens to atoms when substances combine in a chemical reaction."
        )
