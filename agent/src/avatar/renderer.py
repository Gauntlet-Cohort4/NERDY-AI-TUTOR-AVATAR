"""AvatarRenderer protocol, provider adapters, and factory.

The AvatarRenderer protocol is defined in src/types.py and re-exported here.
Use ``create_avatar(config)`` to get the correct adapter for the configured
AVATAR_PROVIDER ("simli", "hedra", or "beyondpresence").
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import structlog

from src.errors import ErrorSeverity, PipelineError, PipelineStage, handle_pipeline_error
from src.types import AvatarRenderer  # noqa: F401 — re-export for convenience

if TYPE_CHECKING:
    from src.config import AppConfig

logger = structlog.get_logger(__name__)


# ── Simli ──────────────────────────────────────────────────────────────────


class SimliAvatarAdapter:
    """Simli avatar adapter implementing the AvatarRenderer protocol.

    Wraps the Simli LiveKit plugin to render a talking-head avatar
    driven by TTS audio output from the pipeline.

    max_idle_time is intentionally omitted: room-level idle timeout
    (session_idle_timeout, default 180s) handles disconnection for all
    avatar providers uniformly.
    """

    def __init__(
        self,
        api_key: str,
        face_id: str,
        max_session_length: int = 600,
    ):
        self._api_key = api_key
        self._face_id = face_id
        self._max_session_length = max_session_length
        self._session: Optional[object] = None

    async def start(self, session, room) -> None:
        """Attach avatar to an AgentSession and LiveKit room."""
        try:
            from livekit.plugins.simli import AvatarSession, SimliConfig

            simli_config = SimliConfig(
                api_key=self._api_key,
                face_id=self._face_id,
                max_session_length=self._max_session_length,
            )
            self._session = AvatarSession(simli_config=simli_config)
            await self._session.start(session, room=room)
            logger.info(
                "avatar_started",
                provider="simli",
                face_id=self._face_id,
                max_session_length=self._max_session_length,
            )
        except ImportError:
            logger.warning(
                "avatar_plugin_not_available",
                provider="simli",
                msg="livekit.plugins.simli not installed — avatar disabled",
            )
        except Exception as exc:
            error = PipelineError(
                stage=PipelineStage.AVATAR,
                severity=ErrorSeverity.DEGRADED,
                message=f"Simli avatar failed to start: {exc}",
                original_exception=exc,
            )
            handle_pipeline_error(error)

    async def close(self) -> None:
        """Clean up avatar connection."""
        if self._session is not None:
            try:
                await self._session.close()
            except Exception as exc:
                logger.warning("avatar_close_error", provider="simli", error=str(exc))
            finally:
                self._session = None
        logger.info("avatar_adapter_closed", provider="simli")


# ── Hedra ──────────────────────────────────────────────────────────────────


class HedraAvatarAdapter:
    """Hedra avatar adapter implementing the AvatarRenderer protocol.

    Wraps the Hedra LiveKit plugin to render a talking-head avatar.
    Hedra reads HEDRA_API_KEY from the environment automatically.
    """

    def __init__(self, avatar_id: str):
        self._avatar_id = avatar_id
        self._session: Optional[object] = None

    async def start(self, session, room) -> None:
        """Attach avatar to an AgentSession and LiveKit room."""
        try:
            from livekit.plugins.hedra import AvatarSession

            self._session = AvatarSession(avatar_id=self._avatar_id)
            await self._session.start(session, room=room)
            logger.info(
                "avatar_started",
                provider="hedra",
                avatar_id=self._avatar_id,
            )
        except ImportError:
            logger.warning(
                "avatar_plugin_not_available",
                provider="hedra",
                msg="livekit.plugins.hedra not installed — avatar disabled",
            )
        except Exception as exc:
            error = PipelineError(
                stage=PipelineStage.AVATAR,
                severity=ErrorSeverity.DEGRADED,
                message=f"Hedra avatar failed to start: {exc}",
                original_exception=exc,
            )
            handle_pipeline_error(error)

    async def close(self) -> None:
        """Clean up avatar connection."""
        if self._session is not None:
            try:
                await self._session.close()
            except Exception as exc:
                logger.warning("avatar_close_error", provider="hedra", error=str(exc))
            finally:
                self._session = None
        logger.info("avatar_adapter_closed", provider="hedra")


# ── Beyond Presence ────────────────────────────────────────────────────────


class BeyAvatarAdapter:
    """Beyond Presence avatar adapter implementing the AvatarRenderer protocol.

    Wraps the Bey LiveKit plugin to render a talking-head avatar.
    Bey reads BEY_API_KEY from the environment automatically.
    """

    def __init__(self, api_key: str, avatar_id: str):
        self._api_key = api_key
        self._avatar_id = avatar_id
        self._session: Optional[object] = None

    async def start(self, session, room) -> None:
        """Attach avatar to an AgentSession and LiveKit room."""
        try:
            from livekit.plugins.bey import AvatarSession

            self._session = AvatarSession(
                api_key=self._api_key,
                avatar_id=self._avatar_id,
            )
            await self._session.start(session, room=room)
            logger.info(
                "avatar_started",
                provider="beyondpresence",
                avatar_id=self._avatar_id,
            )
        except ImportError:
            logger.warning(
                "avatar_plugin_not_available",
                provider="beyondpresence",
                msg="livekit.plugins.bey not installed — avatar disabled",
            )
        except Exception as exc:
            error = PipelineError(
                stage=PipelineStage.AVATAR,
                severity=ErrorSeverity.DEGRADED,
                message=f"Beyond Presence avatar failed to start: {exc}",
                original_exception=exc,
            )
            handle_pipeline_error(error)

    async def close(self) -> None:
        """Clean up avatar connection."""
        if self._session is not None:
            try:
                await self._session.close()
            except Exception as exc:
                logger.warning("avatar_close_error", provider="beyondpresence", error=str(exc))
            finally:
                self._session = None
        logger.info("avatar_adapter_closed", provider="beyondpresence")


# ── Factory ────────────────────────────────────────────────────────────────


def create_avatar(
    config: AppConfig,
) -> SimliAvatarAdapter | HedraAvatarAdapter | BeyAvatarAdapter:
    """Create the avatar adapter for the configured AVATAR_PROVIDER.

    Returns the appropriate adapter based on ``config.avatar_provider``.
    Unknown providers raise ValueError.
    """
    provider = config.avatar_provider

    if provider == "simli":
        logger.info("avatar_provider_selected", provider="simli")
        return SimliAvatarAdapter(
            api_key=config.simli_api_key,
            face_id=config.simli_face_id,
            max_session_length=config.simli_max_session_length,
        )

    if provider == "hedra":
        logger.info("avatar_provider_selected", provider="hedra")
        return HedraAvatarAdapter(avatar_id=config.hedra_avatar_id)

    if provider == "beyondpresence":
        logger.info("avatar_provider_selected", provider="beyondpresence")
        return BeyAvatarAdapter(
            api_key=config.bey_api_key,
            avatar_id=config.bey_avatar_id,
        )

    raise ValueError(
        f"Unknown avatar provider: '{provider}'. "
        "Must be 'simli', 'hedra', or 'beyondpresence'."
    )
