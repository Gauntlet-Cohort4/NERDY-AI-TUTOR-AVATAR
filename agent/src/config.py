"""Central config loader — loads from environment variables with fail-fast validation.

Usage:
    from src.logging_setup import setup_logging
    setup_logging()  # Must be called before from_env()

    from src.config import AppConfig
    config = AppConfig.from_env()

Rule: No os.getenv() calls outside this module. All modules receive config
through dependency injection.
"""

import os
from dataclasses import dataclass

import structlog
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger(__name__)


@dataclass
class AppConfig:
    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Deepgram
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-3"
    deepgram_language: str = "en-US"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.7
    groq_max_tokens: int = 150

    # Cartesia
    cartesia_api_key: str = ""
    cartesia_model: str = "sonic-3"
    cartesia_voice_id: str = "f786b574-daa5-4673-aa0c-cbe3e8534c02"

    # Simli
    simli_api_key: str = ""
    simli_face_id: str = ""
    simli_max_session_length: int = 3600
    simli_max_idle_time: int = 300

    # Application
    log_level: str = "INFO"
    max_conversation_turns: int = 10
    summarization_threshold: int = 10
    token_budget: int = 2000
    vad_silence_threshold_ms: int = 500

    # Database (optional — degrades gracefully if missing)
    database_url: str | None = None

    # Artifacts
    artifact_context_turns: int = 20

    # Vision / Image generation
    groq_vision_model: str = "llama-4-scout-17b-16e-instruct"
    image_gen_provider: str = "none"
    image_gen_api_key: str = ""
    image_gen_model: str = ""

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load config from environment variables. Fails fast on missing required vars."""
        required = [
            "LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
            "DEEPGRAM_API_KEY",
            "GROQ_API_KEY",
            "CARTESIA_API_KEY",
            "SIMLI_API_KEY",
            "SIMLI_FACE_ID",
        ]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

        config = cls(
            livekit_url=os.environ["LIVEKIT_URL"],
            livekit_api_key=os.environ["LIVEKIT_API_KEY"],
            livekit_api_secret=os.environ["LIVEKIT_API_SECRET"],
            deepgram_api_key=os.environ["DEEPGRAM_API_KEY"],
            deepgram_model=os.getenv("DEEPGRAM_MODEL", "nova-3"),
            groq_api_key=os.environ["GROQ_API_KEY"],
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            cartesia_api_key=os.environ["CARTESIA_API_KEY"],
            cartesia_model=os.getenv("CARTESIA_MODEL", "sonic-3"),
            cartesia_voice_id=os.getenv(
                "CARTESIA_VOICE_ID", "f786b574-daa5-4673-aa0c-cbe3e8534c02"
            ),
            simli_api_key=os.environ["SIMLI_API_KEY"],
            simli_face_id=os.environ["SIMLI_FACE_ID"],
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            database_url=os.getenv("DATABASE_URL"),
            artifact_context_turns=int(os.getenv("ARTIFACT_CONTEXT_TURNS", "20")),
            groq_vision_model=os.getenv(
                "GROQ_VISION_MODEL", "llama-4-scout-17b-16e-instruct"
            ),
            image_gen_provider=os.getenv("IMAGE_GEN_PROVIDER", "none"),
            image_gen_api_key=os.getenv("IMAGE_GEN_API_KEY", ""),
            image_gen_model=os.getenv("IMAGE_GEN_MODEL", ""),
        )

        if config.database_url is None:
            logger.warning(
                "database_url_missing",
                msg="Running without persistence — session records, artifacts, and flash cards disabled",
            )

        logger.info(
            "config_loaded",
            livekit_url=config.livekit_url,
            groq_model=config.groq_model,
            database_configured=config.database_url is not None,
        )
        return config
