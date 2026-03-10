"""AvatarRenderer protocol and Simli adapter.

The AvatarRenderer protocol is defined in src/types.py and re-exported here.
SimliAvatarAdapter wraps livekit.plugins.simli.AvatarSession for video rendering.
"""

from __future__ import annotations

from typing import Optional

import structlog

from src.types import AvatarRenderer  # noqa: F401 — re-export for convenience

logger = structlog.get_logger(__name__)


class SimliAvatarAdapter:
    """Simli avatar adapter implementing the AvatarRenderer protocol.

    Wraps the Simli LiveKit plugin to render a talking-head avatar
    driven by TTS audio output from the pipeline.
    """

    def __init__(
        self,
        api_key: str,
        face_id: str,
        max_session_length: int = 3600,
        max_idle_time: int = 300,
    ):
        self.api_key = api_key
        self.face_id = face_id
        self.max_session_length = max_session_length
        self.max_idle_time = max_idle_time
        self._session: Optional[object] = None

    async def start(self, session, room) -> None:
        """Attach avatar to an AgentSession and LiveKit room.

        Creates a Simli AvatarSession and links it to the AgentSession
        so TTS audio drives the avatar's lip-sync and expressions.
        """
        try:
            from livekit.plugins.simli import AvatarSession

            self._session = AvatarSession(
                api_key=self.api_key,
                face_id=self.face_id,
                max_session_length=self.max_session_length,
                max_idle_time=self.max_idle_time,
            )
            await self._session.start(session, room=room)
            logger.info(
                "simli_avatar_started",
                face_id=self.face_id,
                max_session_length=self.max_session_length,
            )
        except ImportError:
            logger.warning(
                "simli_plugin_not_available",
                msg="livekit.plugins.simli not installed — avatar disabled",
            )
        except Exception as exc:
            logger.error(
                "simli_avatar_start_failed",
                error=str(exc),
                face_id=self.face_id,
            )

    async def close(self) -> None:
        """Clean up avatar connection."""
        if self._session is not None:
            try:
                await self._session.close()
            except Exception as exc:
                logger.warning("simli_close_error", error=str(exc))
            finally:
                self._session = None
        logger.info("simli_adapter_closed")
