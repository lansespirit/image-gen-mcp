"""Unit tests for utility functions including validators, cache, and OpenAI client."""

import base64
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest

from gpt_image_mcp.types.enums import (
    ImageQuality,
    ImageSize,
    ImageStyle,
    ModerationLevel,
    OutputFormat,
    BackgroundType
)
from gpt_image_mcp.utils.validators import (
    normalize_enum_value,
    validate_image_quality,
    validate_image_size,
    validate_image_style,
    validate_moderation_level,
    validate_output_format,
    validate_background_type,
    validate_compression,
    validate_limit,
    validate_days,
    sanitize_prompt,
    validate_base64_image
)
from gpt_image_mcp.utils.cache import MemoryCache, CacheManager
from gpt_image_mcp.utils.openai_client import OpenAIClientManager


class TestEnumValidators:
    """Test enum validation and normalization functions."""
    
    def test_normalize_enum_value_exact_match(self):
        """Test exact value matching."""
        assert normalize_enum_value("auto", ImageQuality) == ImageQuality.AUTO
        assert normalize_enum_value("high", ImageQuality) == ImageQuality.HIGH
        assert normalize_enum_value("vivid", ImageStyle) == ImageStyle.VIVID
    
    def test_normalize_enum_value_case_insensitive(self):
        """Test case-insensitive matching."""
        assert normalize_enum_value("AUTO", ImageQuality) == ImageQuality.AUTO
        assert normalize_enum_value("High", ImageQuality) == ImageQuality.HIGH
        assert normalize_enum_value("VIVID", ImageStyle) == ImageStyle.VIVID
        assert normalize_enum_value("natural", ImageStyle) == ImageStyle.NATURAL
    
    def test_normalize_enum_value_with_whitespace(self):
        """Test handling of whitespace."""
        assert normalize_enum_value("  auto  ", ImageQuality) == ImageQuality.AUTO
        assert normalize_enum_value("\thigh\n", ImageQuality) == ImageQuality.HIGH
    
    def test_normalize_enum_value_with_default(self):
        """Test fallback to default values."""
        assert normalize_enum_value("invalid", ImageQuality, ImageQuality.MEDIUM) == ImageQuality.MEDIUM
        assert normalize_enum_value(None, ImageQuality, ImageQuality.AUTO) == ImageQuality.AUTO
        assert normalize_enum_value("", ImageStyle, ImageStyle.NATURAL) == ImageStyle.NATURAL
    
    def test_normalize_enum_value_already_enum(self):
        """Test passing enum instances directly."""
        assert normalize_enum_value(ImageQuality.HIGH, ImageQuality) == ImageQuality.HIGH
        assert normalize_enum_value(ImageSize.SQUARE, ImageSize) == ImageSize.SQUARE
    
    def test_normalize_enum_value_special_cases(self):
        """Test special case handling."""
        # Size aliases
        assert normalize_enum_value("square", ImageSize) == ImageSize.SQUARE
        assert normalize_enum_value("landscape", ImageSize) == ImageSize.LANDSCAPE
        assert normalize_enum_value("portrait", ImageSize) == ImageSize.PORTRAIT
        
        # Numeric inputs should fallback to default
        default_quality = ImageQuality.AUTO
        assert normalize_enum_value(123, ImageQuality, default_quality) == default_quality
        assert normalize_enum_value(3.14, ImageStyle, ImageStyle.VIVID) == ImageStyle.VIVID


class TestSpecificValidators:
    """Test specific validation functions."""
    
    def test_validate_image_quality(self):
        """Test image quality validation."""
        assert validate_image_quality("high") == ImageQuality.HIGH
        assert validate_image_quality("MEDIUM") == ImageQuality.MEDIUM
        assert validate_image_quality("auto") == ImageQuality.AUTO
        assert validate_image_quality("low") == ImageQuality.LOW
        assert validate_image_quality("invalid") == ImageQuality.AUTO  # Default fallback
        assert validate_image_quality(None) == ImageQuality.AUTO
        assert validate_image_quality(ImageQuality.HIGH) == ImageQuality.HIGH
    
    def test_validate_image_size(self):
        """Test image size validation."""
        assert validate_image_size("1024x1024") == ImageSize.SQUARE
        assert validate_image_size("1536x1024") == ImageSize.LANDSCAPE
        assert validate_image_size("1024x1536") == ImageSize.PORTRAIT
        assert validate_image_size("square") == ImageSize.SQUARE
        assert validate_image_size("landscape") == ImageSize.LANDSCAPE
        assert validate_image_size("portrait") == ImageSize.PORTRAIT
        assert validate_image_size("invalid") == ImageSize.LANDSCAPE  # Default fallback
        assert validate_image_size(None) == ImageSize.LANDSCAPE
    
    def test_validate_image_style(self):
        """Test image style validation."""
        assert validate_image_style("vivid") == ImageStyle.VIVID
        assert validate_image_style("natural") == ImageStyle.NATURAL
        assert validate_image_style("VIVID") == ImageStyle.VIVID
        assert validate_image_style("invalid") == ImageStyle.VIVID  # Default fallback
        assert validate_image_style(None) == ImageStyle.VIVID
    
    def test_validate_moderation_level(self):
        """Test moderation level validation."""
        assert validate_moderation_level("auto") == ModerationLevel.AUTO
        assert validate_moderation_level("low") == ModerationLevel.LOW
        assert validate_moderation_level("AUTO") == ModerationLevel.AUTO
        assert validate_moderation_level("invalid") == ModerationLevel.AUTO  # Default fallback
        assert validate_moderation_level(None) == ModerationLevel.AUTO
    
    def test_validate_output_format(self):
        """Test output format validation."""
        assert validate_output_format("png") == OutputFormat.PNG
        assert validate_output_format("jpeg") == OutputFormat.JPEG
        assert validate_output_format("webp") == OutputFormat.WEBP
        assert validate_output_format("PNG") == OutputFormat.PNG
        assert validate_output_format("invalid") == OutputFormat.PNG  # Default fallback
        assert validate_output_format(None) == OutputFormat.PNG
    
    def test_validate_background_type(self):
        """Test background type validation."""
        assert validate_background_type("auto") == BackgroundType.AUTO
        assert validate_background_type("transparent") == BackgroundType.TRANSPARENT
        assert validate_background_type("white") == BackgroundType.WHITE
        assert validate_background_type("black") == BackgroundType.BLACK
        assert validate_background_type("AUTO") == BackgroundType.AUTO
        assert validate_background_type("invalid") == BackgroundType.AUTO  # Default fallback
        assert validate_background_type(None) == BackgroundType.AUTO
    
    def test_validate_compression(self):
        """Test compression validation."""
        assert validate_compression(50) == 50
        assert validate_compression(0) == 0
        assert validate_compression(100) == 100
        assert validate_compression(150) == 100  # Clamped to max
        assert validate_compression(-10) == 0  # Clamped to min
        assert validate_compression("50") == 50  # String conversion
        assert validate_compression("75") == 75
        assert validate_compression("invalid") == 100  # Default fallback
        assert validate_compression(None) == 100
        assert validate_compression(3.14) == 3  # Float to int conversion
    
    def test_validate_limit(self):
        """Test limit validation."""
        assert validate_limit(10, 100) == 10
        assert validate_limit(0, 100) == 1  # Minimum enforced
        assert validate_limit(150, 100) == 100  # Maximum enforced
        assert validate_limit("50", 100) == 50  # String conversion
        assert validate_limit("invalid", 100) == 10  # Default fallback
        assert validate_limit(None, 100) == 10
        assert validate_limit(-5, 50) == 1  # Negative clamped to minimum
    
    def test_validate_days(self):
        """Test days validation."""
        assert validate_days(7, 365) == 7
        assert validate_days(0, 365) == 1  # Minimum enforced
        assert validate_days(400, 365) == 365  # Maximum enforced
        assert validate_days("30", 365) == 30  # String conversion
        assert validate_days("invalid", 365) == 7  # Default fallback
        assert validate_days(None, 365) == 7
        assert validate_days(-5, 100) == 1  # Negative clamped to minimum


class TestPromptSanitization:
    """Test prompt sanitization functionality."""
    
    def test_sanitize_prompt_basic(self):
        """Test basic prompt sanitization."""
        assert sanitize_prompt("valid prompt") == "valid prompt"
        assert sanitize_prompt("  test prompt  ") == "test prompt"
        assert sanitize_prompt("\tprompt\n") == "prompt"
    
    def test_sanitize_prompt_length_limit(self):
        """Test prompt length limiting."""
        long_prompt = "x" * 5000
        sanitized = sanitize_prompt(long_prompt)
        assert len(sanitized) == 4000
        assert sanitized == "x" * 4000
        
        normal_prompt = "normal length prompt"
        assert sanitize_prompt(normal_prompt) == normal_prompt
    
    def test_sanitize_prompt_invalid_inputs(self):
        """Test sanitization with invalid inputs."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            sanitize_prompt(None)
        
        with pytest.raises(ValueError, match="must be a non-empty string"):
            sanitize_prompt("")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_prompt("   ")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_prompt("\t\n  ")
        
        with pytest.raises(ValueError, match="must be a non-empty string"):
            sanitize_prompt(123)
    
    def test_sanitize_prompt_unicode(self):
        """Test prompt sanitization with unicode characters."""
        unicode_prompt = "A 🌟 beautiful sunset over 山 mountains"
        sanitized = sanitize_prompt(unicode_prompt)
        assert sanitized == unicode_prompt  # Should preserve unicode
        
        # Test with various unicode whitespace
        prompt_with_unicode_space = "test\u2000prompt\u2001here"
        sanitized = sanitize_prompt(prompt_with_unicode_space)
        assert sanitized.strip() == "test\u2000prompt\u2001here"


class TestBase64ImageValidation:
    """Test base64 image validation functionality."""
    
    def test_validate_base64_image_data_url(self):
        """Test validation of data URL format."""
        # Valid data URL
        valid_data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        result = validate_base64_image(valid_data_url)
        assert result == valid_data_url
        
        # Valid JPEG data URL
        valid_jpeg_url = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/gA=="
        result = validate_base64_image(valid_jpeg_url)
        assert result == valid_jpeg_url
    
    def test_validate_base64_image_raw_base64(self):
        """Test validation of raw base64 strings."""
        # Valid base64 string (will be converted to data URL)
        raw_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        result = validate_base64_image(raw_base64)
        assert result.startswith("data:image/png;base64,")
        assert raw_base64 in result
    
    def test_validate_base64_image_invalid_inputs(self):
        """Test validation with invalid inputs."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            validate_base64_image(None)
        
        with pytest.raises(ValueError, match="must be a non-empty string"):
            validate_base64_image("")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_base64_image("   ")
        
        with pytest.raises(ValueError, match="Invalid base64"):
            validate_base64_image("invalid-base64!")
        
        with pytest.raises(ValueError, match="Invalid data URL"):
            validate_base64_image("data:invalid-format")
    
    def test_validate_base64_image_malformed_data_url(self):
        """Test validation with malformed data URLs."""
        with pytest.raises(ValueError, match="Invalid data URL"):
            validate_base64_image("data:image/png")  # Missing base64 part
        
        with pytest.raises(ValueError, match="Invalid data URL"):
            validate_base64_image("data:text/plain;base64,dGVzdA==")  # Not image
        
        with pytest.raises(ValueError, match="Invalid base64"):
            validate_base64_image("data:image/png;base64,invalid!")


class TestMemoryCache:
    """Test memory cache implementation."""
    
    def test_memory_cache_creation(self):
        """Test memory cache creation with default settings."""
        cache = MemoryCache()
        assert cache.max_size_bytes > 0
        assert cache.current_size == 0
        assert len(cache.cache) == 0
        assert cache.default_ttl > 0
    
    def test_memory_cache_custom_settings(self):
        """Test memory cache with custom settings."""
        cache = MemoryCache(
            max_size_mb=100,
            default_ttl=3600
        )
        assert cache.max_size_bytes == 100 * 1024 * 1024
        assert cache.default_ttl == 3600
    
    def test_memory_cache_set_get(self):
        """Test basic cache set and get operations."""
        cache = MemoryCache()
        
        # Set a value
        result = cache.set("test_key", "test_value")
        assert result is True
        
        # Get the value
        value = cache.get("test_key")
        assert value == "test_value"
        
        # Get non-existent key
        value = cache.get("non_existent")
        assert value is None
    
    def test_memory_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = MemoryCache(default_ttl=0.1)  # 0.1 second TTL
        
        cache.set("test_key", "test_value")
        
        # Should be available immediately
        assert cache.get("test_key") == "test_value"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired now
        assert cache.get("test_key") is None
    
    def test_memory_cache_custom_ttl(self):
        """Test cache with custom TTL per item."""
        cache = MemoryCache(default_ttl=3600)  # Long default TTL
        
        # Set with short custom TTL
        cache.set("short_ttl_key", "value", ttl=0.1)
        cache.set("long_ttl_key", "value")  # Uses default TTL
        
        # Both should be available immediately
        assert cache.get("short_ttl_key") == "value"
        assert cache.get("long_ttl_key") == "value"
        
        # Wait for short TTL to expire
        time.sleep(0.2)
        
        # Short TTL should be expired, long TTL should remain
        assert cache.get("short_ttl_key") is None
        assert cache.get("long_ttl_key") == "value"
    
    def test_memory_cache_stats(self):
        """Test cache statistics."""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "longer_value_2")
        
        stats = cache.stats()
        assert stats["entries"] == 2
        assert stats["size_mb"] >= 0  # Should be non-negative
        assert stats["utilization"] >= 0  # Should be non-negative
        assert 0 <= stats["utilization"] <= 1  # Should be percentage
    
    def test_memory_cache_size_estimation(self):
        """Test cache size estimation."""
        cache = MemoryCache(max_size_mb=1)  # Small cache for testing
        
        # Add some data
        large_value = "x" * 1000  # 1KB string
        cache.set("large_key", large_value)
        
        stats = cache.stats()
        assert stats["size_mb"] > 0
        assert cache.current_size > 0
    
    def test_memory_cache_clear(self):
        """Test cache clearing."""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert len(cache.cache) == 2
        
        cache.clear()
        
        assert len(cache.cache) == 0
        assert cache.current_size == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_memory_cache_delete(self):
        """Test cache item deletion."""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert cache.get("key1") == "value1"
        
        success = cache.delete("key1")
        assert success is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"  # Other key should remain
        
        # Delete non-existent key
        success = cache.delete("non_existent")
        assert success is False


class TestCacheManager:
    """Test cache manager functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_manager_enabled(self, mock_cache_settings):
        """Test cache manager when enabled."""
        mock_cache_settings.enabled = True
        cache_manager = CacheManager(mock_cache_settings)
        
        assert cache_manager.enabled is True
        assert cache_manager.cache is not None
        
        await cache_manager.initialize()
        await cache_manager.close()
    
    @pytest.mark.asyncio
    async def test_cache_manager_disabled(self, mock_cache_settings):
        """Test cache manager when disabled."""
        mock_cache_settings.enabled = False
        cache_manager = CacheManager(mock_cache_settings)
        
        assert cache_manager.enabled is False
        assert cache_manager.cache is None
        
        # Should return None for all operations
        result = await cache_manager.get_image_generation(prompt="test")
        assert result is None
        
        success = await cache_manager.set_image_generation({}, prompt="test")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cache_manager_image_generation(self, mock_cache_settings):
        """Test cache manager image generation caching."""
        mock_cache_settings.enabled = True
        cache_manager = CacheManager(mock_cache_settings)
        await cache_manager.initialize()
        
        try:
            # Test setting and getting image generation result
            test_result = {"image_id": "test123", "image_url": "data:..."}
            prompt = "a beautiful sunset"
            
            success = await cache_manager.set_image_generation(
                test_result, 
                prompt=prompt,
                quality="high",
                size="1024x1024",
                style="vivid"
            )
            assert success is True
            
            cached_result = await cache_manager.get_image_generation(
                prompt=prompt,
                quality="high",
                size="1024x1024",
                style="vivid"
            )
            assert cached_result == test_result
            
        finally:
            await cache_manager.close()
    
    @pytest.mark.asyncio
    async def test_cache_manager_generation_key_creation(self, mock_cache_settings):
        """Test cache key creation for image generation."""
        mock_cache_settings.enabled = True
        cache_manager = CacheManager(mock_cache_settings)
        await cache_manager.initialize()
        
        try:
            # Different parameters should create different cache keys
            test_result1 = {"image_id": "test1"}
            test_result2 = {"image_id": "test2"}
            
            await cache_manager.set_image_generation(test_result1, prompt="sunset", quality="high")
            await cache_manager.set_image_generation(test_result2, prompt="sunset", quality="low")
            
            # Should get different results based on quality
            cached1 = await cache_manager.get_image_generation(prompt="sunset", quality="high")
            cached2 = await cache_manager.get_image_generation(prompt="sunset", quality="low")
            
            assert cached1 != cached2
            assert cached1["image_id"] == "test1"
            assert cached2["image_id"] == "test2"
            
        finally:
            await cache_manager.close()


class TestOpenAIClientManager:
    """Test OpenAI client manager functionality."""
    
    def test_openai_client_manager_creation(self, mock_openai_settings):
        """Test OpenAI client manager creation."""
        manager = OpenAIClientManager(mock_openai_settings)
        
        assert manager.settings == mock_openai_settings
        # Client should be created lazily
        assert hasattr(manager, '_client')
    
    @patch('gpt_image_mcp.utils.openai_client.OpenAI')
    def test_openai_client_creation(self, mock_openai_class, mock_openai_settings):
        """Test OpenAI client creation with proper settings."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        manager = OpenAIClientManager(mock_openai_settings)
        client = manager.client  # Access client property
        
        # Verify OpenAI client was created with correct parameters
        mock_openai_class.assert_called_once_with(
            api_key=mock_openai_settings.api_key,
            base_url=mock_openai_settings.base_url,
            organization=mock_openai_settings.organization,
            max_retries=mock_openai_settings.max_retries,
            timeout=mock_openai_settings.timeout
        )
        
        assert client == mock_client
    
    @patch('gpt_image_mcp.utils.openai_client.OpenAI')
    def test_openai_client_singleton(self, mock_openai_class, mock_openai_settings):
        """Test that client is created only once (singleton pattern)."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        manager = OpenAIClientManager(mock_openai_settings)
        
        # Access client multiple times
        client1 = manager.client
        client2 = manager.client
        
        # Should only create client once
        assert mock_openai_class.call_count == 1
        assert client1 is client2
    
    def test_openai_client_manager_settings_validation(self):
        """Test that invalid settings raise appropriate errors."""
        from gpt_image_mcp.config.settings import OpenAISettings
        
        # Missing API key should raise validation error during settings creation
        with pytest.raises(Exception):  # Pydantic ValidationError
            invalid_settings = OpenAISettings()
            OpenAIClientManager(invalid_settings)
    
    @patch('gpt_image_mcp.utils.openai_client.OpenAI')
    def test_openai_client_with_organization(self, mock_openai_class, mock_openai_settings):
        """Test OpenAI client creation with organization."""
        mock_openai_settings.organization = "org-test123"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        manager = OpenAIClientManager(mock_openai_settings)
        client = manager.client
        
        # Verify organization was passed
        mock_openai_class.assert_called_once_with(
            api_key=mock_openai_settings.api_key,
            base_url=mock_openai_settings.base_url,
            organization="org-test123",
            max_retries=mock_openai_settings.max_retries,
            timeout=mock_openai_settings.timeout
        )
    
    @patch('gpt_image_mcp.utils.openai_client.OpenAI')
    def test_openai_client_custom_settings(self, mock_openai_class, mock_openai_settings):
        """Test OpenAI client creation with custom settings."""
        mock_openai_settings.base_url = "https://custom.api.com/v1"
        mock_openai_settings.max_retries = 5
        mock_openai_settings.timeout = 300.0
        
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        manager = OpenAIClientManager(mock_openai_settings)
        client = manager.client
        
        # Verify custom settings were used
        mock_openai_class.assert_called_once_with(
            api_key=mock_openai_settings.api_key,
            base_url="https://custom.api.com/v1",
            organization=mock_openai_settings.organization,
            max_retries=5,
            timeout=300.0
        )