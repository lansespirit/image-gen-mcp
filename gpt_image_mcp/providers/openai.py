"""OpenAI provider implementation."""

import base64
import logging
from typing import Any

import httpx
from openai import AsyncOpenAI

from .base import (
    ImageResponse,
    LLMProvider,
    ModelCapability,
    ProviderConfig,
    ProviderError,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider for image generation using gpt-image-1 and DALL-E models."""

    # Supported models and their capabilities
    SUPPORTED_MODELS = {
        "gpt-image-1": ModelCapability(
            model_id="gpt-image-1",
            supported_sizes=["auto", "1024x1024", "1536x1024", "1024x1536"],
            supported_qualities=["auto", "high", "medium", "low"],
            supported_formats=["png", "jpeg", "webp"],
            max_images_per_request=1,
            supports_style=True,
            supports_background=True,
            supports_compression=True,
            custom_parameters={
                "moderation": ["auto", "low"],
                "style": ["vivid", "natural"],
                "background": ["auto", "transparent", "opaque"],
            },
        )
    }

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            organization=config.organization,
            base_url=config.base_url or "https://api.openai.com/v1",
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    def get_supported_models(self) -> set[str]:
        """Return set of supported OpenAI model IDs."""
        return set(self.SUPPORTED_MODELS.keys())

    def get_model_capabilities(self, model_id: str) -> ModelCapability | None:
        """Get capabilities for a specific OpenAI model."""
        return self.SUPPORTED_MODELS.get(model_id)

    async def generate_image(
        self,
        model: str,
        prompt: str,
        quality: str = "auto",
        size: str = "auto",
        style: str = "vivid",
        moderation: str = "auto",
        output_format: str = "png",
        compression: int = 100,
        background: str = "auto",
        n: int = 1,
        **kwargs,
    ) -> ImageResponse:
        """Generate image using OpenAI's Images API."""

        # Validate model
        if model not in self.SUPPORTED_MODELS:
            raise ProviderError(
                f"Model '{model}' is not supported by OpenAI provider",
                provider_name=self.name,
                error_code="UNSUPPORTED_MODEL",
            )

        capabilities = self.SUPPORTED_MODELS[model]

        # Build request parameters
        request_params = {
            "model": model,
            "prompt": prompt,
            "n": min(n, capabilities.max_images_per_request),
        }

        # Map quality parameter based on model
        if model == "dall-e-3":
            request_params["quality"] = "hd" if quality == "high" else "standard"
        elif model == "gpt-image-1":
            request_params["quality"] = quality
            request_params["moderation"] = moderation

        # Add size parameter
        if size in capabilities.supported_sizes:
            request_params["size"] = size
        else:
            request_params["size"] = capabilities.supported_sizes[0]
            self._logger.warning(
                f"Size '{size}' not supported, using {request_params['size']}"
            )

        # Add style parameter if supported
        if capabilities.supports_style:
            request_params["style"] = style

        # Add gpt-image-1 specific parameters
        if model == "gpt-image-1":
            request_params.update(
                {
                    "output_format": output_format,
                    "background": background,
                }
            )

            # Add compression for JPEG/WebP
            if output_format in ["jpeg", "webp"] and compression < 100:
                request_params["output_compression"] = compression

        try:
            self._logger.info(f"Generating image with OpenAI model {model}")
            self._logger.debug(f"Request parameters: {request_params}")

            response = await self.client.images.generate(**request_params)

            # Process response - OpenAI returns base64 for gpt-image-1, URLs for DALL-E
            if hasattr(response.data[0], "b64_json") and response.data[0].b64_json:
                # Base64 response (gpt-image-1)
                image_bytes = base64.b64decode(response.data[0].b64_json)
            elif hasattr(response.data[0], "url") and response.data[0].url:
                # URL response (DALL-E models)
                image_bytes = await self._download_image(response.data[0].url)
            else:
                raise ProviderError(
                    "OpenAI response contains neither base64 data nor URL",
                    provider_name=self.name,
                    error_code="INVALID_RESPONSE",
                )

            # Build metadata
            metadata = {
                "model": model,
                "prompt": prompt,
                "size": request_params["size"],
                "quality": request_params.get("quality", "auto"),
                "style": request_params.get("style", "vivid"),
                "output_format": request_params.get("output_format", "png"),
                "provider": self.name,
                "created_at": getattr(response, "created", None),
            }

            # Add usage information if available
            if hasattr(response, "usage") and response.usage:
                metadata["usage"] = {
                    "total_tokens": response.usage.total_tokens,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }

            return ImageResponse(
                image_data=image_bytes,
                metadata=metadata,
                provider_response=(
                    response.model_dump() if hasattr(response, "model_dump") else None
                ),
            )

        except Exception as e:
            self._logger.error(f"Error generating image with OpenAI: {e}")
            raise ProviderError(
                f"OpenAI image generation failed: {str(e)}",
                provider_name=self.name,
                error_code="GENERATION_FAILED",
            )

    async def edit_image(
        self,
        model: str,
        image_data: str | bytes,
        prompt: str,
        mask_data: str | bytes | None = None,
        quality: str = "auto",
        size: str = "1536x1024",
        output_format: str = "png",
        compression: int = 100,
        background: str = "auto",
        n: int = 1,
        **kwargs,
    ) -> ImageResponse:
        """Edit image using OpenAI's Images API."""

        # Validate model
        if model not in self.SUPPORTED_MODELS:
            raise ProviderError(
                f"Model '{model}' is not supported by OpenAI provider",
                provider_name=self.name,
                error_code="UNSUPPORTED_MODEL",
            )

        capabilities = self.SUPPORTED_MODELS[model]

        # Convert base64 strings to bytes if needed
        if isinstance(image_data, str):
            if image_data.startswith("data:"):
                image_data = image_data.split(",", 1)[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data

        mask_bytes = None
        if mask_data:
            if isinstance(mask_data, str):
                if mask_data.startswith("data:"):
                    mask_data = mask_data.split(",", 1)[1]
                mask_bytes = base64.b64decode(mask_data)
            else:
                mask_bytes = mask_data

        # Build request parameters
        request_params = {
            "model": model,
            "image": image_bytes,
            "prompt": prompt,
            "n": min(n, capabilities.max_images_per_request),
        }

        if mask_bytes:
            request_params["mask"] = mask_bytes

        # Add size parameter
        if size in capabilities.supported_sizes:
            request_params["size"] = size
        else:
            request_params["size"] = capabilities.supported_sizes[0]

        # Add gpt-image-1 specific parameters
        if model == "gpt-image-1":
            request_params.update(
                {
                    "quality": quality,
                    "output_format": output_format,
                    "background": background,
                }
            )

            # Add compression for JPEG/WebP
            if output_format in ["jpeg", "webp"] and compression < 100:
                request_params["output_compression"] = compression

        try:
            self._logger.info(f"Editing image with OpenAI model {model}")
            self._logger.debug(f"Request parameters: {list(request_params.keys())}")

            response = await self.client.images.edit(**request_params)

            # Process response (similar to generate_image)
            if hasattr(response.data[0], "b64_json") and response.data[0].b64_json:
                image_bytes = base64.b64decode(response.data[0].b64_json)
            elif hasattr(response.data[0], "url") and response.data[0].url:
                image_bytes = await self._download_image(response.data[0].url)
            else:
                raise ProviderError(
                    "OpenAI response contains neither base64 data nor URL",
                    provider_name=self.name,
                    error_code="INVALID_RESPONSE",
                )

            metadata = {
                "model": model,
                "prompt": prompt,
                "size": request_params["size"],
                "output_format": request_params.get("output_format", "png"),
                "provider": self.name,
                "operation": "edit",
                "created_at": getattr(response, "created", None),
            }

            return ImageResponse(
                image_data=image_bytes,
                metadata=metadata,
                provider_response=(
                    response.model_dump() if hasattr(response, "model_dump") else None
                ),
            )

        except Exception as e:
            self._logger.error(f"Error editing image with OpenAI: {e}")
            raise ProviderError(
                f"OpenAI image editing failed: {str(e)}",
                provider_name=self.name,
                error_code="EDITING_FAILED",
            )

    async def _download_image(self, image_url: str) -> bytes:
        """Download image from URL (for DALL-E models that return URLs)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return response.content
        except Exception as e:
            raise ProviderError(
                f"Failed to download image from URL: {str(e)}",
                provider_name=self.name,
                error_code="DOWNLOAD_FAILED",
            )

    def estimate_cost(
        self, model: str, prompt: str, image_count: int = 1
    ) -> dict[str, Any]:
        """Estimate cost for OpenAI image generation."""

        # OpenAI pricing (as of 2024)
        pricing = {
            "gpt-image-1": {
                "text_input_per_1m_tokens": 5.0,
                "image_output_per_1m_tokens": 40.0,
                "tokens_per_image": 1750,
            },
            "dall-e-3": {
                "cost_per_image": 0.04,  # $0.04 per image
            },
            "dall-e-2": {
                "cost_per_image": 0.02,  # $0.02 per image
            },
        }

        if model not in pricing:
            return super().estimate_cost(model, prompt, image_count)

        model_pricing = pricing[model]

        if model == "gpt-image-1":
            # Token-based pricing
            text_tokens = len(prompt.split()) * 1.3  # Rough approximation
            text_cost = (text_tokens / 1_000_000) * model_pricing[
                "text_input_per_1m_tokens"
            ]
            image_cost = (
                image_count * model_pricing["tokens_per_image"] / 1_000_000
            ) * model_pricing["image_output_per_1m_tokens"]
            total_cost = text_cost + image_cost

            return {
                "provider": self.name,
                "model": model,
                "estimated_cost_usd": round(total_cost, 4),
                "currency": "USD",
                "breakdown": {
                    "text_input_cost": round(text_cost, 4),
                    "image_output_cost": round(image_cost, 4),
                    "text_tokens": int(text_tokens),
                    "image_tokens": model_pricing["tokens_per_image"] * image_count,
                    "total_images": image_count,
                },
            }
        else:
            # Fixed price per image
            total_cost = model_pricing["cost_per_image"] * image_count

            return {
                "provider": self.name,
                "model": model,
                "estimated_cost_usd": round(total_cost, 4),
                "currency": "USD",
                "breakdown": {
                    "per_image": model_pricing["cost_per_image"],
                    "total_images": image_count,
                    "base_cost": total_cost,
                },
            }
