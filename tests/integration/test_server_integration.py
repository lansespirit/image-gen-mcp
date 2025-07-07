"""Integration tests for the MCP server and resource management."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest
import pytest_asyncio

from gpt_image_mcp.resources.image_resources import ImageResourceManager
from gpt_image_mcp.resources.model_registry import ModelRegistry, model_registry
from gpt_image_mcp.resources.prompt_templates import PromptTemplateResourceManager


class TestImageResourceManager:
    """Test image resource manager functionality."""
    
    @pytest.fixture
    def resource_manager(self, storage_manager, mock_storage_settings):
        """Create image resource manager for testing."""
        return ImageResourceManager(
            storage_manager=storage_manager,
            settings=mock_storage_settings
        )
    
    @pytest.mark.asyncio
    async def test_get_image_resource(self, resource_manager, storage_manager, sample_image_bytes):
        """Test retrieving image resource by ID."""
        image_id = "test_resource_123"
        metadata = {"prompt": "resource test"}
        
        # Store an image first
        await storage_manager.store_image(image_id, sample_image_bytes, metadata)
        
        # Get resource
        result = await resource_manager.get_image_resource(image_id)
        
        # Should return data URL
        assert result.startswith("data:image/")
        assert "base64," in result
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_image_resource(self, resource_manager):
        """Test retrieving non-existent image resource."""
        with pytest.raises(ValueError, match="Image not found"):
            await resource_manager.get_image_resource("nonexistent_123")
    
    @pytest.mark.asyncio
    async def test_get_recent_images(self, resource_manager, storage_manager, sample_image_bytes):
        """Test getting recent images resource."""
        # Store some test images
        for i in range(5):
            await storage_manager.store_image(
                f"recent_test_{i}",
                sample_image_bytes,
                {"prompt": f"recent test {i}"}
            )
        
        # Get recent images
        result = await resource_manager.get_recent_images(limit=3, days=7)
        
        # Should return JSON string
        data = json.loads(result)
        
        assert "images" in data
        assert "total" in data
        assert "limit" in data
        assert "days" in data
        
        # Should respect limit
        assert len(data["images"]) <= 3
        assert data["limit"] == 3
        assert data["days"] == 7
        
        # Each image should have required fields
        for image in data["images"]:
            assert "image_id" in image
            assert "created_at" in image
            assert "prompt" in image
            assert "resource_uri" in image
    
    @pytest.mark.asyncio
    async def test_get_recent_images_empty(self, resource_manager):
        """Test getting recent images when none exist."""
        result = await resource_manager.get_recent_images(limit=10, days=7)
        
        data = json.loads(result)
        assert data["images"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_storage_stats(self, resource_manager, storage_manager, sample_image_bytes):
        """Test getting storage statistics resource."""
        # Store some test data
        await storage_manager.store_image("stats_test", sample_image_bytes, {"prompt": "stats"})
        
        # Get storage stats
        result = await resource_manager.get_storage_stats()
        
        # Should return JSON string
        data = json.loads(result)
        
        # Should contain expected fields
        assert "total_images" in data
        assert "storage_usage_mb" in data
        assert "retention_policy_days" in data
        assert "last_cleanup" in data
        
        # Values should be reasonable
        assert isinstance(data["total_images"], int)
        assert data["total_images"] >= 1
        assert isinstance(data["storage_usage_mb"], (int, float))
        assert data["storage_usage_mb"] >= 0


class TestModelRegistry:
    """Test model registry functionality."""
    
    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing available models."""
        models = await model_registry.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-image-1" in models
    
    @pytest.mark.asyncio
    async def test_get_model_info(self):
        """Test getting model information."""
        model_info = await model_registry.get_model_info("gpt-image-1")
        
        assert model_info is not None
        assert model_info.model_id == "gpt-image-1"
        assert model_info.name
        assert model_info.version
        assert model_info.capabilities
        assert isinstance(model_info.capabilities, list)
    
    @pytest.mark.asyncio
    async def test_get_model_info_nonexistent(self):
        """Test getting info for non-existent model."""
        model_info = await model_registry.get_model_info("nonexistent-model")
        assert model_info is None
    
    @pytest.mark.asyncio
    async def test_get_model_documentation(self):
        """Test getting model documentation."""
        doc = await model_registry.get_model_documentation("gpt-image-1")
        
        assert isinstance(doc, str)
        assert len(doc) > 0
        assert "gpt-image-1" in doc.lower()
        
        # Should contain markdown formatting
        assert "#" in doc  # Headers
        assert "##" in doc or "###" in doc  # Subheaders
    
    @pytest.mark.asyncio
    async def test_get_model_documentation_with_examples(self):
        """Test that model documentation includes usage examples."""
        doc = await model_registry.get_model_documentation("gpt-image-1")
        
        # Should contain example usage
        assert "example" in doc.lower() or "usage" in doc.lower()
        
        # Should contain pricing information
        assert "price" in doc.lower() or "cost" in doc.lower() or "pricing" in doc.lower()
        
        # Should contain rate limit information
        assert "rate" in doc.lower() or "limit" in doc.lower()


class TestPromptTemplateResourceManager:
    """Test prompt template resource manager."""
    
    def test_list_templates(self):
        """Test listing available prompt templates."""
        manager = PromptTemplateResourceManager()
        result = manager.list_templates()
        
        # Should return dict with templates
        assert isinstance(result, dict)
        assert "templates" in result
        assert "categories" in result
        assert "total" in result
        
        # Should have some templates
        assert len(result["templates"]) > 0
        assert result["total"] > 0
        
        # Each template should have required fields
        for template in result["templates"]:
            assert "name" in template
            assert "title" in template
            assert "description" in template
            assert "category" in template
            assert "parameters" in template
    
    def test_get_template_details(self):
        """Test getting template details."""
        manager = PromptTemplateResourceManager()
        
        # First get list to find a valid template
        templates = manager.list_templates()
        template_name = templates["templates"][0]["name"]
        
        # Get details for that template
        details = manager.get_template_details(template_name)
        
        assert details is not None
        assert "name" in details
        assert "title" in details
        assert "description" in details
        assert "parameters" in details
        assert "examples" in details
        assert "usage" in details
        
        # Parameters should be properly formatted
        for param_name, param_info in details["parameters"].items():
            assert "type" in param_info
            assert "description" in param_info
            assert "required" in param_info
    
    def test_get_template_details_nonexistent(self):
        """Test getting details for non-existent template."""
        manager = PromptTemplateResourceManager()
        
        details = manager.get_template_details("nonexistent_template")
        assert details is None
    
    def test_get_template_not_found_response(self):
        """Test getting helpful error response for missing template."""
        manager = PromptTemplateResourceManager()
        
        response = manager.get_template_not_found_response("missing_template")
        
        assert "error" in response
        assert "suggestions" in response
        assert response["error"] == "Template not found"
        assert isinstance(response["suggestions"], list)
    
    def test_template_categories(self):
        """Test that templates are properly categorized."""
        manager = PromptTemplateResourceManager()
        result = manager.list_templates()
        
        categories = result["categories"]
        assert isinstance(categories, dict)
        
        # Should have reasonable categories
        assert len(categories) > 0
        
        # Each category should have templates
        for category, template_list in categories.items():
            assert isinstance(template_list, list)
            assert len(template_list) > 0
    
    def test_template_parameter_validation(self):
        """Test template parameter definitions are valid."""
        manager = PromptTemplateResourceManager()
        templates = manager.list_templates()
        
        for template in templates["templates"]:
            template_name = template["name"]
            details = manager.get_template_details(template_name)
            
            # All parameters should have proper type definitions
            for param_name, param_info in details["parameters"].items():
                assert param_info["type"] in ["string", "boolean", "integer", "number"]
                assert isinstance(param_info["required"], bool)
                assert isinstance(param_info["description"], str)
                assert len(param_info["description"]) > 0


class TestServerIntegration:
    """Test complete server integration functionality."""
    
    @pytest.mark.asyncio
    async def test_server_context_creation(self, mock_settings):
        """Test server context creation with all components."""
        from gpt_image_mcp.server import ServerContext
        from gpt_image_mcp.storage.manager import ImageStorageManager
        from gpt_image_mcp.utils.cache import CacheManager
        from gpt_image_mcp.utils.openai_client import OpenAIClientManager
        from gpt_image_mcp.tools.image_generation import ImageGenerationTool
        from gpt_image_mcp.tools.image_editing import ImageEditingTool
        from gpt_image_mcp.resources.image_resources import ImageResourceManager
        
        # Create all components
        storage_manager = ImageStorageManager(mock_settings.storage)
        await storage_manager.initialize()
        
        try:
            cache_manager = CacheManager(mock_settings.cache)
            await cache_manager.initialize()
            
            try:
                openai_client = OpenAIClientManager(mock_settings.openai)
                
                generation_tool = ImageGenerationTool(
                    openai_client=openai_client,
                    storage_manager=storage_manager,
                    cache_manager=cache_manager,
                    settings=mock_settings.images
                )
                
                editing_tool = ImageEditingTool(
                    openai_client=openai_client,
                    storage_manager=storage_manager,
                    cache_manager=cache_manager,
                    settings=mock_settings.images
                )
                
                resource_manager = ImageResourceManager(
                    storage_manager=storage_manager,
                    settings=mock_settings.storage
                )
                
                # Create server context
                context = ServerContext(
                    settings=mock_settings,
                    storage_manager=storage_manager,
                    openai_client=openai_client,
                    cache_manager=cache_manager,
                    image_generation_tool=generation_tool,
                    image_editing_tool=editing_tool,
                    resource_manager=resource_manager
                )
                
                # Verify all components are properly initialized
                assert context.settings == mock_settings
                assert context.storage_manager == storage_manager
                assert context.openai_client == openai_client
                assert context.cache_manager == cache_manager
                assert context.image_generation_tool == generation_tool
                assert context.image_editing_tool == editing_tool
                assert context.resource_manager == resource_manager
                
            finally:
                await cache_manager.close()
        finally:
            await storage_manager.close()
    
    @patch('gpt_image_mcp.server.mcp')
    @pytest.mark.asyncio
    async def test_server_tool_integration(self, mock_mcp, mock_settings, sample_image_data):
        """Test server tool integration with MCP context."""
        from gpt_image_mcp.server import generate_image, edit_image, get_server_context
        
        # Mock MCP context
        mock_context = MagicMock()
        mock_server_context = MagicMock()
        
        # Mock tools
        mock_generation_tool = AsyncMock()
        mock_editing_tool = AsyncMock()
        
        mock_server_context.image_generation_tool = mock_generation_tool
        mock_server_context.image_editing_tool = mock_editing_tool
        
        mock_context.request_context.lifespan_context = mock_server_context
        mock_mcp.get_context.return_value = mock_context
        
        # Mock tool responses
        generation_result = {
            "task_id": "test_task",
            "image_id": "test_img",
            "image_url": "data:image/png;base64,test",
            "metadata": {"prompt": "test"}
        }
        
        edit_result = {
            "task_id": "edit_task",
            "image_id": "edit_img",
            "image_url": "data:image/png;base64,edited",
            "operation": "edit",
            "metadata": {"prompt": "edit test"}
        }
        
        mock_generation_tool.generate.return_value = generation_result
        mock_editing_tool.edit.return_value = edit_result
        
        # Test image generation
        result = await generate_image(
            prompt="test image",
            quality="high",
            size="1024x1024",
            style="vivid"
        )
        
        assert result == generation_result
        mock_generation_tool.generate.assert_called_once()
        
        # Test image editing
        result = await edit_image(
            image_data=sample_image_data,
            prompt="edit test",
            size="1024x1024",
            quality="high"
        )
        
        assert result == edit_result
        mock_editing_tool.edit.assert_called_once()
    
    @patch('gpt_image_mcp.server.mcp')
    @pytest.mark.asyncio
    async def test_server_resource_integration(self, mock_mcp, mock_settings):
        """Test server resource integration."""
        from gpt_image_mcp.server import (
            get_generated_image,
            get_recent_images,
            get_storage_stats,
            get_model_info,
            list_models
        )
        
        # Mock MCP context
        mock_context = MagicMock()
        mock_server_context = MagicMock()
        mock_resource_manager = AsyncMock()
        
        mock_server_context.resource_manager = mock_resource_manager
        mock_context.request_context.lifespan_context = mock_server_context
        mock_mcp.get_context.return_value = mock_context
        
        # Mock resource responses
        mock_resource_manager.get_image_resource.return_value = "data:image/png;base64,test"
        mock_resource_manager.get_recent_images.return_value = '{"images": []}'
        mock_resource_manager.get_storage_stats.return_value = '{"total_images": 0}'
        
        # Test image resource
        result = await get_generated_image(image_id="test_123")
        assert result == "data:image/png;base64,test"
        mock_resource_manager.get_image_resource.assert_called_with("test_123")
        
        # Test recent images
        result = await get_recent_images(limit=10, days=7)
        assert result == '{"images": []}'
        mock_resource_manager.get_recent_images.assert_called_with(limit=10, days=7)
        
        # Test storage stats
        result = await get_storage_stats()
        assert result == '{"total_images": 0}'
        mock_resource_manager.get_storage_stats.assert_called_once()
        
        # Test model info (no mock needed as it uses global registry)
        result = await get_model_info(model_id="gpt-image-1")
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Test list models
        result = await list_models()
        assert isinstance(result, str)
        data = json.loads(result)
        assert "models" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, mock_settings, sample_image_bytes):
        """Test complete end-to-end workflow."""
        from gpt_image_mcp.storage.manager import ImageStorageManager
        from gpt_image_mcp.utils.cache import CacheManager
        from gpt_image_mcp.utils.openai_client import OpenAIClientManager
        from gpt_image_mcp.tools.image_generation import ImageGenerationTool
        from gpt_image_mcp.resources.image_resources import ImageResourceManager
        
        # Initialize all components
        storage_manager = ImageStorageManager(mock_settings.storage)
        await storage_manager.initialize()
        
        try:
            cache_manager = CacheManager(mock_settings.cache)
            await cache_manager.initialize()
            
            try:
                # Mock OpenAI client for this test
                with patch('gpt_image_mcp.utils.openai_client.OpenAI') as mock_openai_class:
                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.data = [MagicMock()]
                    mock_response.data[0].b64_json = base64.b64encode(sample_image_bytes).decode()
                    mock_response.data[0].revised_prompt = "End-to-end test image"
                    mock_client.images.generate = AsyncMock(return_value=mock_response)
                    mock_openai_class.return_value = mock_client
                    
                    openai_client = OpenAIClientManager(mock_settings.openai)
                    
                    generation_tool = ImageGenerationTool(
                        openai_client=openai_client,
                        storage_manager=storage_manager,
                        cache_manager=cache_manager,
                        settings=mock_settings.images
                    )
                    
                    resource_manager = ImageResourceManager(
                        storage_manager=storage_manager,
                        settings=mock_settings.storage
                    )
                    
                    # Generate an image
                    generation_result = await generation_tool.generate(
                        prompt="end-to-end test"
                    )
                    
                    assert "image_id" in generation_result
                    image_id = generation_result["image_id"]
                    
                    # Retrieve the image through resource manager
                    image_data_url = await resource_manager.get_image_resource(image_id)
                    assert image_data_url.startswith("data:image/")
                    
                    # Check that it appears in recent images
                    recent_images_json = await resource_manager.get_recent_images(limit=10, days=1)
                    recent_images = json.loads(recent_images_json)
                    
                    found_image = None
                    for img in recent_images["images"]:
                        if img["image_id"] == image_id:
                            found_image = img
                            break
                    
                    assert found_image is not None
                    assert found_image["prompt"] == "end-to-end test"
                    
                    # Check storage stats
                    stats_json = await resource_manager.get_storage_stats()
                    stats = json.loads(stats_json)
                    
                    assert stats["total_images"] >= 1
                    assert stats["storage_usage_mb"] > 0
                    
            finally:
                await cache_manager.close()
        finally:
            await storage_manager.close()