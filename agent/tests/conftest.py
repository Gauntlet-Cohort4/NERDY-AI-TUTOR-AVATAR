"""Shared test fixtures for the Nerdy AI Tutor agent tests."""

from types import SimpleNamespace

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
        # Avatar — default to simli for tests
        "AVATAR_PROVIDER": "simli",
        "SIMLI_API_KEY": "test_simli_key",
        "SIMLI_FACE_ID": "test_simli_face_id",
        "HEDRA_API_KEY": "test_hedra_key",
        "HEDRA_AVATAR_ID": "test_hedra_avatar_id",
        "BEY_API_KEY": "test_bey_key",
        "BEY_AVATAR_ID": "test_bey_avatar_id",
        # Optional — set to their expected defaults so .env never leaks
        "DEEPGRAM_MODEL": "nova-3",
        "GROQ_MODEL": "llama-3.3-70b-versatile",
        "CARTESIA_MODEL": "sonic-3",
        "CARTESIA_VOICE_ID": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
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
        avatar_provider="simli",
        simli_api_key="test_simli_key",
        simli_face_id="test_simli_face_id",
        hedra_api_key="test_hedra_key",
        hedra_avatar_id="test_hedra_avatar_id",
        bey_api_key="test_bey_key",
        bey_avatar_id="test_bey_avatar_id",
    )


def _make_eou_event(transcription_delay: float = 0.15):
    """Build a SimpleNamespace mimicking a MetricsCollectedEvent with EOUMetrics.

    ``transcription_delay`` is the time from end-of-speech to transcript ready —
    the authoritative STT processing latency from the livekit-agents pipeline.
    """
    from livekit.agents.metrics import EOUMetrics

    return SimpleNamespace(
        metrics=EOUMetrics(
            type="eou_metrics",
            timestamp=0.0,
            end_of_utterance_delay=0.05,
            transcription_delay=transcription_delay,
            on_user_turn_completed_delay=0.01,
        ),
    )


def _make_stt_event(duration: float = 0.25):
    """Build a SimpleNamespace mimicking a MetricsCollectedEvent with STTMetrics.

    Simulates streaming STT (Deepgram websocket): ``duration`` is always 0.0,
    ``audio_duration`` carries the pushed audio segment length.  The ``duration``
    parameter here maps to ``audio_duration`` on the STTMetrics object (used as
    fallback when no preceding EOU event provides ``transcription_delay``).
    """
    from livekit.agents.metrics import STTMetrics

    return SimpleNamespace(
        metrics=STTMetrics(
            type="stt_metrics",
            label="stt",
            request_id="req-stt",
            timestamp=0.0,
            duration=0.0,  # always 0 for streaming STT
            audio_duration=duration,  # fallback metric
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


def _send_full_turn(
    collector,
    stt_duration=0.25,
    llm_ttft=0.22,
    tts_ttfb=0.09,
    eou_transcription_delay=0.15,
):
    """Send a complete EOU -> STT -> LLM -> TTS metrics cycle, producing one TurnMetrics.

    Default ``eou_transcription_delay`` is 0.15s (150ms) — the real STT processing
    latency from the EOUMetrics event.  ``stt_duration`` is the audio_duration
    fallback (only used when no EOU event precedes the STT event).
    """
    collector.on_metrics(_make_eou_event(transcription_delay=eou_transcription_delay))
    collector.on_metrics(_make_stt_event(duration=stt_duration))
    collector.on_metrics(_make_llm_event(ttft=llm_ttft))
    collector.on_metrics(_make_tts_event(ttfb=tts_ttfb))


@pytest.fixture
def mock_metrics_event():
    """A list of four events (EOU, STT, LLM, TTS) mimicking a full pipeline turn.

    When all four are fed to ``on_metrics`` in order, the collector records
    one ``TurnMetrics`` with stt=150ms (from EOU transcription_delay=0.15),
    llm_ttft=220ms, tts_ttfb=90ms, total_e2e=460ms.
    """
    return [
        _make_eou_event(transcription_delay=0.15),
        _make_stt_event(duration=0.25),
        _make_llm_event(ttft=0.22),
        _make_tts_event(ttfb=0.09),
    ]


@pytest.fixture
def metrics_collector():
    """Return a fresh MetricsCollector."""
    from src.metrics import MetricsCollector

    return MetricsCollector(session_id="test-session")
