"""Provider registry for managing multiple LLM providers."""

import asyncio
import logging
from typing import Any

from .base import LLMProvider, ProviderError

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for managing LLM providers and model routing."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._model_to_provider: dict[str, str] = {}
        self._registry_lock = asyncio.Lock()

    async def register_provider(self, provider: LLMProvider) -> None:
        """Register a new provider.

        Args:
            provider: The provider instance to register

        Raises:
            ProviderError: If provider registration fails
        """
        if not provider.is_available():
            logger.warning(
                f"Provider {provider.name} is not available, skipping registration"
            )
            return

        async with self._registry_lock:
            # Check for conflicting provider names
            if provider.name in self._providers:
                raise ProviderError(
                    f"Provider '{provider.name}' is already registered",
                    provider_name=provider.name,
                    error_code="DUPLICATE_PROVIDER",
                )

            # Register the provider
            self._providers[provider.name] = provider

            # Map all supported models to this provider
            supported_models = provider.get_supported_models()
            for model_id in supported_models:
                if model_id in self._model_to_provider:
                    existing_provider = self._model_to_provider[model_id]
                    logger.warning(
                        f"Model '{model_id}' is already registered with provider "
                        f"'{existing_provider}'. "
                        f"Overriding with '{provider.name}'"
                    )

                self._model_to_provider[model_id] = provider.name

            logger.info(
                f"Registered provider '{provider.name}' with "
                f"{len(supported_models)} models"
            )

    async def unregister_provider(self, provider_name: str) -> None:
        """Unregister a provider.

        Args:
            provider_name: Name of the provider to unregister
        """
        async with self._registry_lock:
            if provider_name not in self._providers:
                logger.warning(f"Provider '{provider_name}' is not registered")
                return

            self._providers.pop(provider_name)

            # Remove model mappings
            models_to_remove = []
            for model_id, mapped_provider in self._model_to_provider.items():
                if mapped_provider == provider_name:
                    models_to_remove.append(model_id)

            for model_id in models_to_remove:
                del self._model_to_provider[model_id]

            logger.info(
                f"Unregistered provider '{provider_name}' and "
                f"{len(models_to_remove)} models"
            )

    def get_provider(self, provider_name: str) -> LLMProvider | None:
        """Get a provider by name.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(provider_name)

    def get_provider_for_model(self, model_id: str) -> LLMProvider | None:
        """Get the provider that supports a specific model.

        Args:
            model_id: The model ID to look up

        Returns:
            Provider instance or None if model is not supported
        """
        provider_name = self._model_to_provider.get(model_id)
        if provider_name:
            return self._providers.get(provider_name)
        return None

    def get_all_providers(self) -> list[LLMProvider]:
        """Get all registered providers.

        Returns:
            List of all registered providers
        """
        return list(self._providers.values())

    def get_available_providers(self) -> list[LLMProvider]:
        """Get all available (enabled and properly configured) providers.

        Returns:
            List of available providers
        """
        return [
            provider for provider in self._providers.values() if provider.is_available()
        ]

    def get_supported_models(self) -> set[str]:
        """Get all supported models across all providers.

        Returns:
            Set of all supported model IDs
        """
        return set(self._model_to_provider.keys())

    def get_models_by_provider(self) -> dict[str, set[str]]:
        """Get models grouped by provider.

        Returns:
            Dict mapping provider names to their supported models
        """
        result = {}
        for provider_name, provider in self._providers.items():
            result[provider_name] = provider.get_supported_models()
        return result

    def is_model_supported(self, model_id: str) -> bool:
        """Check if a model is supported by any provider.

        Args:
            model_id: The model ID to check

        Returns:
            True if the model is supported
        """
        return model_id in self._model_to_provider

    def get_model_info(self, model_id: str) -> dict[str, Any] | None:
        """Get detailed information about a model.

        Args:
            model_id: The model ID

        Returns:
            Dict containing model information or None if not found
        """
        provider = self.get_provider_for_model(model_id)
        if not provider:
            return None

        capabilities = provider.get_model_capabilities(model_id)
        if not capabilities:
            return None

        return {
            "model_id": model_id,
            "provider": provider.name,
            "capabilities": capabilities,
            "is_available": provider.is_available(),
        }

    def validate_model_request(
        self, model_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate a model request and normalize parameters.

        Args:
            model_id: The model ID
            params: Request parameters

        Returns:
            Normalized parameters

        Raises:
            ProviderError: If validation fails
        """
        provider = self.get_provider_for_model(model_id)
        if not provider:
            raise ProviderError(
                f"Model '{model_id}' is not supported by any registered provider",
                provider_name="registry",
                error_code="UNSUPPORTED_MODEL",
            )

        if not provider.is_available():
            raise ProviderError(
                f"Provider '{provider.name}' for model '{model_id}' is not available",
                provider_name=provider.name,
                error_code="PROVIDER_UNAVAILABLE",
            )

        return provider.validate_model_params(model_id, params)

    def get_default_model(self, provider_name: str | None = None) -> str | None:
        """Get a default model, optionally from a specific provider.

        Args:
            provider_name: Optional provider name to get default from

        Returns:
            Default model ID or None if no models available
        """
        if provider_name:
            provider = self.get_provider(provider_name)
            if provider and provider.is_available():
                models = provider.get_supported_models()
                return next(iter(models)) if models else None
        else:
            # Get default from any available provider
            for provider in self.get_available_providers():
                models = provider.get_supported_models()
                if models:
                    return next(iter(models))

        return None

    def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dict containing registry statistics
        """
        available_providers = self.get_available_providers()

        return {
            "total_providers": len(self._providers),
            "available_providers": len(available_providers),
            "total_models": len(self._model_to_provider),
            "providers": {
                name: {
                    "available": provider.is_available(),
                    "models": list(provider.get_supported_models()),
                }
                for name, provider in self._providers.items()
            },
        }

    def __str__(self) -> str:
        return (
            f"ProviderRegistry(providers={len(self._providers)}, "
            f"models={len(self._model_to_provider)})"
        )

    def __repr__(self) -> str:
        return (
            f"ProviderRegistry(providers={list(self._providers.keys())}, "
            f"models={len(self._model_to_provider)})"
        )
