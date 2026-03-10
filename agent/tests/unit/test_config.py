"""Tests for AppConfig.

Requirement mapping:
- test_config_loads_from_env → Config loads all required vars
- test_config_fails_on_missing_var → Fail-fast on missing required var
- test_config_fails_on_multiple_missing → Lists ALL missing vars
- test_config_defaults_applied → Correct defaults for optional vars
- test_config_overrides_defaults → Env vars override defaults
"""

import pytest
from src.config import AppConfig


class TestConfigLoadsFromEnv:
    def test_config_loads_from_env(self, mock_env_vars):
        config = AppConfig.from_env()
        assert config.livekit_url == "wss://test.livekit.cloud"
        assert config.livekit_api_key == "test_livekit_key"
        assert config.livekit_api_secret == "test_livekit_secret"
        assert config.deepgram_api_key == "test_deepgram_key"
        assert config.groq_api_key == "test_groq_key"
        assert config.cartesia_api_key == "test_cartesia_key"
        assert config.simli_api_key == "test_simli_key"


class TestConfigFailsFast:
    def test_config_fails_on_missing_required_var(self, mock_env_vars, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY")
        with pytest.raises(EnvironmentError, match="GROQ_API_KEY"):
            AppConfig.from_env()

    def test_config_fails_on_multiple_missing_vars(self, monkeypatch):
        monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
        monkeypatch.setenv("LIVEKIT_API_KEY", "test")
        # Missing: LIVEKIT_API_SECRET, DEEPGRAM_API_KEY, GROQ_API_KEY, CARTESIA_API_KEY, SIMLI_API_KEY
        for key in ["LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY", "GROQ_API_KEY", "CARTESIA_API_KEY", "SIMLI_API_KEY"]:
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(EnvironmentError) as exc_info:
            AppConfig.from_env()
        error_msg = str(exc_info.value)
        for key in ["LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY", "GROQ_API_KEY", "CARTESIA_API_KEY", "SIMLI_API_KEY"]:
            assert key in error_msg


class TestConfigDefaults:
    def test_config_defaults_applied(self, mock_env_vars, monkeypatch):
        # Clear optional vars that might leak from .env
        for key in ["DEEPGRAM_MODEL", "GROQ_MODEL", "CARTESIA_MODEL", "CARTESIA_VOICE_ID", "LOG_LEVEL", "SIMLI_FACE_ID"]:
            monkeypatch.delenv(key, raising=False)
        config = AppConfig.from_env()
        assert config.deepgram_model == "nova-3"
        assert config.groq_model == "llama-3.3-70b-versatile"
        assert config.cartesia_model == "sonic-3"
        assert config.cartesia_voice_id == "f786b574-daa5-4673-aa0c-cbe3e8534c02"
        assert config.log_level == "INFO"
        assert config.groq_temperature == 0.7
        assert config.groq_max_tokens == 150
        assert config.max_conversation_turns == 10
        assert config.summarization_threshold == 10
        assert config.token_budget == 2000

    def test_config_overrides_defaults(self, mock_env_vars, monkeypatch):
        monkeypatch.setenv("GROQ_MODEL", "custom-model")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        config = AppConfig.from_env()
        assert config.groq_model == "custom-model"
        assert config.log_level == "DEBUG"
