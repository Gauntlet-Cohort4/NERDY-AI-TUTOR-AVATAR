"""Tests for STT keyterm update on subject handoff.

Requirement mapping:
- test_get_keyterms_biology       → get_keyterms(Subject.BIOLOGY) returns biology keyterms
- test_get_keyterms_math          → get_keyterms(Subject.MATH) returns math keyterms
- test_get_keyterms_physics       → get_keyterms(Subject.PHYSICS) returns physics keyterms
- test_update_stt_keyterms_calls  → _update_stt_keyterms() calls stt.update_options
- test_stt_none_graceful          → handles stt=None gracefully
- test_stt_no_update_options      → handles stt without update_options gracefully
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.education.subjects import SUBJECT_CONFIGS
from src.types import Subject


class TestGetKeyterms:
    def test_get_keyterms_biology(self):
        from src.education.subjects import get_keyterms

        keyterms = get_keyterms(Subject.BIOLOGY)
        expected = list(SUBJECT_CONFIGS[Subject.BIOLOGY].keyterms)
        assert keyterms == expected
        assert "photosynthesis" in keyterms

    def test_get_keyterms_math(self):
        from src.education.subjects import get_keyterms

        keyterms = get_keyterms(Subject.MATH)
        expected = list(SUBJECT_CONFIGS[Subject.MATH].keyterms)
        assert keyterms == expected
        assert "fraction" in keyterms

    def test_get_keyterms_physics(self):
        from src.education.subjects import get_keyterms

        keyterms = get_keyterms(Subject.PHYSICS)
        expected = list(SUBJECT_CONFIGS[Subject.PHYSICS].keyterms)
        assert keyterms == expected
        assert "Newton's laws" in keyterms

    def test_get_keyterms_returns_list(self):
        from src.education.subjects import get_keyterms

        result = get_keyterms(Subject.BIOLOGY)
        assert isinstance(result, list)

    def test_get_keyterms_nonexistent_subject_returns_empty(self):
        """If a subject is not in SUBJECT_CONFIGS, return empty list."""
        from src.education.subjects import get_keyterms

        # Create a mock subject that doesn't exist in configs
        mock_subject = MagicMock()
        result = get_keyterms(mock_subject)
        assert result == []


class TestSubjectTutorAgentKeyterms:
    def test_update_stt_keyterms_calls_update_options(self):
        """_update_stt_keyterms() should call stt.update_options with correct keyterms."""
        from src.agents.base import SubjectTutorAgent

        agent = SubjectTutorAgent.__new__(SubjectTutorAgent)
        agent._subject = Subject.BIOLOGY

        mock_stt = MagicMock()
        mock_stt.update_options = MagicMock()
        mock_session = SimpleNamespace(stt=mock_stt)
        agent._session = mock_session

        # Use the property-based access pattern
        type(agent).session = property(lambda self: self._session)
        agent._update_stt_keyterms()

        expected_keyterms = list(SUBJECT_CONFIGS[Subject.BIOLOGY].keyterms)
        mock_stt.update_options.assert_called_once_with(keyterm=expected_keyterms)

    def test_update_stt_keyterms_stt_none(self):
        """Should not crash when session.stt is None."""
        from src.agents.base import SubjectTutorAgent

        agent = SubjectTutorAgent.__new__(SubjectTutorAgent)
        agent._subject = Subject.BIOLOGY

        mock_session = SimpleNamespace(stt=None)
        agent._session = mock_session
        type(agent).session = property(lambda self: self._session)

        # Should not raise
        agent._update_stt_keyterms()

    def test_update_stt_keyterms_no_update_options(self):
        """Should not crash when stt has no update_options method."""
        from src.agents.base import SubjectTutorAgent

        agent = SubjectTutorAgent.__new__(SubjectTutorAgent)
        agent._subject = Subject.MATH

        # stt object without update_options
        mock_stt = SimpleNamespace()
        mock_session = SimpleNamespace(stt=mock_stt)
        agent._session = mock_session
        type(agent).session = property(lambda self: self._session)

        # Should not raise
        agent._update_stt_keyterms()

    def test_update_stt_keyterms_no_stt_attribute(self):
        """Should not crash when session has no stt attribute at all."""
        from src.agents.base import SubjectTutorAgent

        agent = SubjectTutorAgent.__new__(SubjectTutorAgent)
        agent._subject = Subject.PHYSICS

        mock_session = SimpleNamespace()  # No stt attribute
        agent._session = mock_session
        type(agent).session = property(lambda self: self._session)

        # Should not raise
        agent._update_stt_keyterms()


class TestSubjectAgentsInheritBase:
    """Verify that each subject agent inherits from SubjectTutorAgent."""

    def test_biology_inherits_subject_tutor_agent(self):
        from src.agents.base import SubjectTutorAgent
        from src.agents.biology import BiologyTutorAgent

        assert issubclass(BiologyTutorAgent, SubjectTutorAgent)

    def test_math_inherits_subject_tutor_agent(self):
        from src.agents.base import SubjectTutorAgent
        from src.agents.math import MathTutorAgent

        assert issubclass(MathTutorAgent, SubjectTutorAgent)

    def test_physics_inherits_subject_tutor_agent(self):
        from src.agents.base import SubjectTutorAgent
        from src.agents.physics import PhysicsTutorAgent

        assert issubclass(PhysicsTutorAgent, SubjectTutorAgent)

    def test_biology_has_correct_subject(self):
        from src.agents.biology import BiologyTutorAgent

        agent = BiologyTutorAgent()
        assert agent._subject == Subject.BIOLOGY

    def test_math_has_correct_subject(self):
        from src.agents.math import MathTutorAgent

        agent = MathTutorAgent()
        assert agent._subject == Subject.MATH

    def test_physics_has_correct_subject(self):
        from src.agents.physics import PhysicsTutorAgent

        agent = PhysicsTutorAgent()
        assert agent._subject == Subject.PHYSICS
