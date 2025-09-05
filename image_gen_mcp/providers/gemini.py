"""Gemini provider implementation using Google's native Generative AI API."""

import base64
import json
import logging
import os
from typing import Any

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2 import service_account

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
        # NOTE: 'imagen-4.0-generate-preview-06-06' is a preview version
        # and may be deprecated in the future.
        "imagen_4": ModelCapability(
            model_id="imagen-4.0-generate-preview-06-06",
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
        "imagen-3": ModelCapability(
            model_id="imagen-3.0-generate-002",
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

        # For Vertex AI (Imagen models), we need service account authentication
        self.credentials_path = config.api_key  # Path to JSON file
        self.base_url = (
            config.base_url or "https://us-central1-aiplatform.googleapis.com/v1"
        )
        self.timeout = config.timeout
        self.max_retries = config.max_retries

        # Load service account credentials with path validation
        # Resolve and validate the credentials file path to prevent
        # path traversal attacks
        resolved_path = os.path.abspath(self.credentials_path)

        # Define allowed directories for credential files
        # (project directory and common locations)
        project_dir = os.path.abspath(os.getcwd())
        allowed_dirs = [
            project_dir,  # Current project directory
            os.path.expanduser("~/.config/gcloud"),  # Standard gcloud config location
            os.path.expanduser("~/.google"),  # Alternative Google config location
        ]

        # Check if the resolved path is within allowed directories
        # using os.path.commonpath
        path_is_allowed = any(
            resolved_path.startswith(os.path.abspath(allowed_dir) + os.sep)
            for allowed_dir in allowed_dirs
        )
        if not path_is_allowed:
            raise ValueError(
                f"Credentials file path is not in allowed directories: "
                f"{resolved_path}. Allowed directories: {allowed_dirs}"
            )

        if not os.path.exists(resolved_path):
            raise ValueError(
                f"Service account file not found: {resolved_path}. "
                "Please ensure the service account JSON file exists and "
                "the path is correct."
            )

        # Verify it's actually a file (not a directory)
        if not os.path.isfile(resolved_path):
            raise ValueError(
                f"Credentials path is not a file: {resolved_path}"
            )

        self.credentials = service_account.Credentials.from_service_account_file(
            resolved_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        # Extract project ID from credentials using the validated path
        try:
            # Check file size before reading to prevent memory exhaustion
            max_file_size = 1024 * 1024  # 1 MB limit for credentials file
            file_size = os.path.getsize(resolved_path)
            if file_size > max_file_size:
                raise ValueError(
                    f"Service account file '{resolved_path}' is too large "
                    f"({file_size} bytes). Maximum allowed size is "
                    f"{max_file_size} bytes. Refusing to load potentially "
                    "maliciously large file."
                )

            with open(resolved_path, encoding='utf-8') as f:
                try:
                    cred_data = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Invalid JSON format in service account file "
                        f"'{resolved_path}': {e}. Please ensure the file "
                        "contains valid JSON credentials."
                    ) from e

                self.project_id = cred_data.get('project_id')
                if not self.project_id:
                    available_keys = (
                        list(cred_data.keys()) if isinstance(cred_data, dict)
                        else "N/A"
                    )
                    raise ValueError(
                        f"'project_id' field not found in service account file "
                        f"'{resolved_path}'. Available fields: {available_keys}. "
                        "Please ensure this is a valid Google Cloud service "
                        "account JSON file."
                    )

        except OSError as e:
            raise ValueError(
                f"Unable to read service account file '{resolved_path}': {e}. "
                "Please check file permissions and ensure the file is accessible."
            ) from e
        except PermissionError as e:
            raise ValueError(
                f"Permission denied reading service account file "
                f"'{resolved_path}': {e}. Please check file permissions."
            ) from e
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
        **kwargs,
    ) -> ImageResponse:
        """Generate image using Google's native Generative AI API."""

        # Accept both "imagen-4" and "imagen_4" for backward compatibility
        normalized_model = model.replace("-", "_")
        if normalized_model not in self.SUPPORTED_MODELS:
            raise ProviderError(
                f"Model '{model}' is not supported by Gemini provider",
                provider_name=self.name,
                error_code="UNSUPPORTED_MODEL",
            )

        # Build request for Vertex AI Imagen API
        request_body = {
            "instances": [{
                "prompt": prompt
            }],
            "parameters": {}
        }

        # Add aspect ratio if size is specified
        if size != "auto":
            aspect_ratio = self._convert_size_to_aspect_ratio(size)
            request_body["parameters"]["aspectRatio"] = aspect_ratio

        # Use the actual model ID and Vertex AI endpoint
        actual_model_id = self.SUPPORTED_MODELS[normalized_model].model_id
        url = (
            f"{self.base_url}/projects/{self.project_id}/locations/us-central1/"
            f"publishers/google/models/{actual_model_id}:predict"
        )

        # Get fresh access token
        self.credentials.refresh(Request())
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.credentials.token}"
        }

        try:
            self._logger.info(f"Generating image with Gemini model {model}")
            self._logger.debug(f"Request URL: {url}")
            self._logger.debug(f"Request body: {request_body}")

            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url, json=request_body, headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ProviderError(
                            f"Gemini API error {response.status}: {error_text}",
                            provider_name=self.name,
                            error_code="API_ERROR",
                        )

                    response_data = await response.json()

                    # Extract image data from Imagen predict response
                    if "predictions" not in response_data:
                        raise ProviderError(
                            "Missing 'predictions' field in Imagen response",
                            provider_name=self.name,
                            error_code="INVALID_RESPONSE",
                        )

                    predictions = response_data["predictions"]
                    if not isinstance(predictions, list):
                        raise ProviderError(
                            f"'predictions' field is not a list but "
                            f"{type(predictions).__name__}",
                            provider_name=self.name,
                            error_code="INVALID_RESPONSE",
                        )

                    if len(predictions) == 0:
                        raise ProviderError(
                            "Empty predictions list in Imagen response",
                            provider_name=self.name,
                            error_code="INVALID_RESPONSE",
                        )

                    prediction = predictions[0]

                    # Extract image data from Vertex AI Imagen response
                    # Expected format: {"bytesBase64Encoded": "base64_string"}
                    # Documentation: https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/imagen
                    # Fail fast if API format changes to detect issues immediately
                    if not isinstance(prediction, dict):
                        prediction_type = type(prediction).__name__
                        raise ProviderError(
                            f"Unexpected prediction format. Expected dict but got "
                            f"{prediction_type}. This indicates a Vertex AI API "
                            "change that requires code updates.",
                            provider_name=self.name,
                            error_code="INVALID_RESPONSE",
                        )
                    if "bytesBase64Encoded" not in prediction:
                        available_keys = list(prediction.keys())
                        raise ProviderError(
                            f"Missing expected 'bytesBase64Encoded' field in Imagen "
                            f"response. Available fields: {available_keys}. This "
                            "indicates a Vertex AI API change - please update the "
                            "integration.",
                            provider_name=self.name,
                            error_code="INVALID_RESPONSE",
                        )
                    image_data = prediction["bytesBase64Encoded"]
                    if not image_data:
                        raise ProviderError(
                            "Empty image data in 'bytesBase64Encoded' field",
                            provider_name=self.name,
                            error_code="INVALID_RESPONSE",
                        )

                    # Decode base64 image data
                    image_bytes = base64.b64decode(image_data)

                    # Build metadata
                    metadata = {
                        "model": model,
                        "prompt": prompt,
                        "size": size,
                        "quality": quality,
                        "provider": self.name,
                        "created_at": None,  # Gemini doesn't provide timestamp
                    }

                    return ImageResponse(
                        image_data=image_bytes,
                        metadata=metadata,
                        provider_response=response_data,
                    )

        except aiohttp.ClientError as e:
            self._logger.error(f"Network error with Gemini: {e}")
            raise ProviderError(
                f"Gemini network error: {str(e)}",
                provider_name=self.name,
                error_code="NETWORK_ERROR",
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
            "imagen_4": {
                "cost_per_image": 0.04,  # Higher cost for latest model (estimated)
            },
            "imagen_3": {
                "cost_per_image": 0.02,  # Lower cost for older model (estimated)
            },
        }

        # Normalize model name for lookup
        normalized_model = model.replace("-", "_")
        if normalized_model not in pricing:
            return super().estimate_cost(model, prompt, image_count)

        model_pricing = pricing[normalized_model]
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
