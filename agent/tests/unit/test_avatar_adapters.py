"""Tests for avatar adapters (Simli, Hedra, Beyond Presence) and the create_avatar factory."""

import pytest

from src.avatar.renderer import (
    BeyAvatarAdapter,
    HedraAvatarAdapter,
    SimliAvatarAdapter,
    create_avatar,
)
from src.config import AppConfig


# ── Simli ──────────────────────────────────────────────────────────────────


class TestSimliAvatarAdapterInit:
    def test_stores_api_key(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        assert adapter.api_key == "key"

    def test_stores_face_id(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        assert adapter.face_id == "face"

    def test_default_max_session_length(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        assert adapter.max_session_length == 600

    def test_default_max_idle_time(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        assert adapter.max_idle_time == 30

    def test_custom_limits(self):
        adapter = SimliAvatarAdapter(
            api_key="k", face_id="f", max_session_length=1800, max_idle_time=120
        )
        assert adapter.max_session_length == 1800
        assert adapter.max_idle_time == 120


class TestSimliAvatarAdapterStart:
    @pytest.mark.asyncio
    async def test_start_creates_simli_session(self, mock_config):
        adapter = SimliAvatarAdapter(
            api_key=mock_config.simli_api_key,
            face_id="test-face",
        )
        assert adapter.api_key == mock_config.simli_api_key

    @pytest.mark.asyncio
    async def test_start_logs_event(self, mock_config):
        adapter = SimliAvatarAdapter(
            api_key=mock_config.simli_api_key,
            face_id="test-face",
        )
        assert adapter.face_id == "test-face"


class TestSimliAvatarAdapterClose:
    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        await adapter.close()
        await adapter.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_resets_session(self):
        adapter = SimliAvatarAdapter(api_key="key", face_id="face")
        await adapter.close()
        assert adapter._session is None


# ── Hedra ──────────────────────────────────────────────────────────────────


class TestHedraAvatarAdapterInit:
    def test_stores_avatar_id(self):
        adapter = HedraAvatarAdapter(avatar_id="avatar-123")
        assert adapter.avatar_id == "avatar-123"

    def test_session_initially_none(self):
        adapter = HedraAvatarAdapter(avatar_id="avatar-123")
        assert adapter._session is None


class TestHedraAvatarAdapterClose:
    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        adapter = HedraAvatarAdapter(avatar_id="avatar-123")
        await adapter.close()
        await adapter.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_resets_session(self):
        adapter = HedraAvatarAdapter(avatar_id="avatar-123")
        await adapter.close()
        assert adapter._session is None


# ── Beyond Presence ────────────────────────────────────────────────────────


class TestBeyAvatarAdapterInit:
    def test_stores_api_key(self):
        adapter = BeyAvatarAdapter(api_key="bey-key", avatar_id="bey-avatar")
        assert adapter.api_key == "bey-key"

    def test_stores_avatar_id(self):
        adapter = BeyAvatarAdapter(api_key="bey-key", avatar_id="bey-avatar")
        assert adapter.avatar_id == "bey-avatar"

    def test_session_initially_none(self):
        adapter = BeyAvatarAdapter(api_key="bey-key", avatar_id="bey-avatar")
        assert adapter._session is None


class TestBeyAvatarAdapterClose:
    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        adapter = BeyAvatarAdapter(api_key="bey-key", avatar_id="bey-avatar")
        await adapter.close()
        await adapter.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_resets_session(self):
        adapter = BeyAvatarAdapter(api_key="bey-key", avatar_id="bey-avatar")
        await adapter.close()
        assert adapter._session is None


# ── Factory ────────────────────────────────────────────────────────────────


class TestCreateAvatar:
    def test_creates_simli_adapter(self, mock_config):
        config = AppConfig(
            **{**vars(mock_config), "avatar_provider": "simli"}
        )
        adapter = create_avatar(config)
        assert isinstance(adapter, SimliAvatarAdapter)
        assert adapter.api_key == config.simli_api_key
        assert adapter.face_id == config.simli_face_id

    def test_creates_hedra_adapter(self, mock_config):
        config = AppConfig(
            **{**vars(mock_config), "avatar_provider": "hedra"}
        )
        adapter = create_avatar(config)
        assert isinstance(adapter, HedraAvatarAdapter)
        assert adapter.avatar_id == config.hedra_avatar_id

    def test_creates_bey_adapter(self, mock_config):
        config = AppConfig(
            **{
                **vars(mock_config),
                "avatar_provider": "beyondpresence",
                "bey_api_key": "bey-key-123",
                "bey_avatar_id": "bey-avatar-456",
            }
        )
        adapter = create_avatar(config)
        assert isinstance(adapter, BeyAvatarAdapter)
        assert adapter.api_key == "bey-key-123"
        assert adapter.avatar_id == "bey-avatar-456"

    def test_unknown_provider_raises(self, mock_config):
        config = AppConfig(
            **{**vars(mock_config), "avatar_provider": "unknown"}
        )
        with pytest.raises(ValueError, match="Unknown avatar provider"):
            create_avatar(config)
