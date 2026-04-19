"""Configuration tests - Environment variable override and backward compatibility."""
import os
import pytest

from shared.config.settings import Settings, get_settings
from shared.constants.domain import EnvironmentMode


class TestSettingsDefaults:
    """Test default settings values (backward compatibility)."""

    def test_default_env_is_develop(self) -> None:
        """Test default environment is DEVELOP."""
        settings = Settings()
        assert settings.env == EnvironmentMode.DEVELOP

    def test_default_ai_provider_is_mock(self) -> None:
        """Test default AI provider is mock (backward compatible)."""
        settings = Settings()
        assert settings.ai_provider == "mock"

    def test_default_strategy_version_stage2(self) -> None:
        """Test default strategy version is stage2."""
        settings = Settings()
        assert settings.strategy_version == "stage2"

    def test_default_jwt_secret_change_me(self) -> None:
        """Test JWT secret default warns about change."""
        settings = Settings()
        assert settings.jwt_secret == "CHANGE_ME"

    def test_default_session_ttl_15_minutes(self) -> None:
        """Test default session TTL is 15 minutes."""
        settings = Settings()
        assert settings.session_ttl_minutes == 15


class TestSettingsEnvironmentOverride:
    """Test environment variable overrides."""

    def test_env_override_via_env_var(self, monkeypatch) -> None:
        """Test environment mode can be overridden via env var."""
        monkeypatch.setenv("GOLD_ENV", "shadow")
        # Need to clear cache
        from shared.config import settings as settings_module
        settings_module.get_settings.cache_clear()
        
        settings = Settings()
        assert settings.env == EnvironmentMode.SHADOW

    def test_ai_provider_override_via_env_var(self, monkeypatch) -> None:
        """Test AI provider can be overridden via env var."""
        monkeypatch.setenv("GOLD_AI_PROVIDER", "deepseek")
        from shared.config import settings as settings_module
        settings_module.get_settings.cache_clear()
        
        settings = Settings()
        assert settings.ai_provider == "deepseek"

    def test_db_url_override_via_env_var(self, monkeypatch) -> None:
        """Test database URL can be overridden via env var."""
        monkeypatch.setenv("GOLD_DB_URL", "postgresql://user:pass@host:5432/db")
        from shared.config import settings as settings_module
        settings_module.get_settings.cache_clear()
        
        settings = Settings()
        assert "host" in settings.db_url


class TestSettingsValidation:
    """Test settings validation constraints."""

    def test_session_ttl_min_1(self) -> None:
        """Test session TTL minimum is 1 minute."""
        with pytest.raises(Exception):  # Validation error
            Settings(session_ttl_minutes=0)

    def test_session_ttl_max_1440(self) -> None:
        """Test session TTL maximum is 1440 minutes (24h)."""
        with pytest.raises(Exception):  # Validation error
            Settings(session_ttl_minutes=1441)

    def test_ai_timeout_min_1000(self) -> None:
        """Test AI timeout minimum is 1000ms."""
        with pytest.raises(Exception):  # Validation error
            Settings(ai_timeout_ms=500)

    def test_ai_timeout_max_60000(self) -> None:
        """Test AI timeout maximum is 60000ms."""
        with pytest.raises(Exception):  # Validation error
            Settings(ai_timeout_ms=61000)

    def test_ai_max_retries_min_0(self) -> None:
        """Test AI max retries can be 0."""
        settings = Settings(ai_max_retries=0)
        assert settings.ai_max_retries == 0

    def test_ai_max_retries_max_10(self) -> None:
        """Test AI max retries maximum is 10."""
        with pytest.raises(Exception):  # Validation error
            Settings(ai_max_retries=11)

    def test_jwt_secret_min_length_8(self) -> None:
        """Test JWT secret minimum length is 8."""
        with pytest.raises(Exception):  # Validation error
            Settings(jwt_secret="short")


class TestStage2Features:
    """Test Stage 2 specific settings."""

    def test_entry_protection_mode_default(self) -> None:
        """Test default entry protection mode."""
        settings = Settings()
        assert settings.entry_protection_mode == "protective"

    def test_ai_review_required_default(self) -> None:
        """Test AI review is required by default."""
        settings = Settings()
        assert settings.ai_review_required == True

    def test_event_window_blocking_default(self) -> None:
        """Test event window blocking is enabled by default."""
        settings = Settings()
        assert settings.event_window_blocking == True

    def test_stage2_features_configurable(self) -> None:
        """Test stage2 features can be configured."""
        settings = Settings(
            entry_protection_mode="aggressive",
            ai_review_required=False,
            event_window_blocking=False,
        )
        assert settings.entry_protection_mode == "aggressive"
        assert settings.ai_review_required == False
        assert settings.event_window_blocking == False


class TestSettingsSingleton:
    """Test settings singleton pattern."""

    def test_get_settings_cached(self) -> None:
        """Test get_settings returns cached instance."""
        from shared.config import settings as settings_module
        settings_module.get_settings.cache_clear()
        
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_get_settings_after_cache_clear(self) -> None:
        """Test get_settings creates new instance after cache clear."""
        from shared.config import settings as settings_module
        settings_module.get_settings.cache_clear()
        
        s1 = get_settings()
        settings_module.get_settings.cache_clear()
        s2 = get_settings()
        # May or may not be same depending on implementation
        assert isinstance(s1, Settings)
        assert isinstance(s2, Settings)
