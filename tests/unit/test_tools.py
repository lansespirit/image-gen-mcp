"""Unit tests for image generation and editing tools."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

import pytest
import pytest_asyncio

from gpt_image_mcp.tools.image_generation import ImageGenerationTool
from gpt_image_mcp.tools.image_editing import ImageEditingTool
from gpt_image_mcp.types.enums import ImageQuality, ImageSize, ImageStyle, OutputFormat, BackgroundType


class TestImageGenerationTool:
    """Test image generation tool functionality."""
    
    @pytest.fixture
    def generation_tool(self, mock_openai_client_manager, storage_manager, cache_manager, mock_image_settings):
        """Create image generation tool for testing."""
        return ImageGenerationTool(
            openai_client=mock_openai_client_manager,
            storage_manager=storage_manager,
            cache_manager=cache_manager,
            settings=mock_image_settings
        )
    
    @pytest.mark.asyncio
    async def test_generate_image_basic(self, generation_tool, mock_openai_client):
        """Test basic image generation."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        mock_response.data[0].revised_prompt = "A beautiful sunset over mountains"
        
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
        
        # Generate image
        result = await generation_tool.generate(
            prompt="A beautiful sunset",
            quality=ImageQuality.HIGH,
            size=ImageSize.SQUARE,
            style=ImageStyle.VIVID
        )
        
        # Verify result structure
        assert "task_id" in result
        assert "image_id" in result
        assert "image_url" in result
        assert "resource_uri" in result
        assert "metadata" in result
        
        # Verify result values
        assert result["task_id"].startswith("task_")
        assert result["image_id"].startswith("img_")
        assert result["image_url"].startswith("data:image/")
        assert result["resource_uri"].startswith("generated-images://")
        
        # Verify metadata
        metadata = result["metadata"]
        assert metadata["prompt"] == "A beautiful sunset"
        assert metadata["revised_prompt"] == "A beautiful sunset over mountains"
        assert metadata["quality"] == "high"
        assert metadata["size"] == "1024x1024"
        assert metadata["style"] == "vivid"
        assert "generation_time" in metadata
        assert "tokens_used" in metadata
    
    @pytest.mark.asyncio
    async def test_generate_image_with_defaults(self, generation_tool, mock_openai_client):
        """Test image generation with default parameters."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "test_base64_data"
        mock_response.data[0].revised_prompt = "Default test image"
        
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
        
        # Generate with minimal parameters
        result = await generation_tool.generate(prompt="test image")
        
        # Should use default settings
        metadata = result["metadata"]
        assert metadata["quality"] == "auto"  # From mock_image_settings
        assert metadata["size"] == "1024x1024"
        assert metadata["style"] == "vivid"
    
    @pytest.mark.asyncio
    async def test_generate_image_with_cache_hit(self, generation_tool, mock_openai_client):
        """Test image generation with cache hit."""
        # Mock cache to return a result
        cached_result = {
            "task_id": "cached_task_123",
            "image_id": "cached_img_456",
            "image_url": "data:image/png;base64,cached_data",
            "metadata": {"prompt": "cached image"}
        }
        
        generation_tool.cache_manager.get_image_generation = AsyncMock(return_value=cached_result)
        
        # Generate image (should hit cache)
        result = await generation_tool.generate(prompt="cached image")
        
        # Should return cached result
        assert result == cached_result
        
        # OpenAI should not be called
        mock_openai_client.images.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_image_cache_miss_and_store(self, generation_tool, mock_openai_client):
        """Test image generation with cache miss and subsequent storage."""
        # Mock cache miss
        generation_tool.cache_manager.get_image_generation = AsyncMock(return_value=None)
        generation_tool.cache_manager.set_image_generation = AsyncMock(return_value=True)
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "new_image_data"
        mock_response.data[0].revised_prompt = "New generated image"
        
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
        
        # Generate image
        result = await generation_tool.generate(prompt="new image")
        
        # Should call OpenAI
        mock_openai_client.images.generate.assert_called_once()
        
        # Should store in cache
        generation_tool.cache_manager.set_image_generation.assert_called_once()
        
        # Verify generation parameters passed to OpenAI
        call_args = mock_openai_client.images.generate.call_args
        assert call_args[1]["prompt"] == "new image"
        assert call_args[1]["model"] == "gpt-image-1"
        assert call_args[1]["response_format"] == "b64_json"
    
    @pytest.mark.asyncio
    async def test_generate_image_with_format_conversion(self, generation_tool, mock_openai_client):
        """Test image generation with format conversion."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        # PNG data in base64
        mock_response.data[0].b64_json = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        mock_response.data[0].revised_prompt = "Format test"
        
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
        
        # Generate with JPEG output format
        result = await generation_tool.generate(
            prompt="format test",
            output_format=OutputFormat.JPEG,
            compression=85
        )
        
        # Should convert to JPEG format
        assert result["image_url"].startswith("data:image/jpeg;base64,")
        
        metadata = result["metadata"]
        assert metadata["output_format"] == "jpeg"
        assert metadata["compression"] == 85
    
    @pytest.mark.asyncio
    async def test_generate_image_with_background_processing(self, generation_tool, mock_openai_client):
        """Test image generation with background processing."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        mock_response.data[0].revised_prompt = "Background test"
        
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
        
        # Generate with opaque background
        result = await generation_tool.generate(
            prompt="background test",
            background=BackgroundType.OPAQUE
        )
        
        metadata = result["metadata"]
        assert metadata["background"] == "opaque"
    
    @pytest.mark.asyncio
    async def test_generate_image_error_handling(self, generation_tool, mock_openai_client):
        """Test error handling during image generation."""
        # Mock OpenAI to raise an exception
        mock_openai_client.images.generate = AsyncMock(side_effect=Exception("API Error"))
        
        # Should propagate the exception
        with pytest.raises(Exception, match="API Error"):
            await generation_tool.generate(prompt="error test")
    
    @pytest.mark.asyncio
    async def test_generate_image_with_moderation(self, generation_tool, mock_openai_client):
        """Test image generation with content moderation."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "safe_image_data"
        mock_response.data[0].revised_prompt = "Safe content"
        
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
        
        # Generate with moderation
        result = await generation_tool.generate(
            prompt="safe content",
            moderation="auto"
        )
        
        # Should include moderation info in metadata
        metadata = result["metadata"]
        assert "moderation" in metadata
    
    @pytest.mark.asyncio
    async def test_generate_image_parameter_validation(self, generation_tool):
        """Test parameter validation before generation."""
        # Invalid prompt should raise error
        with pytest.raises(ValueError):
            await generation_tool.generate(prompt="")
        
        with pytest.raises(ValueError):
            await generation_tool.generate(prompt=None)
    
    @pytest.mark.asyncio
    async def test_generate_image_storage_integration(self, generation_tool, mock_openai_client):
        """Test integration with storage manager."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "storage_test_data"
        mock_response.data[0].revised_prompt = "Storage test"
        
        mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
        
        # Mock storage manager
        generation_tool.storage_manager.store_image = AsyncMock()
        
        # Generate image
        result = await generation_tool.generate(prompt="storage test")
        
        # Verify storage was called
        generation_tool.storage_manager.store_image.assert_called_once()
        
        # Check parameters passed to storage
        call_args = generation_tool.storage_manager.store_image.call_args
        image_id = call_args[0][0]
        image_data = call_args[0][1]
        metadata = call_args[0][2]
        
        assert image_id == result["image_id"]
        assert isinstance(image_data, bytes)
        assert metadata["prompt"] == "storage test"


class TestImageEditingTool:
    """Test image editing tool functionality."""
    
    @pytest.fixture
    def editing_tool(self, mock_openai_client_manager, storage_manager, cache_manager, mock_image_settings):
        """Create image editing tool for testing."""
        return ImageEditingTool(
            openai_client=mock_openai_client_manager,
            storage_manager=storage_manager,
            cache_manager=cache_manager,
            settings=mock_image_settings
        )
    
    @pytest.mark.asyncio
    async def test_edit_image_basic(self, editing_tool, mock_openai_client, sample_image_data):
        """Test basic image editing."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "edited_image_data"
        mock_response.data[0].revised_prompt = "Edited: Add blue sky"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Edit image
        result = await editing_tool.edit(
            image_data=sample_image_data,
            prompt="Add blue sky",
            size=ImageSize.SQUARE,
            quality=ImageQuality.HIGH
        )
        
        # Verify result structure
        assert "task_id" in result
        assert "image_id" in result
        assert "image_url" in result
        assert "resource_uri" in result
        assert "operation" in result
        assert "metadata" in result
        
        # Verify operation type
        assert result["operation"] == "edit"
        
        # Verify metadata
        metadata = result["metadata"]
        assert metadata["prompt"] == "Add blue sky"
        assert metadata["revised_prompt"] == "Edited: Add blue sky"
        assert metadata["operation"] == "edit"
        assert "edit_time" in metadata
    
    @pytest.mark.asyncio
    async def test_edit_image_with_mask(self, editing_tool, mock_openai_client, sample_image_data):
        """Test image editing with mask."""
        mask_data = "data:image/png;base64,mask_data_here"
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "masked_edit_result"
        mock_response.data[0].revised_prompt = "Masked edit result"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Edit with mask
        result = await editing_tool.edit(
            image_data=sample_image_data,
            prompt="Edit specific area",
            mask_data=mask_data
        )
        
        # Verify mask was used
        call_args = mock_openai_client.images.edit.call_args
        assert "mask" in call_args[1]
        
        # Verify metadata includes mask info
        metadata = result["metadata"]
        assert metadata["has_mask"] is True
    
    @pytest.mark.asyncio
    async def test_edit_image_without_mask(self, editing_tool, mock_openai_client, sample_image_data):
        """Test image editing without mask."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "full_edit_result"
        mock_response.data[0].revised_prompt = "Full image edit"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Edit without mask
        result = await editing_tool.edit(
            image_data=sample_image_data,
            prompt="Edit entire image"
        )
        
        # Verify no mask was passed
        call_args = mock_openai_client.images.edit.call_args
        assert "mask" not in call_args[1] or call_args[1]["mask"] is None
        
        # Verify metadata
        metadata = result["metadata"]
        assert metadata["has_mask"] is False
    
    @pytest.mark.asyncio
    async def test_edit_image_format_conversion(self, editing_tool, mock_openai_client, sample_image_data):
        """Test image editing with format conversion."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        mock_response.data[0].revised_prompt = "Format converted edit"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Edit with WEBP output
        result = await editing_tool.edit(
            image_data=sample_image_data,
            prompt="convert format",
            output_format=OutputFormat.WEBP,
            compression=90
        )
        
        # Should convert to WebP
        assert result["image_url"].startswith("data:image/webp;base64,")
        
        metadata = result["metadata"]
        assert metadata["output_format"] == "webp"
        assert metadata["compression"] == 90
    
    @pytest.mark.asyncio
    async def test_edit_image_parameter_validation(self, editing_tool):
        """Test parameter validation for image editing."""
        # Invalid image data
        with pytest.raises(ValueError):
            await editing_tool.edit(image_data="", prompt="test")
        
        with pytest.raises(ValueError):
            await editing_tool.edit(image_data=None, prompt="test")
        
        # Invalid prompt
        with pytest.raises(ValueError):
            await editing_tool.edit(image_data="data:image/png;base64,test", prompt="")
        
        with pytest.raises(ValueError):
            await editing_tool.edit(image_data="data:image/png;base64,test", prompt=None)
    
    @pytest.mark.asyncio
    async def test_edit_image_data_url_processing(self, editing_tool, mock_openai_client):
        """Test processing of different data URL formats."""
        # Test with full data URL
        full_data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        # Test with raw base64
        raw_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "processed_result"
        mock_response.data[0].revised_prompt = "Processed edit"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Test with full data URL
        result1 = await editing_tool.edit(image_data=full_data_url, prompt="test1")
        assert "image_id" in result1
        
        # Test with raw base64 (should be converted to data URL)
        result2 = await editing_tool.edit(image_data=raw_base64, prompt="test2")
        assert "image_id" in result2
        
        # Both should have called OpenAI edit
        assert mock_openai_client.images.edit.call_count == 2
    
    @pytest.mark.asyncio
    async def test_edit_image_error_handling(self, editing_tool, mock_openai_client, sample_image_data):
        """Test error handling during image editing."""
        # Mock OpenAI to raise an exception
        mock_openai_client.images.edit = AsyncMock(side_effect=Exception("Edit API Error"))
        
        # Should propagate the exception
        with pytest.raises(Exception, match="Edit API Error"):
            await editing_tool.edit(image_data=sample_image_data, prompt="error test")
    
    @pytest.mark.asyncio
    async def test_edit_image_storage_integration(self, editing_tool, mock_openai_client, sample_image_data):
        """Test integration with storage manager during editing."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "stored_edit_result"
        mock_response.data[0].revised_prompt = "Storage integration test"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Mock storage manager
        editing_tool.storage_manager.store_image = AsyncMock()
        
        # Edit image
        result = await editing_tool.edit(
            image_data=sample_image_data,
            prompt="storage integration test"
        )
        
        # Verify storage was called
        editing_tool.storage_manager.store_image.assert_called_once()
        
        # Check parameters passed to storage
        call_args = editing_tool.storage_manager.store_image.call_args
        image_id = call_args[0][0]
        image_data = call_args[0][1]
        metadata = call_args[0][2]
        
        assert image_id == result["image_id"]
        assert isinstance(image_data, bytes)
        assert metadata["prompt"] == "storage integration test"
        assert metadata["operation"] == "edit"
    
    @pytest.mark.asyncio
    async def test_edit_image_with_background_processing(self, editing_tool, mock_openai_client, sample_image_data):
        """Test image editing with background processing."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "background_processed"
        mock_response.data[0].revised_prompt = "Background processed edit"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Edit with transparent background
        result = await editing_tool.edit(
            image_data=sample_image_data,
            prompt="make background transparent",
            background=BackgroundType.TRANSPARENT,
            output_format=OutputFormat.PNG  # PNG supports transparency
        )
        
        metadata = result["metadata"]
        assert metadata["background"] == "transparent"
        assert metadata["output_format"] == "png"
        
        # Should ensure PNG format for transparency
        assert result["image_url"].startswith("data:image/png;base64,")
    
    @pytest.mark.asyncio
    async def test_edit_image_quality_settings(self, editing_tool, mock_openai_client, sample_image_data):
        """Test image editing with different quality settings."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "quality_test_result"
        mock_response.data[0].revised_prompt = "Quality test"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Test with different quality levels
        for quality in [ImageQuality.HIGH, ImageQuality.MEDIUM, ImageQuality.LOW]:
            result = await editing_tool.edit(
                image_data=sample_image_data,
                prompt=f"test {quality.value} quality",
                quality=quality
            )
            
            metadata = result["metadata"]
            assert metadata["quality"] == quality.value
    
    @pytest.mark.asyncio
    async def test_edit_image_size_settings(self, editing_tool, mock_openai_client, sample_image_data):
        """Test image editing with different size settings."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].b64_json = "size_test_result"
        mock_response.data[0].revised_prompt = "Size test"
        
        mock_openai_client.images.edit = AsyncMock(return_value=mock_response)
        
        # Test with different sizes
        for size in [ImageSize.SQUARE, ImageSize.LANDSCAPE, ImageSize.PORTRAIT]:
            result = await editing_tool.edit(
                image_data=sample_image_data,
                prompt=f"test {size.value} size",
                size=size
            )
            
            metadata = result["metadata"]
            assert metadata["size"] == size.value
            
            # Verify OpenAI was called with correct size
            call_args = mock_openai_client.images.edit.call_args
            assert call_args[1]["size"] == size.value