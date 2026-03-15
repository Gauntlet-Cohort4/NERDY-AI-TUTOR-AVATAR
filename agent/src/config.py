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

    # Groq (real-time tutoring LLM)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.7
    groq_max_tokens: int = 150

    # Artifact generation LLM (summaries, worksheets, cheat sheets, flash cards)
    artifact_llm_provider: str = "anthropic"  # "anthropic" or "groq"
    artifact_llm_model: str = ""  # resolved from provider if empty
    anthropic_api_key: str = ""

    # Cartesia
    cartesia_api_key: str = ""
    cartesia_model: str = "sonic-3"
    cartesia_voice_id: str = "f786b574-daa5-4673-aa0c-cbe3e8534c02"

    # Avatar provider — "simli", "hedra", or "beyondpresence"
    avatar_provider: str = "simli"

    # Simli
    simli_api_key: str = ""
    simli_face_id: str = ""
    simli_max_session_length: int = 3600

    # Hedra (reads HEDRA_API_KEY from env automatically)
    hedra_api_key: str = ""
    hedra_avatar_id: str = ""

    # Beyond Presence
    bey_api_key: str = ""
    bey_avatar_id: str = ""

    # Session
    session_idle_timeout: int = 180  # 3 minutes — disconnect room after no activity

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
        avatar_provider = os.getenv("AVATAR_PROVIDER", "simli").lower()

        required = [
            "LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
            "DEEPGRAM_API_KEY",
            "GROQ_API_KEY",
            "CARTESIA_API_KEY",
        ]
        # Require provider-specific keys
        if avatar_provider == "simli":
            required += ["SIMLI_API_KEY", "SIMLI_FACE_ID"]
        elif avatar_provider == "hedra":
            required += ["HEDRA_API_KEY", "HEDRA_AVATAR_ID"]
        elif avatar_provider == "beyondpresence":
            required += ["BEY_API_KEY", "BEY_AVATAR_ID"]
        else:
            raise EnvironmentError(
                f"Unknown AVATAR_PROVIDER '{avatar_provider}'. "
                "Must be 'simli', 'hedra', or 'beyondpresence'."
            )

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
            artifact_llm_provider=os.getenv("ARTIFACT_LLM_PROVIDER", "anthropic").lower(),
            artifact_llm_model=os.getenv("ARTIFACT_LLM_MODEL", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            cartesia_api_key=os.environ["CARTESIA_API_KEY"],
            cartesia_model=os.getenv("CARTESIA_MODEL", "sonic-3"),
            cartesia_voice_id=os.getenv(
                "CARTESIA_VOICE_ID", "f786b574-daa5-4673-aa0c-cbe3e8534c02"
            ),
            avatar_provider=avatar_provider,
            simli_api_key=os.getenv("SIMLI_API_KEY", ""),
            simli_face_id=os.getenv("SIMLI_FACE_ID", ""),
            hedra_api_key=os.getenv("HEDRA_API_KEY", ""),
            hedra_avatar_id=os.getenv("HEDRA_AVATAR_ID", ""),
            bey_api_key=os.getenv("BEY_API_KEY", ""),
            bey_avatar_id=os.getenv("BEY_AVATAR_ID", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            database_url=os.getenv("DATABASE_URL"),
            artifact_context_turns=int(os.getenv("ARTIFACT_CONTEXT_TURNS", "20")),
            groq_vision_model=os.getenv(
                "GROQ_VISION_MODEL", "llama-4-scout-17b-16e-instruct"
            ),
            image_gen_provider=os.getenv("IMAGE_GEN_PROVIDER", "none"),
            image_gen_api_key=os.getenv("IMAGE_GEN_API_KEY", ""),
            image_gen_model=os.getenv("IMAGE_GEN_MODEL", ""),
            session_idle_timeout=int(os.getenv("SESSION_IDLE_TIMEOUT", "180")),
        )

        # Resolve artifact LLM model default from provider if not set
        if not config.artifact_llm_model:
            _defaults = {
                "anthropic": "claude-sonnet-4-5-20250929",
                "groq": config.groq_model,
            }
            config.artifact_llm_model = _defaults.get(
                config.artifact_llm_provider, config.groq_model,
            )

        # Fall back to groq if anthropic is selected but no key is set
        if config.artifact_llm_provider == "anthropic" and not config.anthropic_api_key:
            logger.warning(
                "anthropic_api_key_missing",
                msg="ARTIFACT_LLM_PROVIDER=anthropic but no ANTHROPIC_API_KEY — falling back to groq",
            )
            config.artifact_llm_provider = "groq"
            config.artifact_llm_model = config.groq_model

        if config.database_url is None:
            logger.warning(
                "database_url_missing",
                msg="Running without persistence — session records, artifacts, and flash cards disabled",
            )

        logger.info(
            "config_loaded",
            livekit_url=config.livekit_url,
            groq_model=config.groq_model,
            artifact_llm=f"{config.artifact_llm_provider}/{config.artifact_llm_model}",
            avatar_provider=config.avatar_provider,
            database_configured=config.database_url is not None,
        )
        return config
