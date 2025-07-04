"""Basic tests for the GPT Image MCP Server."""

import pytest
from unittest.mock import Mock, AsyncMock
from gpt_image_mcp.config.settings import Settings, OpenAISettings, ImageSettings
from gpt_image_mcp.storage.manager import ImageStorageManager
from gpt_image_mcp.utils.cache import CacheManager, MemoryCache


class TestSettings:
    """Test configuration settings."""
    
    def test_settings_creation(self):
        """Test that settings can be created with defaults."""
        settings = Settings()
        assert settings.server.name == "GPT Image MCP Server"
        assert settings.images.default_model == "gpt-image-1"
        assert settings.storage.retention_days == 30
    
    def test_openai_settings(self):
        """Test OpenAI settings validation."""
        openai_settings = OpenAISettings(api_key="test-key")
        assert openai_settings.api_key == "test-key"
        assert openai_settings.base_url == "https://api.openai.com/v1"


class TestMemoryCache:
    """Test memory cache functionality."""
    
    def test_cache_creation(self):
        """Test cache creation with defaults."""
        cache = MemoryCache()
        assert cache.max_size_bytes > 0
        assert cache.current_size == 0
        assert len(cache.cache) == 0
    
    def test_cache_set_get(self):
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
    
    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = MemoryCache(default_ttl=0)  # Immediate expiration
        
        cache.set("test_key", "test_value", ttl=0)
        
        # Should be expired immediately
        import time
        time.sleep(0.1)
        value = cache.get("test_key")
        assert value is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        stats = cache.stats()
        assert stats["entries"] == 2
        assert stats["size_mb"] > 0
        assert stats["utilization"] > 0


@pytest.mark.asyncio
class TestCacheManager:
    """Test cache manager functionality."""
    
    async def test_cache_manager_creation(self):
        """Test cache manager creation."""
        from gpt_image_mcp.config.settings import CacheSettings
        
        settings = CacheSettings(enabled=True, backend="memory")
        cache_manager = CacheManager(settings)
        
        assert cache_manager.enabled is True
        assert cache_manager.cache is not None
        
        await cache_manager.initialize()
        await cache_manager.close()
    
    async def test_disabled_cache_manager(self):
        """Test cache manager when disabled."""
        from gpt_image_mcp.config.settings import CacheSettings
        
        settings = CacheSettings(enabled=False)
        cache_manager = CacheManager(settings)
        
        assert cache_manager.enabled is False
        assert cache_manager.cache is None
        
        # Should return None for all operations
        result = await cache_manager.get_image_generation(prompt="test")
        assert result is None
        
        success = await cache_manager.set_image_generation({}, prompt="test")
        assert success is False


@pytest.mark.asyncio 
class TestImageStorageManager:
    """Test image storage manager."""
    
    async def test_storage_manager_creation(self):
        """Test storage manager creation."""
        from gpt_image_mcp.config.settings import StorageSettings
        
        settings = StorageSettings(base_path="./test_storage")
        storage_manager = ImageStorageManager(settings)
        
        await storage_manager.initialize()
        assert storage_manager.base_path.exists()
        
        await storage_manager.close()
    
    def test_image_id_generation(self):
        """Test unique image ID generation."""
        from gpt_image_mcp.config.settings import StorageSettings
        
        settings = StorageSettings()
        storage_manager = ImageStorageManager(settings)
        
        id1 = storage_manager.generate_image_id()
        id2 = storage_manager.generate_image_id()
        
        assert id1 != id2
        assert id1.startswith("img_")
        assert id2.startswith("img_")
        assert len(id1) > 20  # Should be reasonably long
    
    async def test_storage_stats(self):
        """Test storage statistics."""
        from gpt_image_mcp.config.settings import StorageSettings
        
        settings = StorageSettings(base_path="./test_storage")
        storage_manager = ImageStorageManager(settings)
        
        await storage_manager.initialize()
        stats = await storage_manager.get_storage_stats()
        
        assert "total_images" in stats
        assert "storage_usage_mb" in stats
        assert "retention_policy_days" in stats
        
        await storage_manager.close()


class TestPromptTemplates:
    """Test prompt template functionality."""
    
    def test_template_manager_creation(self):
        """Test template manager creation."""
        from gpt_image_mcp.prompts.templates import PromptTemplateManager
        
        manager = PromptTemplateManager()
        assert len(manager.templates) > 0
        
        templates = manager.list_templates()
        assert len(templates) > 0
        assert all("name" in template for template in templates)
    
    def test_template_rendering(self):
        """Test template rendering with arguments."""
        from gpt_image_mcp.prompts.templates import PromptTemplateManager
        
        manager = PromptTemplateManager()
        
        # Test creative image template
        result = manager.render_template(
            "creative_image",
            subject="a dragon",
            style="oil painting",
            mood="dramatic",
            color_palette="warm reds and golds"
        )
        
        assert result is not None
        prompt, metadata = result
        assert "dragon" in prompt
        assert "oil painting" in prompt
        assert "dramatic" in prompt
        assert "recommended_size" in metadata
    
    def test_template_validation(self):
        """Test template argument validation."""
        from gpt_image_mcp.prompts.templates import PromptTemplateManager
        
        manager = PromptTemplateManager()
        
        # Should raise error for missing required argument
        with pytest.raises(ValueError):
            manager.render_template("creative_image")  # Missing required 'subject'
    
    def test_template_suggestions(self):
        """Test template suggestions based on use case."""
        from gpt_image_mcp.prompts.templates import PromptTemplateManager
        
        manager = PromptTemplateManager()
        
        suggestions = manager.get_template_suggestions("social media post")
        assert "social_media" in suggestions
        
        suggestions = manager.get_template_suggestions("blog header")
        assert "blog_header" in suggestions
        
        suggestions = manager.get_template_suggestions("product photography")
        assert "product_photography" in suggestions


if __name__ == "__main__":
    pytest.main([__file__])