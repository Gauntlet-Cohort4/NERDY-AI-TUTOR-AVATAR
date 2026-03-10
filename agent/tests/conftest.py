"""Shared test fixtures for the Nerdy AI Tutor agent tests."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set all required environment variables to dummy values."""
    env_vars = {
        "LIVEKIT_URL": "wss://test.livekit.cloud",
        "LIVEKIT_API_KEY": "test_livekit_key",
        "LIVEKIT_API_SECRET": "test_livekit_secret",
        "DEEPGRAM_API_KEY": "test_deepgram_key",
        "GROQ_API_KEY": "test_groq_key",
        "CARTESIA_API_KEY": "test_cartesia_key",
        "SIMLI_API_KEY": "test_simli_key",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_config():
    """Return an AppConfig instance with dummy values (constructed directly)."""
    from src.config import AppConfig

    return AppConfig(
        livekit_url="wss://test.livekit.cloud",
        livekit_api_key="test_livekit_key",
        livekit_api_secret="test_livekit_secret",
        deepgram_api_key="test_deepgram_key",
        groq_api_key="test_groq_key",
        cartesia_api_key="test_cartesia_key",
        simli_api_key="test_simli_key",
    )


@pytest.fixture
def mock_metrics_event():
    """A SimpleNamespace mimicking an AgentSession metrics event."""
    return SimpleNamespace(
        stt_duration=0.25,
        llm_ttft=0.22,
        tts_ttfb=0.09,
        e2e_duration=0.65,
    )


@pytest.fixture
def metrics_collector():
    """Return a fresh MetricsCollector."""
    from src.metrics import MetricsCollector

    return MetricsCollector(session_id="test-session")
