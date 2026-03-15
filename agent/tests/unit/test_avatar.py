"""Tests for AvatarRenderer protocol and adapter compliance.

Requirement mapping:
- test_avatar_renderer_protocol_* → Protocol abstraction layer
- test_simli_adapter_* → Simli adapter protocol compliance
- test_hedra_adapter_* → Hedra adapter protocol compliance
"""

from unittest.mock import AsyncMock

import pytest

from src.avatar.renderer import HedraAvatarAdapter, SimliAvatarAdapter
from src.types import AvatarRenderer


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
    async def test_simli_adapter_start_graceful_without_plugin(self):
        """start() should not raise even if simli plugin is unavailable."""
        adapter = SimliAvatarAdapter(api_key="test", face_id="test-face")
        mock_session = AsyncMock()
        mock_room = AsyncMock()
        await adapter.start(mock_session, mock_room)  # Should not raise

    @pytest.mark.asyncio
    async def test_simli_adapter_close_succeeds(self):
        adapter = SimliAvatarAdapter(api_key="test", face_id="test-face")
        await adapter.close()  # Should not raise


class TestHedraAvatarAdapter:
    def test_hedra_adapter_exists(self):
        assert HedraAvatarAdapter is not None

    def test_hedra_adapter_satisfies_protocol(self):
        adapter = HedraAvatarAdapter(avatar_id="test-avatar")
        assert isinstance(adapter, AvatarRenderer)

    @pytest.mark.asyncio
    async def test_hedra_adapter_start_graceful_without_plugin(self):
        """start() should not raise even if hedra plugin is unavailable."""
        adapter = HedraAvatarAdapter(avatar_id="test-avatar")
        mock_session = AsyncMock()
        mock_room = AsyncMock()
        await adapter.start(mock_session, mock_room)  # Should not raise

    @pytest.mark.asyncio
    async def test_hedra_adapter_close_succeeds(self):
        adapter = HedraAvatarAdapter(avatar_id="test-avatar")
        await adapter.close()  # Should not raise
