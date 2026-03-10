"""Tests for AvatarRenderer protocol and SimliAvatarAdapter.

Requirement mapping:
- test_avatar_renderer_protocol_* → Protocol abstraction layer
- test_simli_adapter_* → Simli adapter skeleton compliance
"""

from unittest.mock import AsyncMock

import pytest
from src.types import AvatarRenderer
from src.avatar.renderer import SimliAvatarAdapter


class TestAvatarRendererProtocol:
    def test_avatar_renderer_protocol_has_start(self):
        assert hasattr(AvatarRenderer, "start")

    def test_avatar_renderer_protocol_has_close(self):
        assert hasattr(AvatarRenderer, "close")

    def test_mock_avatar_satisfies_protocol(self):
        class MockAvatar:
            async def start(self, session, room) -> None:
                pass

            async def close(self) -> None:
                pass

        mock = MockAvatar()
        assert isinstance(mock, AvatarRenderer)


class TestSimliAvatarAdapter:
    def test_simli_adapter_exists(self):
        assert SimliAvatarAdapter is not None

    def test_simli_adapter_satisfies_protocol(self):
        adapter = SimliAvatarAdapter(api_key="test", face_id="test-face")
        assert isinstance(adapter, AvatarRenderer)

    @pytest.mark.asyncio
    async def test_simli_adapter_start_not_implemented(self):
        adapter = SimliAvatarAdapter(api_key="test", face_id="test-face")
        mock_session = AsyncMock()
        mock_room = AsyncMock()
        with pytest.raises(NotImplementedError):
            await adapter.start(mock_session, mock_room)

    @pytest.mark.asyncio
    async def test_simli_adapter_close_succeeds(self):
        adapter = SimliAvatarAdapter(api_key="test", face_id="test-face")
        await adapter.close()  # Should not raise
