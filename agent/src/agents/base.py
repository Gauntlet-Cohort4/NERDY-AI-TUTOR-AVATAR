"""SubjectTutorAgent — base class for subject-specific tutor agents.

Provides STT keyterm update on subject handoff via _update_stt_keyterms().
Each subclass sets _subject to its Subject enum value.
"""

from __future__ import annotations

import structlog
from livekit.agents import Agent

from src.education.subjects import get_keyterms
from src.types import Subject

logger = structlog.get_logger(__name__)


class SubjectTutorAgent(Agent):
    """Base class for subject-specific tutor agents.

    Subclasses must set the _subject class attribute to the appropriate
    Subject enum value. Call _update_stt_keyterms() in on_enter() to
    update Deepgram STT keyterms for the active subject.
    """

    _subject: Subject  # Must be set by subclass

    def _update_stt_keyterms(self) -> None:
        """Update Deepgram STT keyterms for this subject.

        Handles gracefully:
        - session.stt is None
        - session has no stt attribute
        - stt has no update_options method
        """
        stt = getattr(self.session, "stt", None)
        if stt is not None and hasattr(stt, "update_options"):
            keyterms = get_keyterms(self._subject)
            stt.update_options(keyterm=keyterms)
            logger.info(
                "stt_keyterms_updated",
                subject=self._subject.value,
                count=len(keyterms),
            )
