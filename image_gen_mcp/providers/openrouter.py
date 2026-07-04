"""OpenRouter provider for image generation via the dedicated Images API.

OpenRouter provides a dedicated image generation endpoint at POST /api/v1/images
(launched June 2026). This provider targets that endpoint exclusively.

Reference: https://openrouter.ai/docs/guides/overview/multimodal/image-generation
"""

import base64
import logging
from typing import Any

import httpx

from .base import (
    ImageResponse,
    LLMProvider,
    ModelCapability,
    ProviderConfig,
    ProviderError,
)

logger = logging.getLogger(__name__)

_OPENROUTER_MODEL_SLUGS: dict[str, str] = {
    "gpt-5.4-image-2": "openai/gpt-5.4-image-2",
    "gpt-5-image": "openai/gpt-5-image",
    "gpt-5-image-mini": "openai/gpt-5-image-mini",
}

_SIZE_TO_ASPECT_RATIO: dict[str, str] = {
    "1024x1024": "1:1",
    "1536x1024": "3:2",
    "1024x1536": "2:3",
    "3840x2160": "16:9",
}

_GPT_54_IMAGE_2_CAPABILITY = dict(
    supported_sizes=["auto", "1024x1024", "1536x1024", "1024x1536", "3840x2160"],
    supported_qualities=["auto", "high", "medium", "low"],
    supported_formats=["png", "jpeg", "webp"],
    max_images_per_request=10,
    supports_style=False,
    supports_background=True,
    supports_compression=True,
    supports_custom_sizes=True,
    size_constraints={
        "multiple_of": 16,
        "max_edge": 3840,
        "max_aspect_ratio": 3.0,
        "min_pixels": 655_360,
        "max_pixels": 8_294_400,
    },
    custom_parameters={
        "background": ["auto", "transparent", "opaque"],
    },
)

_GPT_IMAGE_CAPABILITY = dict(
    supported_sizes=["auto", "1024x1024", "1536x1024", "1024x1536"],
    supported_qualities=["auto", "high", "medium", "low"],
    supported_formats=["png", "jpeg", "webp"],
    max_images_per_request=10,
    supports_style=False,
    supports_background=True,
    supports_compression=True,
    custom_parameters={
        "background": ["auto", "transparent", "opaque"],
    },
)


def _size_to_aspect_ratio(size: str) -> str | None:
    normalized = size.strip().lower() if isinstance(size, str) else ""
    return _SIZE_TO_ASPECT_RATIO.get(normalized)


def _build_request_body(
    slug: str,
    prompt: str,
    quality: str,
    size: str,
    output_format: str,
    compression: int,
    background: str,
    n: int,
    input_references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": slug,
        "prompt": prompt,
        "n": n,
    }

    if size and size != "auto":
        ratio = _size_to_aspect_ratio(size)
        if ratio:
            body["aspect_ratio"] = ratio
        else:
            body["size"] = size

    if quality and quality != "auto":
        body["quality"] = quality

    if output_format and output_format != "auto":
        body["output_format"] = output_format

    if background and background != "auto":
        body["background"] = background

    if compression < 100 and output_format in ("jpeg", "webp"):
        body["output_compression"] = compression

    if input_references:
        body["input_references"] = input_references

    return body


def _image_bytes_from_response(
    data: dict[str, Any], provider_name: str
) -> tuple[bytes, str]:
    images = data.get("data", [])
    if not images or not images[0].get("b64_json"):
        raise ProviderError(
            "No image data in OpenRouter response",
            provider_name=provider_name,
            error_code="INVALID_RESPONSE",
        )
    raw = images[0]["b64_json"]
    media_type = images[0].get("media_type", "image/png")
    fmt = media_type.split("/")[-1].lower() if "/" in media_type else "png"
    return base64.b64decode(raw), fmt


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider — uses the dedicated Images API (POST /api/v1/images).

    Reference: https://openrouter.ai/docs/guides/overview/multimodal/image-generation
    """

    SUPPORTED_MODELS = {
        "gpt-5.4-image-2": ModelCapability(
            model_id="gpt-5.4-image-2",
            **_GPT_54_IMAGE_2_CAPABILITY,
        ),
        "gpt-5-image": ModelCapability(
            model_id="gpt-5-image",
            **_GPT_IMAGE_CAPABILITY,
        ),
        "gpt-5-image-mini": ModelCapability(
            model_id="gpt-5-image-mini",
            **_GPT_IMAGE_CAPABILITY,
        ),
    }

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        headers: dict[str, str] = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        if config.custom_headers:
            headers.update(config.custom_headers)
        self._base_url = (config.base_url or "https://openrouter.ai/api/v1").rstrip(
            "/"
        )
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=httpx.Timeout(config.timeout),
        )

    async def close(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

    def _model_slug(self, model: str) -> str:
        slug = _OPENROUTER_MODEL_SLUGS.get(model)
        if not slug:
            raise ProviderError(
                f"Model '{model}' is not supported by OpenRouter provider",
                provider_name=self.name,
                error_code="UNSUPPORTED_MODEL",
            )
        return slug

    def get_supported_models(self) -> set[str]:
        return set(self.SUPPORTED_MODELS.keys())

    def get_model_capabilities(self, model_id: str) -> ModelCapability | None:
        return self.SUPPORTED_MODELS.get(model_id)

    def validate_model_params(
        self, model: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        return super().validate_model_params(model, params)

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
        if model not in self.SUPPORTED_MODELS:
            raise ProviderError(
                f"Model '{model}' is not supported by OpenRouter provider",
                provider_name=self.name,
                error_code="UNSUPPORTED_MODEL",
            )

        slug = self._model_slug(model)
        body = _build_request_body(
            slug=slug,
            prompt=prompt,
            quality=quality,
            size=size,
            output_format=output_format,
            compression=compression,
            background=background,
            n=min(n, self.SUPPORTED_MODELS[model].max_images_per_request),
        )

        try:
            self._logger.info(f"Generating image with OpenRouter model {model}")
            resp = await self._client.post("/images", json=body)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise ProviderError(
                f"OpenRouter API error: {e.response.text[:500]}",
                provider_name=self.name,
                error_code="GENERATION_FAILED",
            ) from e
        except Exception as e:
            raise ProviderError(
                f"OpenRouter image generation failed: {e}",
                provider_name=self.name,
                error_code="GENERATION_FAILED",
            ) from e

        image_bytes, actual_format = _image_bytes_from_response(data, self.name)

        metadata: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "output_format": actual_format,
            "provider": self.name,
            "created_at": data.get("created"),
        }
        if data.get("usage"):
            metadata["usage"] = {
                "total_tokens": data["usage"].get("total_tokens"),
                "input_tokens": data["usage"].get("prompt_tokens"),
                "output_tokens": data["usage"].get("completion_tokens"),
            }

        return ImageResponse(image_data=image_bytes, metadata=metadata)

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
        if model not in self.SUPPORTED_MODELS:
            raise ProviderError(
                f"Model '{model}' is not supported by OpenRouter provider",
                provider_name=self.name,
                error_code="UNSUPPORTED_MODEL",
            )

        if mask_data is not None:
            raise ProviderError(
                "Mask-based editing is not supported by the OpenRouter provider",
                provider_name=self.name,
                error_code="FEATURE_NOT_SUPPORTED",
            )

        if isinstance(image_data, bytes):
            b64 = base64.b64encode(image_data).decode("ascii")
            image_url = f"data:image/png;base64,{b64}"
        else:
            image_url = image_data

        input_references = [
            {"type": "image_url", "image_url": {"url": image_url}}
        ]

        slug = self._model_slug(model)
        body = _build_request_body(
            slug=slug,
            prompt=prompt,
            quality=quality,
            size=size,
            output_format=output_format,
            compression=compression,
            background=background,
            n=min(n, self.SUPPORTED_MODELS[model].max_images_per_request),
            input_references=input_references,
        )

        try:
            self._logger.info(f"Editing image with OpenRouter model {model}")
            resp = await self._client.post("/images", json=body)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise ProviderError(
                f"OpenRouter API error: {e.response.text[:500]}",
                provider_name=self.name,
                error_code="EDITING_FAILED",
            ) from e
        except Exception as e:
            raise ProviderError(
                f"OpenRouter image editing failed: {e}",
                provider_name=self.name,
                error_code="EDITING_FAILED",
            ) from e

        image_bytes, actual_format = _image_bytes_from_response(data, self.name)

        metadata: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "output_format": actual_format,
            "provider": self.name,
            "operation": "edit",
            "created_at": data.get("created"),
        }

        return ImageResponse(image_data=image_bytes, metadata=metadata)

    async def check_health(self) -> dict[str, Any]:
        try:
            resp = await self._client.get("/images/models")
            resp.raise_for_status()
            models_data = resp.json().get("data", [])
            api_ids = {m["id"] for m in models_data if isinstance(m, dict)}
        except Exception as e:
            self._logger.warning(f"OpenRouter health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

        available = []
        missing = []
        for friendly, slug in _OPENROUTER_MODEL_SLUGS.items():
            if slug in api_ids:
                available.append(friendly)
            else:
                missing.append(friendly)

        if not available:
            return {
                "status": "unhealthy",
                "error": "No configured image models available via OpenRouter",
                "models_available": [],
            }
        result: dict[str, Any] = {"status": "healthy", "models_available": available}
        if missing:
            result["warning"] = f"Models not found: {', '.join(missing)}"
        return result

    def estimate_cost(
        self,
        model: str,
        prompt: str,
        image_count: int = 1,
        quality: str = "auto",
        size: str = "1024x1024",
    ) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": model,
            "estimated_cost_usd": 0.0,
            "currency": "USD",
            "note": "Check openrouter.ai/models for current pricing",
            "breakdown": {"total_images": image_count},
        }
