"""AvatarRenderer protocol and Simli adapter.

The AvatarRenderer protocol is defined in src/types.py and re-exported here.
SimliAvatarAdapter is a skeleton that will be completed in Phase 2.
"""

import structlog

from src.types import AvatarRenderer  # noqa: F401 — re-export for convenience

logger = structlog.get_logger(__name__)


class SimliAvatarAdapter:
    """Simli avatar adapter implementing the AvatarRenderer protocol.

    Phase 0: Skeleton only. Phase 2 will implement the full Simli integration.
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

    async def start(self, session, room) -> None:
        """Attach avatar to an AgentSession and LiveKit room.

        Raises NotImplementedError until Phase 2 implementation.
        """
        raise NotImplementedError(
            "SimliAvatarAdapter.start() will be implemented in Phase 2"
        )

    async def close(self) -> None:
        """Clean up avatar connection."""
        logger.info("simli_adapter_closed")
