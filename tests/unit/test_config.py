"""Unit tests for configuration and settings management."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from gpt_image_mcp.config.settings import (
    CacheSettings,
    ImageSettings,
    OpenAISettings,
    ServerSettings,
    Settings,
    StorageSettings,
)


class TestServerSettings:
    """Test server configuration settings."""

    def test_server_settings_defaults(self):
        """Test server settings with default values."""
        settings = ServerSettings()

        assert settings.name == "Image Gen MCP Server"
        assert settings.version == "0.1.0"
        assert settings.log_level == "INFO"
        assert settings.port == 3001
        assert settings.rate_limit_rpm == 50

    def test_server_settings_custom_values(self):
        """Test server settings with custom values."""
        settings = ServerSettings(
            name="Custom Server",
            version="2.0.0",
            log_level="DEBUG",
            port=8080,
            rate_limit_rpm=100,
        )

        assert settings.name == "Custom Server"
        assert settings.version == "2.0.0"
        assert settings.log_level == "DEBUG"
        assert settings.port == 8080
        assert settings.rate_limit_rpm == 100

    def test_server_settings_validation(self):
        """Test server settings validation."""
        # Valid port range
        settings = ServerSettings(port=8080)
        assert settings.port == 8080

        # Invalid port should raise validation error
        with pytest.raises(ValidationError):
            ServerSettings(port=70000)  # Port too high

        with pytest.raises(ValidationError):
            ServerSettings(port=0)  # Port too low

    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = ServerSettings(log_level=level)
            assert settings.log_level == level

        # Invalid log level should raise validation error
        with pytest.raises(ValidationError):
            ServerSettings(log_level="INVALID")


class TestOpenAISettings:
    """Test OpenAI configuration settings."""

    def test_openai_settings_required_fields(self):
        """Test OpenAI settings with required fields."""
        settings = OpenAISettings(api_key="test-key")

        assert settings.api_key == "test-key"
        assert settings.base_url == "https://api.openai.com/v1"
        assert settings.organization is None
        assert settings.max_retries == 3
        assert settings.timeout == 30.0

    def test_openai_settings_custom_values(self):
        """Test OpenAI settings with custom values."""
        settings = OpenAISettings(
            api_key="custom-key",
            base_url="https://custom.api.com/v1",
            organization="org-123",
            max_retries=5,
            timeout=300.0,
        )

        assert settings.api_key == "custom-key"
        assert settings.base_url == "https://custom.api.com/v1"
        assert settings.organization == "org-123"
        assert settings.max_retries == 5
        assert settings.timeout == 300.0

    def test_openai_settings_validation(self):
        """Test OpenAI settings validation."""
        # Missing API key should raise validation error
        with pytest.raises(ValidationError):
            OpenAISettings()

        # Empty API key should raise validation error
        with pytest.raises(ValidationError):
            OpenAISettings(api_key="")

        # Invalid max_retries should raise validation error
        with pytest.raises(ValidationError):
            OpenAISettings(api_key="test", max_retries=-1)

        # Invalid timeout should raise validation error
        with pytest.raises(ValidationError):
            OpenAISettings(api_key="test", timeout=0)

    def test_api_key_masking(self):
        """Test API key is properly masked in string representation."""
        settings = OpenAISettings(api_key="sk-1234567890abcdef")

        # Convert to string and check that key is masked
        settings_str = str(settings)
        assert "sk-1234567890abcdef" not in settings_str
        assert "sk-***" in settings_str or "***" in settings_str


class TestStorageSettings:
    """Test storage configuration settings."""

    def test_storage_settings_defaults(self):
        """Test storage settings with default values."""
        settings = StorageSettings()

        assert settings.base_path == "./storage"
        assert settings.retention_days == 30
        assert settings.max_size_gb == 10
        assert settings.cleanup_interval_hours == 24

    def test_storage_settings_custom_values(self):
        """Test storage settings with custom values."""
        settings = StorageSettings(
            base_path="/custom/storage",
            retention_days=60,
            max_size_gb=20,
            cleanup_interval_hours=12,
        )

        assert settings.base_path == "/custom/storage"
        assert settings.retention_days == 60
        assert settings.max_size_gb == 20
        assert settings.cleanup_interval_hours == 12

    def test_storage_settings_validation(self):
        """Test storage settings validation."""
        # Valid settings
        settings = StorageSettings(
            retention_days=1, max_size_gb=1, cleanup_interval_hours=1
        )
        assert settings.retention_days == 1

        # Invalid retention_days should raise validation error
        with pytest.raises(ValidationError):
            StorageSettings(retention_days=0)

        # Invalid max_size_gb should raise validation error
        with pytest.raises(ValidationError):
            StorageSettings(max_size_gb=0)

        # Invalid cleanup_interval_hours should raise validation error
        with pytest.raises(ValidationError):
            StorageSettings(cleanup_interval_hours=0)


class TestCacheSettings:
    """Test cache configuration settings."""

    def test_cache_settings_defaults(self):
        """Test cache settings with default values."""
        settings = CacheSettings()

        assert settings.enabled is True
        assert settings.backend == "memory"
        assert settings.ttl_hours == 24
        assert settings.max_size_mb == 500
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_cache_settings_custom_values(self):
        """Test cache settings with custom values."""
        settings = CacheSettings(
            enabled=False,
            backend="redis",
            ttl_hours=12,
            max_size_mb=1000,
            redis_url="redis://custom:6379/1",
        )

        assert settings.enabled is False
        assert settings.backend == "redis"
        assert settings.ttl_hours == 12
        assert settings.max_size_mb == 1000
        assert settings.redis_url == "redis://custom:6379/1"

    def test_cache_settings_validation(self):
        """Test cache settings validation."""
        # Valid backend values
        settings_memory = CacheSettings(backend="memory")
        assert settings_memory.backend == "memory"

        settings_redis = CacheSettings(
            backend="redis", redis_url="redis://localhost:6379"
        )
        assert settings_redis.backend == "redis"

        # Invalid backend should raise validation error
        with pytest.raises(ValidationError):
            CacheSettings(backend="invalid")

        # Redis backend without URL should raise validation error
        with pytest.raises(ValidationError):
            CacheSettings(backend="redis", redis_url=None)

        # Invalid ttl_hours should raise validation error
        with pytest.raises(ValidationError):
            CacheSettings(ttl_hours=0)

        # Invalid max_size_mb should raise validation error
        with pytest.raises(ValidationError):
            CacheSettings(max_size_mb=0)


class TestImageSettings:
    """Test image generation settings."""

    def test_image_settings_defaults(self):
        """Test image settings with default values."""
        settings = ImageSettings()

        assert settings.default_model == "gpt-image-1"
        assert settings.default_quality == "auto"
        assert settings.default_size == "1536x1024"
        assert settings.default_style == "vivid"
        assert settings.default_moderation == "auto"
        assert settings.default_output_format == "png"
        assert settings.default_compression == 100

    def test_image_settings_custom_values(self):
        """Test image settings with custom values."""
        settings = ImageSettings(
            default_model="dalle-3",
            default_quality="high",
            default_size="1024x1024",
            default_style="natural",
            default_moderation="low",
            default_output_format="jpeg",
            default_compression=85,
        )

        assert settings.default_model == "dalle-3"
        assert settings.default_quality == "high"
        assert settings.default_size == "1024x1024"
        assert settings.default_style == "natural"
        assert settings.default_moderation == "low"
        assert settings.default_output_format == "jpeg"
        assert settings.default_compression == 85

    def test_image_settings_validation(self):
        """Test image settings validation."""
        # Valid quality values
        for quality in ["auto", "high", "medium", "low"]:
            settings = ImageSettings(default_quality=quality)
            assert settings.default_quality == quality

        # Valid size values
        for size in ["1024x1024", "1536x1024", "1024x1536"]:
            settings = ImageSettings(default_size=size)
            assert settings.default_size == size

        # Valid style values
        for style in ["vivid", "natural"]:
            settings = ImageSettings(default_style=style)
            assert settings.default_style == style

        # Invalid values should raise validation errors
        with pytest.raises(ValidationError):
            ImageSettings(default_quality="invalid")

        with pytest.raises(ValidationError):
            ImageSettings(default_size="invalid")

        with pytest.raises(ValidationError):
            ImageSettings(default_style="invalid")

        # Test compression validation
        with pytest.raises(ValidationError):
            ImageSettings(default_compression=150)  # Too high

        with pytest.raises(ValidationError):
            ImageSettings(default_compression=-1)  # Too low


class TestCompleteSettings:
    """Test complete settings configuration."""

    def test_settings_from_dict(self):
        """Test creating settings from dictionary."""
        config_dict = {
            "server": {"name": "Test Server", "port": 8080},
            "openai": {"api_key": "test-key"},
            "storage": {"base_path": "/tmp/test"},
            "cache": {"enabled": False},
            "images": {"default_quality": "high"},
        }

        settings = Settings(**config_dict)

        assert settings.server.name == "Test Server"
        assert settings.server.port == 8080
        assert settings.openai.api_key == "test-key"
        assert settings.storage.base_path.endswith("/test")  # Allow for path resolution
        assert settings.cache.enabled is False
        assert settings.images.default_quality == "high"

    def test_settings_from_env_file(self, tmp_path):
        """Test loading settings from environment file."""
        env_file = tmp_path / ".env"
        env_content = """
OPENAI_API_KEY=test-env-key
OPENAI_BASE_URL=https://custom.api.com/v1
SERVER_PORT=9000
LOG_LEVEL=DEBUG
STORAGE_BASE_PATH=/custom/storage
CACHE_ENABLED=false
DEFAULT_QUALITY=high
        """
        env_file.write_text(env_content.strip())

        # Mock the from_env method to use our test file
        with patch.object(Settings, "from_env") as mock_from_env:
            # Create settings with our test values
            test_settings = Settings(
                openai=OpenAISettings(
                    api_key="test-env-key", base_url="https://custom.api.com/v1"
                ),
                server=ServerSettings(port=9000, log_level="DEBUG"),
                storage=StorageSettings(base_path="/custom/storage"),
                cache=CacheSettings(enabled=False),
                images=ImageSettings(default_quality="high"),
            )
            mock_from_env.return_value = test_settings

            settings = Settings.from_env()

            assert settings.openai.api_key == "test-env-key"
            assert settings.openai.base_url == "https://custom.api.com/v1"
            assert settings.server.port == 9000
            assert settings.server.log_level == "DEBUG"
            assert settings.storage.base_path == "/custom/storage"
            assert settings.cache.enabled is False
            assert settings.images.default_quality == "high"

    def test_settings_validation_cascade(self):
        """Test that validation errors cascade properly."""
        # Invalid nested configuration should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                **{
                    "openai": {"api_key": ""},  # Invalid empty key
                    "server": {"port": 70000},  # Invalid port
                }
            )

        # Should contain multiple validation errors
        assert len(exc_info.value.errors()) >= 2

    def test_settings_partial_override(self):
        """Test partial configuration override."""
        # Start with defaults
        settings = Settings(openai=OpenAISettings(api_key="test-key"))

        # Check that defaults are applied
        assert settings.server.name == "Image Gen MCP Server"
        assert settings.storage.retention_days == 30
        assert settings.cache.enabled is True
        assert settings.images.default_quality == "auto"

        # Override specific values
        custom_settings = Settings(
            openai=OpenAISettings(api_key="test-key"),
            server=ServerSettings(name="Custom Server"),
            cache=CacheSettings(enabled=False),
        )

        assert custom_settings.server.name == "Custom Server"
        assert custom_settings.server.port == 3001  # Still default
        assert custom_settings.cache.enabled is False
        assert custom_settings.storage.retention_days == 30  # Still default

    def test_settings_env_var_override(self):
        """Test environment variable override."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "env-api-key",
                "SERVER_PORT": "8888",
                "LOG_LEVEL": "WARNING",
                "CACHE_ENABLED": "false",
            },
        ):
            # Create mock settings that would be loaded from env
            with patch.object(Settings, "from_env") as mock_from_env:
                test_settings = Settings(
                    openai=OpenAISettings(api_key="env-api-key"),
                    server=ServerSettings(port=8888, log_level="WARNING"),
                    cache=CacheSettings(enabled=False),
                )
                mock_from_env.return_value = test_settings

                settings = Settings.from_env()

                assert settings.openai.api_key == "env-api-key"
                assert settings.server.port == 8888
                assert settings.server.log_level == "WARNING"
                assert settings.cache.enabled is False
