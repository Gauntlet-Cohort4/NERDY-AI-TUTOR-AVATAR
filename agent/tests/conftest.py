"""Shared test fixtures for the Nerdy AI Tutor agent tests."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set all environment variables to controlled values (required + optional defaults)."""
    env_vars = {
        # Required
        "LIVEKIT_URL": "wss://test.livekit.cloud",
        "LIVEKIT_API_KEY": "test_livekit_key",
        "LIVEKIT_API_SECRET": "test_livekit_secret",
        "DEEPGRAM_API_KEY": "test_deepgram_key",
        "GROQ_API_KEY": "test_groq_key",
        "CARTESIA_API_KEY": "test_cartesia_key",
        "SIMLI_API_KEY": "test_simli_key",
        # Optional — set to their expected defaults so .env never leaks
        "DEEPGRAM_MODEL": "nova-3",
        "GROQ_MODEL": "llama-3.3-70b-versatile",
        "CARTESIA_MODEL": "sonic-3",
        "CARTESIA_VOICE_ID": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
        "SIMLI_FACE_ID": "",
        "LOG_LEVEL": "INFO",
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


def _make_stt_event(duration: float = 0.25):
    """Build a SimpleNamespace mimicking a MetricsCollectedEvent with STTMetrics."""
    from livekit.agents.metrics import STTMetrics

    return SimpleNamespace(
        metrics=STTMetrics(
            type="stt_metrics",
            label="stt",
            request_id="req-stt",
            timestamp=0.0,
            duration=duration,
            audio_duration=duration,
            streamed=True,
        ),
    )


def _make_llm_event(ttft: float = 0.22, duration: float = 0.5):
    """Build a SimpleNamespace mimicking a MetricsCollectedEvent with LLMMetrics."""
    from livekit.agents.metrics import LLMMetrics

    return SimpleNamespace(
        metrics=LLMMetrics(
            type="llm_metrics",
            label="llm",
            request_id="req-llm",
            timestamp=0.0,
            duration=duration,
            ttft=ttft,
            cancelled=False,
            completion_tokens=0,
            prompt_tokens=0,
            prompt_cached_tokens=0,
            total_tokens=0,
            tokens_per_second=0.0,
        ),
    )


def _make_tts_event(ttfb: float = 0.09, duration: float = 0.3):
    """Build a SimpleNamespace mimicking a MetricsCollectedEvent with TTSMetrics."""
    from livekit.agents.metrics import TTSMetrics

    return SimpleNamespace(
        metrics=TTSMetrics(
            type="tts_metrics",
            label="tts",
            request_id="req-tts",
            timestamp=0.0,
            ttfb=ttfb,
            duration=duration,
            audio_duration=duration,
            cancelled=False,
            characters_count=0,
            streamed=True,
        ),
    )


def _send_full_turn(collector, stt_duration=0.25, llm_ttft=0.22, tts_ttfb=0.09):
    """Send a complete STT -> LLM -> TTS metrics cycle, producing one TurnMetrics."""
    collector.on_metrics(_make_stt_event(duration=stt_duration))
    collector.on_metrics(_make_llm_event(ttft=llm_ttft))
    collector.on_metrics(_make_tts_event(ttfb=tts_ttfb))


@pytest.fixture
def mock_metrics_event():
    """A list of three events (STT, LLM, TTS) mimicking a full pipeline turn.

    When all three are fed to ``on_metrics`` in order, the collector records
    one ``TurnMetrics`` with stt=250ms, llm_ttft=220ms, tts_ttfb=90ms,
    total_e2e=560ms (sum of stage timings).
    """
    return [
        _make_stt_event(duration=0.25),
        _make_llm_event(ttft=0.22),
        _make_tts_event(ttfb=0.09),
    ]


@pytest.fixture
def metrics_collector():
    """Return a fresh MetricsCollector."""
    from src.metrics import MetricsCollector

    return MetricsCollector(session_id="test-session")
