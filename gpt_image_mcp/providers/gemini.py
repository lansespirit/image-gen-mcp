"""Gemini provider implementation using OpenAI compatibility mode."""

import base64
import logging
from typing import Any

from openai import AsyncOpenAI

from .base import (
    ImageResponse,
    LLMProvider,
    ModelCapability,
    ProviderConfig,
    ProviderError,
)

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini provider for image generation using Imagen models via
    OpenAI compatibility."""

    # Supported Imagen models and their capabilities
    SUPPORTED_MODELS = {
        "imagen-4": ModelCapability(
            model_id="imagen-4",
            supported_sizes=["1024x1024", "1536x1024", "1024x1536"],
            supported_qualities=["auto", "high", "medium", "low"],
            supported_formats=["png", "jpeg", "webp"],
            max_images_per_request=1,
            supports_style=False,  # Imagen uses different style approach
            supports_background=False,
            supports_compression=True,
            custom_parameters={
                "aspect_ratio": ["1:1", "3:4", "4:3", "9:16", "16:9"],
                "enhance_prompt": [True, False],
                "include_safety_attributes": [True, False],
            },
        ),
        "imagen-4-ultra": ModelCapability(
            model_id="imagen-4-ultra",
            supported_sizes=["1024x1024", "1536x1024", "1024x1536"],
            supported_qualities=["auto", "high", "medium", "low"],
            supported_formats=["png", "jpeg", "webp"],
            max_images_per_request=1,  # Imagen 4 Ultra can only generate
            # one image at a time
            supports_style=False,
            supports_background=False,
            supports_compression=True,
            custom_parameters={
                "aspect_ratio": ["1:1", "3:4", "4:3", "9:16", "16:9"],
                "enhance_prompt": [True, False],
                "include_safety_attributes": [True, False],
            },
        ),
    }

    # Size to aspect ratio mapping
    SIZE_TO_ASPECT_RATIO = {
        "1024x1024": "1:1",
        "1536x1024": "3:2",  # Closest to 16:9
        "1024x1536": "2:3",  # Closest to 9:16
        "auto": "1:1",
    }

    def __init__(self, config: ProviderConfig):
        super().__init__(config)

        # Use Gemini's OpenAI compatibility endpoint
        base_url = (
            config.base_url or "https://generativelanguage.googleapis.com/v1beta/"
        )

        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    def get_supported_models(self) -> set[str]:
        """Return set of supported Gemini model IDs."""
        return set(self.SUPPORTED_MODELS.keys())

    def get_model_capabilities(self, model_id: str) -> ModelCapability | None:
        """Get capabilities for a specific Gemini model."""
        return self.SUPPORTED_MODELS.get(model_id)

    def _convert_size_to_aspect_ratio(self, size: str) -> str:
        """Convert OpenAI size format to Gemini aspect ratio."""
        return self.SIZE_TO_ASPECT_RATIO.get(size, "1:1")

    def _convert_quality_to_gemini(self, quality: str) -> str:
        """Convert quality parameter to Gemini format."""
        quality_mapping = {
            "auto": "auto",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }
        return quality_mapping.get(quality, "auto")

    async def generate_image(
        self,
        model: str,
        prompt: str,
        quality: str = "auto",
        size: str = "1536x1024",
        style: str = "vivid",
        moderation: str = "auto",
        output_format: str = "png",
        compression: int = 100,
        background: str = "auto",
        n: int = 1,
        **kwargs,
    ) -> ImageResponse:
        """Generate image using Gemini's Images API via OpenAI compatibility."""

        # Validate model
        if model not in self.SUPPORTED_MODELS:
            raise ProviderError(
                f"Model '{model}' is not supported by Gemini provider",
                provider_name=self.name,
                error_code="UNSUPPORTED_MODEL",
            )

        capabilities = self.SUPPORTED_MODELS[model]

        # Build request parameters for Gemini API
        request_params = {
            "model": model,
            "prompt": prompt,
            "n": min(n, capabilities.max_images_per_request),
        }

        # Convert size to aspect ratio for Gemini
        aspect_ratio = self._convert_size_to_aspect_ratio(size)

        # Add Gemini-specific parameters
        gemini_params = {
            "quality": self._convert_quality_to_gemini(quality),
            "output_format": output_format,
            "aspect_ratio": aspect_ratio,
            "enhance_prompt": True,  # Enable prompt enhancement by default
            "include_safety_attributes": True,
        }

        # Add compression for JPEG/WebP
        if output_format in ["jpeg", "webp"] and compression < 100:
            gemini_params["compression_quality"] = compression

        # Note: Gemini doesn't support style/background like OpenAI
        # These parameters are ignored but logged
        if style != "vivid":
            self._logger.info(
                f"Style parameter '{style}' is not supported by Gemini, ignoring"
            )
        if background != "auto":
            self._logger.info(
                f"Background parameter '{background}' is not supported by Gemini, "
                "ignoring"
            )

        request_params.update(gemini_params)

        try:
            self._logger.info(f"Generating image with Gemini model {model}")
            self._logger.debug(f"Request parameters: {request_params}")

            # Use OpenAI client with Gemini endpoint
            response = await self.client.images.generate(**request_params)

            # Process response - Gemini returns base64 data
            if hasattr(response.data[0], "b64_json") and response.data[0].b64_json:
                image_bytes = base64.b64decode(response.data[0].b64_json)
            else:
                raise ProviderError(
                    "Gemini response does not contain base64 data",
                    provider_name=self.name,
                    error_code="INVALID_RESPONSE",
                )

            # Build metadata
            metadata = {
                "model": model,
                "prompt": prompt,
                "original_size": size,
                "aspect_ratio": aspect_ratio,
                "quality": quality,
                "output_format": output_format,
                "provider": self.name,
                "created_at": getattr(response, "created", None),
                "enhanced_prompt": gemini_params.get("enhance_prompt", False),
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
            self._logger.error(f"Error generating image with Gemini: {e}")
            raise ProviderError(
                f"Gemini image generation failed: {str(e)}",
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
        """Edit image using Gemini's Images API."""

        # Note: Image editing support depends on Gemini's capabilities
        # This is a placeholder implementation
        raise ProviderError(
            "Image editing is not yet supported by Gemini provider",
            provider_name=self.name,
            error_code="FEATURE_NOT_SUPPORTED",
        )

    def validate_model_params(
        self, model: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate and normalize parameters for Gemini models."""

        # First do base validation
        params = super().validate_model_params(model, params)

        capabilities = self.get_model_capabilities(model)
        if not capabilities:
            raise ProviderError(
                f"No capabilities found for model '{model}'",
                provider_name=self.name,
                error_code="MISSING_CAPABILITIES",
            )

        # Gemini-specific validations

        # Convert size to aspect ratio and validate
        if "size" in params:
            aspect_ratio = self._convert_size_to_aspect_ratio(params["size"])
            if aspect_ratio not in capabilities.custom_parameters.get(
                "aspect_ratio", []
            ):
                # Use default aspect ratio
                params["size"] = "1024x1024"  # Maps to 1:1
                self._logger.warning(
                    "Aspect ratio not supported, using 1:1 (1024x1024)"
                )

        # Validate image count for Imagen 4 Ultra
        if model == "imagen-4-ultra" and params.get("n", 1) > 1:
            params["n"] = 1
            self._logger.warning(
                "Imagen 4 Ultra only supports generating 1 image at a time"
            )

        # Remove unsupported parameters
        unsupported_params = ["style", "background", "moderation"]
        for param in unsupported_params:
            if param in params:
                self._logger.debug(
                    f"Removing unsupported parameter '{param}' for Gemini"
                )
                del params[param]

        return params

    def estimate_cost(
        self, model: str, prompt: str, image_count: int = 1
    ) -> dict[str, Any]:
        """Estimate cost for Gemini image generation."""

        # Gemini/Imagen pricing (as of 2024)
        pricing = {
            "imagen-4": {
                "cost_per_image": 0.04,  # $0.04 per image
            },
            "imagen-4-ultra": {
                "cost_per_image": 0.08,  # Higher cost for Ultra model (estimated)
            },
            "imagen-3": {
                "cost_per_image": 0.02,  # Lower cost for older model (estimated)
            },
        }

        if model not in pricing:
            return super().estimate_cost(model, prompt, image_count)

        model_pricing = pricing[model]
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
