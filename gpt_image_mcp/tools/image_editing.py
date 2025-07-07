"""Image editing tool implementation."""

import base64
import logging
import uuid
from typing import Any, Dict

from ..config.settings import Settings
from ..storage.manager import ImageStorageManager
from ..utils.cache import CacheManager
from ..utils.openai_client import OpenAIClientManager
from ..utils.path_utils import build_image_url_path

logger = logging.getLogger(__name__)


class ImageEditingTool:
    """Tool for editing images using OpenAI's gpt-image-1 model."""
    
    def __init__(
        self,
        openai_client: OpenAIClientManager,
        storage_manager: ImageStorageManager,
        cache_manager: CacheManager,
        settings: Settings,
    ):
        self.openai_client = openai_client
        self.storage_manager = storage_manager
        self.cache_manager = cache_manager
        self.settings = settings
    
    def _build_image_url(self, image_id: str, file_format: str = "png") -> str:
        """Build image URL using base_host setting or server host."""
        if self.settings.images.base_host:
            # Use configured host base (e.g., nginx/CDN URL) with full path
            url_path = build_image_url_path(image_id, file_format)
            return f"{self.settings.images.base_host.rstrip('/')}/{url_path}"
        else:
            # Use MCP server host with simple endpoint
            return f"http://{self.settings.server.host}:{self.settings.server.port}/images/{image_id}"
    
    async def edit(
        self,
        image_data: str,
        prompt: str,
        mask_data: str | None = None,
        size: str = "1536x1024",
        quality: str = "auto",
        output_format: str = "png",
        compression: int = 100,
        background: str = "auto",
    ) -> Dict[str, Any]:
        """Edit an existing image with text instructions."""
        
        # Apply defaults from settings
        quality = quality or self.settings.images.default_quality
        size = size or self.settings.images.default_size
        output_format = output_format or self.settings.images.default_output_format
        compression = compression if compression is not None else self.settings.images.default_compression
        
        # Generate task ID for tracking
        task_id = str(uuid.uuid4())
        
        # Check cache first (using hash of image data)
        cache_params = {
            "image_data": image_data,
            "prompt": prompt,
            "mask_data": mask_data,
            "quality": quality,
            "size": size,
            "output_format": output_format,
            "compression": compression,
            "background": background,
            "model": self.settings.images.default_model,
        }
        
        cached_result = await self.cache_manager.get_image_edit(**cache_params)
        if cached_result:
            logger.info(f"Returning cached edit result for prompt: {prompt[:50]}...")
            return cached_result
        
        try:
            # Validate image data format
            if image_data.startswith("data:"):
                # Extract base64 data from data URL
                image_data = image_data.split(",", 1)[1]
            
            # Edit image using OpenAI API
            logger.info(f"Editing image for task {task_id}")
            response = await self.openai_client.edit_image(
                image_data=image_data,
                prompt=prompt,
                mask_data=mask_data,
                model=self.settings.images.default_model,
                quality=quality,
                size=size,
                output_format=output_format,
                compression=compression,
                background=background,
                n=1,
            )
            
            # Process the first (and only) edited image
            edited_image_data = response.data[0]
            
            # Decode base64 image data
            image_bytes = base64.b64decode(edited_image_data.b64_json)
            
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
                "operation": "edit",
                "prompt": prompt,
                "has_mask": mask_data is not None,
                "parameters": {
                    "model": self.settings.images.default_model,
                    "quality": quality,
                    "size": size,
                    "output_format": output_format,
                    "compression": compression,
                    "background": background,
                },
                "cost_info": cost_info,
                "api_response": {
                    "created": getattr(response, 'created', None),
                    "size": getattr(response, 'size', size),
                    "quality": getattr(response, 'quality', quality),
                    "output_format": getattr(response, 'output_format', output_format),
                    "background": getattr(response, 'background', background),
                }
            }
            
            # Save to local storage
            image_id, image_path = await self.storage_manager.save_image(
                image_data=image_bytes,
                metadata=metadata,
                file_format=output_format
            )
            
            # Build image URL instead of base64 data
            image_url = self._build_image_url(image_id, output_format)
            
            # Prepare result
            result = {
                "task_id": task_id,
                "image_id": image_id,
                "image_url": image_url,  # URL instead of base64 data
                "resource_uri": f"generated-images://{image_id}",
                "operation": "edit",
                "metadata": {
                    "size": size,
                    "quality": quality,
                    "output_format": output_format,
                    "background": background,
                    "prompt": prompt,
                    "has_mask": mask_data is not None,
                    "created_at": metadata.get("created_at"),
                    "cost_estimate": cost_info.get("estimated_cost_usd"),
                    "file_size_bytes": len(image_bytes),
                    "dimensions": size,
                    "format": output_format.upper(),
                    "local_path": str(image_path),
                }
            }
            
            # Cache the result with URL
            await self.cache_manager.set_image_edit(result, **cache_params)
            
            logger.info(f"Successfully edited image {image_id} for task {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error editing image for task {task_id}: {e}")
            raise RuntimeError(f"Image editing failed: {str(e)}") from e