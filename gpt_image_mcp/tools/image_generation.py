"""Image generation tool implementation."""

import base64
import logging
import uuid
from typing import Any, Dict

from ..config.settings import ImageSettings
from ..storage.manager import ImageStorageManager
from ..utils.cache import CacheManager
from ..utils.openai_client import OpenAIClientManager
from ..types.enums import (
    ImageQuality,
    ImageSize,
    ImageStyle,
    ModerationLevel,
    OutputFormat,
    BackgroundType,
)

logger = logging.getLogger(__name__)


class ImageGenerationTool:
    """Tool for generating images using OpenAI's gpt-image-1 model."""
    
    def __init__(
        self,
        openai_client: OpenAIClientManager,
        storage_manager: ImageStorageManager,
        cache_manager: CacheManager,
        settings: ImageSettings,
    ):
        self.openai_client = openai_client
        self.storage_manager = storage_manager
        self.cache_manager = cache_manager
        self.settings = settings
    
    async def generate(
        self,
        prompt: str,
        quality: ImageQuality | str = ImageQuality.AUTO,
        size: ImageSize | str = ImageSize.LANDSCAPE,
        style: ImageStyle | str = ImageStyle.VIVID,
        moderation: ModerationLevel | str = ModerationLevel.AUTO,
        output_format: OutputFormat | str = OutputFormat.PNG,
        compression: int = 100,
        background: BackgroundType | str = BackgroundType.AUTO,
    ) -> Dict[str, Any]:
        """Generate an image from a text prompt."""
        
        # Convert enums to string values for API calls
        # The parameters already come validated from server.py
        quality_str = quality.value if isinstance(quality, ImageQuality) else str(quality)
        size_str = size.value if isinstance(size, ImageSize) else str(size)
        style_str = style.value if isinstance(style, ImageStyle) else str(style)
        moderation_str = moderation.value if isinstance(moderation, ModerationLevel) else str(moderation)
        output_format_str = output_format.value if isinstance(output_format, OutputFormat) else str(output_format)
        background_str = background.value if isinstance(background, BackgroundType) else str(background)
        
        # Generate task ID for tracking
        task_id = str(uuid.uuid4())
        
        # Check cache first
        cache_params = {
            "prompt": prompt,
            "quality": quality_str,
            "size": size_str,
            "style": style_str,
            "moderation": moderation_str,
            "output_format": output_format_str,
            "compression": compression,
            "background": background_str,
            "model": self.settings.default_model,
        }
        
        cached_result = await self.cache_manager.get_image_generation(**cache_params)
        if cached_result:
            logger.info(f"Returning cached result for prompt: {prompt[:50]}...")
            return cached_result
        
        try:
            # Generate image using OpenAI API
            logger.info(f"Generating image for task {task_id}")
            response = await self.openai_client.generate_image(
                prompt=prompt,
                model=self.settings.default_model,
                quality=quality_str,
                size=size_str,
                style=style_str,
                moderation=moderation_str,
                output_format=output_format_str,
                compression=compression,
                background=background_str,
                n=1,
            )
            
            # Process the first (and only) image
            image_data = response.data[0]
            
            # Decode base64 image data
            image_bytes = base64.b64decode(image_data.b64_json)
            
            # Estimate cost
            cost_info = self.openai_client.estimate_cost(prompt, 1)
            
            # Add actual usage if available
            if hasattr(response, 'usage') and response.usage:
                cost_info.update({
                    "actual_usage": {
                        "total_tokens": response.usage.total_tokens,
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    }
                })
            
            # Prepare metadata
            metadata = {
                "task_id": task_id,
                "prompt": prompt,
                "parameters": {
                    "model": self.settings.default_model,
                    "quality": quality_str,
                    "size": size_str,
                    "style": style_str,
                    "moderation": moderation_str,
                    "output_format": output_format_str,
                    "compression": compression,
                    "background": background_str,
                },
                "cost_info": cost_info,
                "api_response": {
                    "created": getattr(response, 'created', None),
                    "size": getattr(response, 'size', size_str),
                    "quality": getattr(response, 'quality', quality_str),
                    "output_format": getattr(response, 'output_format', output_format_str),
                    "background": getattr(response, 'background', background_str),
                }
            }
            
            # Save to local storage
            image_id, image_path = await self.storage_manager.save_image(
                image_data=image_bytes,
                metadata=metadata,
                file_format=output_format_str
            )
            
            # Create base64 data URL for immediate client use
            mime_type = f"image/{output_format_str}"
            data_url = f"data:{mime_type};base64,{image_data.b64_json}"
            
            # Prepare result
            result = {
                "task_id": task_id,
                "image_id": image_id,
                "image_url": data_url,  # Complete data URL with image data
                "resource_uri": f"generated-images://{image_id}",
                "metadata": {
                    "size": size_str,
                    "quality": quality_str,
                    "style": style_str,
                    "moderation": moderation_str,
                    "output_format": output_format_str,
                    "background": background_str,
                    "prompt": prompt,
                    "created_at": metadata.get("created_at"),
                    "cost_estimate": cost_info.get("estimated_cost_usd"),
                    "file_size_bytes": len(image_bytes),
                    "dimensions": size_str,
                    "format": output_format_str.upper(),
                    "local_path": str(image_path),
                }
            }
            
            # Cache the result (without the large base64 data)
            cache_result = result.copy()
            cache_result["image_url"] = f"generated-images://{image_id}"  # Use resource URI for cache
            await self.cache_manager.set_image_generation(cache_result, **cache_params)
            
            logger.info(f"Successfully generated image {image_id} for task {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating image for task {task_id}: {e}")
            raise RuntimeError(f"Image generation failed: {str(e)}") from e