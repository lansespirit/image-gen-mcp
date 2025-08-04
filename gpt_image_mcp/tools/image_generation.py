"""Image generation tool implementation."""

import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from ..config.settings import Settings
from ..providers.base import ProviderConfig, ProviderError
from ..providers.gemini import GeminiProvider
from ..providers.openai import OpenAIProvider
from ..providers.registry import ProviderRegistry
from ..storage.manager import ImageStorageManager
from ..types.enums import (
    BackgroundType,
    ImageQuality,
    ImageSize,
    ImageStyle,
    ModerationLevel,
    OutputFormat,
)
from ..utils.cache import CacheManager
from ..utils.path_utils import build_image_url_path

logger = logging.getLogger(__name__)


class ImageGenerationTool:
    """Tool for generating images using multiple LLM providers."""

    def __init__(
        self,
        storage_manager: ImageStorageManager,
        cache_manager: CacheManager,
        settings: Settings,
        openai_client=None,
    ):
        """
        Args:
            storage_manager: ImageStorageManager instance.
            cache_manager: CacheManager instance.
            settings: Settings instance (must have .providers, .images, etc.).
            openai_client: Optional OpenAI client.
        """
        self.settings = settings
        self.storage_manager = storage_manager
        self.cache_manager = cache_manager
        self.provider_registry = ProviderRegistry()
        self.openai_client = openai_client
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize and register all available providers."""
        # Initialize OpenAI provider
        openai_provider = getattr(self.settings.providers, "openai", None)
        if openai_provider and openai_provider.enabled and openai_provider.api_key:
            try:
                openai_config = ProviderConfig(
                    api_key=self.settings.providers.openai.api_key,
                    organization=self.settings.providers.openai.organization,
                    base_url=self.settings.providers.openai.base_url,
                    timeout=self.settings.providers.openai.timeout,
                    max_retries=self.settings.providers.openai.max_retries,
                    enabled=self.settings.providers.openai.enabled,
                )
                openai_provider = OpenAIProvider(openai_config)
                # Register provider asynchronously - we'll handle this later
                self._register_provider_async(openai_provider)
                logger.info("OpenAI provider initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")

        # Initialize Gemini provider
        gemini_provider = getattr(self.settings.providers, "gemini", None)
        if gemini_provider and gemini_provider.enabled and gemini_provider.api_key:
            try:
                gemini_config = ProviderConfig(
                    api_key=self.settings.providers.gemini.api_key,
                    base_url=self.settings.providers.gemini.base_url,
                    timeout=self.settings.providers.gemini.timeout,
                    max_retries=self.settings.providers.gemini.max_retries,
                    enabled=self.settings.providers.gemini.enabled,
                )
                gemini_provider = GeminiProvider(gemini_config)

                # Register provider asynchronously - we'll handle this later
                self._register_provider_async(gemini_provider)
                logger.info("Gemini provider initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize Gemini provider: {e}")

    def _register_provider_async(self, provider) -> None:
        """Store provider for async registration later."""
        if not hasattr(self, "_pending_providers"):
            self._pending_providers = []
        self._pending_providers.append(provider)

    async def _ensure_providers_registered(self) -> None:
        """Ensure all providers are registered."""
        if hasattr(self, "_pending_providers"):
            for provider in self._pending_providers:
                try:
                    await self.provider_registry.register_provider(provider)
                except Exception as e:
                    logger.error(f"Failed to register provider {provider.name}: {e}")
            # Clear pending providers after registration
            self._pending_providers = []

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
            from ..utils.path_utils import build_image_storage_path

            image_path = build_image_storage_path(
                Path(self.settings.storage.base_path), image_id, file_format
            )
            return f"file://{image_path.absolute()}"

    def _get_default_model(self) -> str:
        """Get the default model based on configuration and available providers."""
        # First try the configured default model
        configured_default = self.settings.images.default_model

        # Check if the configured default is available
        if self.provider_registry.is_model_supported(configured_default):
            return configured_default

        # If configured default is not available, try to find any available model
        available_models = self.provider_registry.get_supported_models()
        if available_models:
            # Return the first available model
            return next(iter(available_models))

        # If no models are available, return the configured default anyway
        # This will cause a proper error message later
        return configured_default

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        quality: ImageQuality | str = ImageQuality.AUTO,
        size: ImageSize | str = ImageSize.LANDSCAPE,
        style: ImageStyle | str = ImageStyle.VIVID,
        moderation: ModerationLevel | str = ModerationLevel.AUTO,
        output_format: OutputFormat | str = OutputFormat.PNG,
        compression: int = 100,
        background: BackgroundType | str = BackgroundType.AUTO,
    ) -> dict[str, Any]:
        """Generate an image from a text prompt using the specified or default model."""

        # Ensure providers are registered
        await self._ensure_providers_registered()

        # Convert enums to string values for API calls
        quality_str = (
            quality.value if isinstance(quality, ImageQuality) else str(quality)
        )
        size_str = size.value if isinstance(size, ImageSize) else str(size)
        style_str = style.value if isinstance(style, ImageStyle) else str(style)
        moderation_str = (
            moderation.value
            if isinstance(moderation, ModerationLevel)
            else str(moderation)
        )
        output_format_str = (
            output_format.value
            if isinstance(output_format, OutputFormat)
            else str(output_format)
        )
        background_str = (
            background.value
            if isinstance(background, BackgroundType)
            else str(background)
        )

        # Determine which model to use
        target_model = model or self._get_default_model()

        # Get the provider for this model
        provider = self.provider_registry.get_provider_for_model(target_model)
        if not provider:
            available_models = list(self.provider_registry.get_supported_models())
            if not available_models:
                raise RuntimeError(
                    "No providers are available. Please ensure you have "
                    "configured at least one provider with a valid API key. "
                    "Set PROVIDERS__OPENAI__API_KEY for OpenAI or "
                    "PROVIDERS__GEMINI__API_KEY for Gemini."
                )
            else:
                raise RuntimeError(
                    f"No provider found for model '{target_model}'. "
                    f"Available models: {available_models}. "
                    "Use list_available_models() to see detailed information."
                )

        if not provider.is_available():
            raise RuntimeError(
                f"Provider '{provider.name}' for model '{target_model}' is not "
                "available or misconfigured"
            )

        # Generate task ID for tracking
        task_id = str(uuid.uuid4())

        # Build parameters for caching and validation
        params = {
            "prompt": prompt,
            "quality": quality_str,
            "size": size_str,
            "style": style_str,
            "moderation": moderation_str,
            "output_format": output_format_str,
            "compression": compression,
            "background": background_str,
            "model": target_model,
        }

        # Check cache first
        cached_result = await self.cache_manager.get_image_generation(**params)
        if cached_result:
            logger.info(f"Returning cached result for prompt: {prompt[:50]}...")
            return cached_result

        try:
            # Validate parameters for the specific model
            validated_params = self.provider_registry.validate_model_request(
                target_model, params
            )

            # Generate image using the provider
            logger.info(
                f"Generating image for task {task_id} using model {target_model} "
                f"via {provider.name}"
            )

            provider_response = await provider.generate_image(
                model=target_model,
                prompt=prompt,
                quality=validated_params.get("quality", quality_str),
                size=validated_params.get("size", size_str),
                style=validated_params.get("style", style_str),
                moderation=validated_params.get("moderation", moderation_str),
                output_format=validated_params.get("output_format", output_format_str),
                compression=validated_params.get("compression", compression),
                background=validated_params.get("background", background_str),
                n=1,
            )

            # Estimate cost
            cost_info = provider.estimate_cost(target_model, prompt, 1)

            # Prepare metadata
            metadata = {
                "task_id": task_id,
                "prompt": prompt,
                "model": target_model,
                "provider": provider.name,
                "parameters": validated_params,
                "cost_info": cost_info,
                "provider_metadata": provider_response.metadata,
            }

            # Save to local storage
            image_id, image_path = await self.storage_manager.save_image(
                image_data=provider_response.image_data,
                metadata=metadata,
                file_format=validated_params.get("output_format", output_format_str),
            )

            # Build image URL instead of base64 data
            image_url = self._build_image_url(
                image_id, validated_params.get("output_format", output_format_str)
            )

            # Prepare result
            result = {
                "task_id": task_id,
                "image_id": image_id,
                "image_url": image_url,
                "resource_uri": f"generated-images://{image_id}",
                "metadata": {
                    "model": target_model,
                    "provider": provider.name,
                    "size": validated_params.get("size", size_str),
                    "quality": validated_params.get("quality", quality_str),
                    "style": validated_params.get("style", style_str),
                    "moderation": validated_params.get("moderation", moderation_str),
                    "output_format": validated_params.get(
                        "output_format", output_format_str
                    ),
                    "background": validated_params.get("background", background_str),
                    "prompt": prompt,
                    "created_at": metadata.get("created_at"),
                    "cost_estimate": cost_info.get("estimated_cost_usd"),
                    "file_size_bytes": len(provider_response.image_data),
                    "dimensions": validated_params.get("size", size_str),
                    "format": validated_params.get(
                        "output_format", output_format_str
                    ).upper(),
                },
            }

            # Cache the result
            await self.cache_manager.set_image_generation(result, **params)

            logger.info(
                f"Successfully generated image {image_id} for task {task_id} "
                f"using {provider.name}"
            )
            return result

        except ProviderError as e:
            logger.error(f"Provider error for task {task_id}: {e}")
            raise RuntimeError(f"Image generation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating image for task {task_id}: {e}")
            raise RuntimeError(f"Image generation failed: {str(e)}")

    def get_supported_models(self) -> dict[str, Any]:
        """Get information about all supported models."""
        return self.provider_registry.get_registry_stats()

    def get_available_providers(self) -> list[str]:
        """Get list of available provider names."""
        return [
            provider.name
            for provider in self.provider_registry.get_available_providers()
        ]
