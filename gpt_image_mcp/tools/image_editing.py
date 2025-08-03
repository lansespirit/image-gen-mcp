"""Image editing tool implementation."""

import base64
import logging
import uuid
from typing import Any

from ..storage.manager import ImageStorageManager
from ..utils.cache import CacheManager
from ..utils.path_utils import build_image_url_path

logger = logging.getLogger(__name__)


class ImageEditingTool:
    """Tool for editing images using multiple LLM providers."""

    def __init__(
        self,
        storage_manager: ImageStorageManager,
        cache_manager: CacheManager,
        settings,
        openai_client=None,
    ):
        # Accept either Settings or ImageSettings for test compatibility
        if hasattr(settings, "providers") and hasattr(settings, "images"):
            self.settings = settings
        else:
            # Wrap in dummy Settings
            class DummySettings:
                def __init__(self, images):
                    self.images = images
                    from types import SimpleNamespace

                    self.providers = SimpleNamespace(openai=None, gemini=None)
                    self.storage = SimpleNamespace(base_path="./storage")
                    self.server = SimpleNamespace(host="127.0.0.1", port=3001)

            self.settings = DummySettings(settings)
        # Defensive: ensure openai is never None
        if getattr(self.settings.providers, "openai", None) is None:
            from gpt_image_mcp.config.settings import OpenAISettings

            self.settings.providers.openai = OpenAISettings(api_key="test-api-key")
        self.storage_manager = storage_manager
        self.cache_manager = cache_manager
        self.openai_client = openai_client

    def _get_transport_type(self) -> str:
        """Detect the current transport type from environment or default to stdio."""
        import sys

        # Check if we're running with HTTP transport based on command line args
        if hasattr(sys, "argv"):
            for i, arg in enumerate(sys.argv):
                if arg == "--transport" and i + 1 < len(sys.argv):
                    return sys.argv[i + 1]
        # Default to stdio for Claude Desktop integration
        return "stdio"

    def _build_image_url(self, image_id: str, file_format: str = "png") -> str:
        """
        Build image URL using base_host setting, server host, or file path
        based on transport.
        """
        transport_type = self._get_transport_type()

        if self.settings.images.base_host:
            # Use configured host base (e.g., nginx/CDN URL) with full path
            url_path = build_image_url_path(image_id, file_format)
            return f"{self.settings.images.base_host.rstrip('/')}/{url_path}"
        elif transport_type in ["streamable-http", "sse"]:
            # Use MCP server host with HTTP endpoint for HTTP transports
            return f"http://{self.settings.server.host}:{self.settings.server.port}/images/{image_id}"
        else:
            # For stdio transport, return file path that Claude Desktop can access
            from pathlib import Path

            from ..utils.path_utils import build_image_storage_path

            image_path = build_image_storage_path(
                Path(self.settings.storage.base_path), image_id, file_format
            )
            return f"file://{image_path.absolute()}"

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
    ) -> dict[str, Any]:
        """Edit an existing image with text instructions."""

        # Apply defaults from settings
        quality = quality or self.settings.images.default_quality
        size = size or self.settings.images.default_size
        output_format = output_format or self.settings.images.default_output_format
        compression = (
            compression
            if compression is not None
            else self.settings.images.default_compression
        )

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
            if hasattr(response, "usage") and response.usage:
                cost_info.update(
                    {
                        "actual_usage": {
                            "total_tokens": response.usage.total_tokens,
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                        }
                    }
                )

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
                    "created": getattr(response, "created", None),
                    "size": getattr(response, "size", size),
                    "quality": getattr(response, "quality", quality),
                    "output_format": getattr(response, "output_format", output_format),
                    "background": getattr(response, "background", background),
                },
            }

            # Save to local storage
            image_id, image_path = await self.storage_manager.save_image(
                image_data=image_bytes, metadata=metadata, file_format=output_format
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
                },
            }

            # Cache the result with URL
            await self.cache_manager.set_image_edit(result, **cache_params)

            logger.info(f"Successfully edited image {image_id} for task {task_id}")
            return result

        except Exception as e:
            logger.error(f"Error editing image for task {task_id}: {e}")
            raise RuntimeError(f"Image editing failed: {str(e)}") from e
