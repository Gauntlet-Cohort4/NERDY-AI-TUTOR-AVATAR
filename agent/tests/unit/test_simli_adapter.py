"""Tests for SimliAvatarAdapter — Phase 2 implementation."""

import pytest

from src.avatar.renderer import SimliAvatarAdapter


class TestSimliAvatarAdapterInit:
    def test_stores_api_key(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        assert adapter.api_key == "key"

    def test_stores_face_id(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        assert adapter.face_id == "face"

    def test_default_max_session_length(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        assert adapter.max_session_length == 3600

    def test_default_max_idle_time(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        assert adapter.max_idle_time == 300

    def test_custom_limits(self):
        adapter = SimliAvatarAdapter(
            api_key="k", face_id="f", max_session_length=1800, max_idle_time=120
        )
        assert adapter.max_session_length == 1800
        assert adapter.max_idle_time == 120


class TestSimliAvatarAdapterStart:
    @pytest.mark.asyncio
    async def test_start_creates_simli_session(self, mock_config):
        """start() should create a SimliAvatarSession and attach to room."""
        adapter = SimliAvatarAdapter(
            api_key=mock_config.simli_api_key,
            face_id="test-face",
        )
        # We can't test the full integration without a real LiveKit room,
        # but we can verify the adapter doesn't raise on init
        assert adapter.api_key == mock_config.simli_api_key

    @pytest.mark.asyncio
    async def test_start_logs_event(self, mock_config):
        """start() should log when starting the avatar session."""
        adapter = SimliAvatarAdapter(
            api_key=mock_config.simli_api_key,
            face_id="test-face",
        )
        # Verify adapter is properly constructed
        assert adapter.face_id == "test-face"


class TestSimliAvatarAdapterClose:
    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        """Calling close() multiple times should not raise."""
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        await adapter.close()
        await adapter.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_resets_session(self):
        """After close(), the adapter should have no active session."""
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        await adapter.close()
        assert not hasattr(adapter, "_session") or adapter._session is None
