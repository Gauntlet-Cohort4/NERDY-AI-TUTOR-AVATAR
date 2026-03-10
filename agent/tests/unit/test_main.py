"""Tests for main.py entrypoint — Phase 2."""

from unittest.mock import patch, MagicMock

import pytest


class TestEntrypointFunction:
    def test_entrypoint_is_importable(self):
        """The entrypoint function should be importable."""
        from main import entrypoint
        assert callable(entrypoint)

    def test_entrypoint_creates_agent_session(self, mock_config):
        """entrypoint() should return a configured AgentSession."""
        from main import create_agent_session
        session = create_agent_session(mock_config)
        assert session is not None

    def test_create_agent_session_uses_router(self, mock_config):
        """The agent session should start with SubjectRouterAgent."""
        from main import create_agent_session
        session = create_agent_session(mock_config)
        assert session.agent_name == "SubjectRouterAgent"

    def test_create_agent_session_has_stt(self, mock_config):
        """The agent session should have STT configured."""
        from main import create_agent_session
        session = create_agent_session(mock_config)
        assert session.stt_provider == "deepgram"

    def test_create_agent_session_has_llm(self, mock_config):
        """The agent session should have LLM configured."""
        from main import create_agent_session
        session = create_agent_session(mock_config)
        assert session.llm_provider == "groq"

    def test_create_agent_session_has_tts(self, mock_config):
        """The agent session should have TTS configured."""
        from main import create_agent_session
        session = create_agent_session(mock_config)
        assert session.tts_provider == "cartesia"


class TestHealthCheck:
    def test_health_check_available(self):
        """A health check function should be importable from main."""
        from main import health_check
        result = health_check()
        assert result["status"] == "healthy"
        assert "service" in result
        assert "timestamp" in result
