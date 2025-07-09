"""Base classes for LLM provider abstraction."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    
    def __init__(self, message: str, provider_name: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.provider_name = provider_name
        self.error_code = error_code
        
    def __str__(self) -> str:
        base_msg = f"[{self.provider_name}] {super().__str__()}"
        if self.error_code:
            base_msg += f" (Code: {self.error_code})"
        return base_msg


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    api_key: str
    base_url: Optional[str] = None
    organization: Optional[str] = None
    timeout: float = 300.0
    max_retries: int = 3
    enabled: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class ImageResponse:
    """Standardized response format for image generation."""
    image_data: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)
    provider_response: Optional[Dict[str, Any]] = None
    
    
@dataclass
class ModelCapability:
    """Model capability information."""
    model_id: str
    supported_sizes: List[str]
    supported_qualities: List[str]
    supported_formats: List[str]
    max_images_per_request: int = 1
    supports_style: bool = False
    supports_background: bool = False
    supports_compression: bool = False
    custom_parameters: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()
        self._logger = logging.getLogger(f"{__name__}.{self.name}")
        
    @abstractmethod
    def get_supported_models(self) -> Set[str]:
        """Return set of supported model IDs."""
        pass
        
    @abstractmethod
    def get_model_capabilities(self, model_id: str) -> Optional[ModelCapability]:
        """Get capabilities for a specific model."""
        pass
        
    @abstractmethod
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
        **kwargs
    ) -> ImageResponse:
        """Generate image using the provider's API."""
        pass
        
    @abstractmethod
    async def edit_image(
        self,
        model: str,
        image_data: Union[str, bytes],
        prompt: str,
        mask_data: Optional[Union[str, bytes]] = None,
        quality: str = "auto",
        size: str = "auto",
        output_format: str = "png",
        compression: int = 100,
        background: str = "auto",
        n: int = 1,
        **kwargs
    ) -> ImageResponse:
        """Edit image using the provider's API."""
        pass
        
    def validate_model_params(self, model: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize parameters for a specific model.
        
        Args:
            model: Model ID to validate against
            params: Parameters to validate
            
        Returns:
            Normalized parameters
            
        Raises:
            ProviderError: If model is not supported or parameters are invalid
        """
        if model not in self.get_supported_models():
            raise ProviderError(
                f"Model '{model}' is not supported by {self.name} provider",
                provider_name=self.name,
                error_code="UNSUPPORTED_MODEL"
            )
            
        capabilities = self.get_model_capabilities(model)
        if not capabilities:
            raise ProviderError(
                f"No capabilities found for model '{model}'",
                provider_name=self.name,
                error_code="MISSING_CAPABILITIES"
            )
            
        # Validate size parameter
        if "size" in params and params["size"] not in capabilities.supported_sizes:
            self._logger.warning(
                f"Size '{params['size']}' not in supported sizes {capabilities.supported_sizes} for model {model}. Using default."
            )
            params["size"] = capabilities.supported_sizes[0]
            
        # Validate quality parameter
        if "quality" in params and params["quality"] not in capabilities.supported_qualities:
            self._logger.warning(
                f"Quality '{params['quality']}' not in supported qualities {capabilities.supported_qualities} for model {model}. Using default."
            )
            params["quality"] = capabilities.supported_qualities[0]
            
        # Validate format parameter
        if "output_format" in params and params["output_format"] not in capabilities.supported_formats:
            self._logger.warning(
                f"Format '{params['output_format']}' not in supported formats {capabilities.supported_formats} for model {model}. Using default."
            )
            params["output_format"] = capabilities.supported_formats[0]
            
        # Validate number of images
        if "n" in params and params["n"] > capabilities.max_images_per_request:
            self._logger.warning(
                f"Requested {params['n']} images, but model {model} supports max {capabilities.max_images_per_request}. Adjusting."
            )
            params["n"] = capabilities.max_images_per_request
            
        return params
        
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        return self.config.enabled and bool(self.config.api_key)
        
    def estimate_cost(self, model: str, prompt: str, image_count: int = 1) -> Dict[str, Any]:
        """Estimate cost for image generation. Override in subclasses for provider-specific pricing."""
        return {
            "provider": self.name,
            "model": model,
            "estimated_cost_usd": 0.0,
            "currency": "USD",
            "breakdown": {
                "per_image": 0.0,
                "total_images": image_count,
                "base_cost": 0.0,
            }
        }
        
    def __str__(self) -> str:
        return f"{self.name.title()}Provider(enabled={self.config.enabled})"
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self.config.enabled})"