"""Unit tests for OpenRouter provider (dedicated Images API)."""

import base64

import pytest

from image_gen_mcp.providers.base import ProviderConfig, ProviderError
from image_gen_mcp.providers.openrouter import (
    OpenRouterProvider,
    _build_request_body,
    _image_bytes_from_response,
    _size_to_aspect_ratio,
)

_SAMPLE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA"
    "DUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
_SAMPLE_IMAGE_DATA_URL = f"data:image/png;base64,{_SAMPLE_B64}"
_SAMPLE_BYTES = base64.b64decode(_SAMPLE_B64)


def _fake_images_response(b64: str, media_type: str | None = None) -> dict:
    item: dict = {"b64_json": b64}
    if media_type:
        item["media_type"] = media_type
    return {
        "created": 1700000000,
        "data": [item],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 2000,
            "total_tokens": 2010,
        },
    }


@pytest.fixture
def provider():
    return OpenRouterProvider(
        ProviderConfig(api_key="sk-or-v1-test", enabled=True)
    )


class TestSizeToAspectRatio:
    def test_known_sizes(self):
        assert _size_to_aspect_ratio("1024x1024") == "1:1"
        assert _size_to_aspect_ratio("1536x1024") == "3:2"
        assert _size_to_aspect_ratio("1024x1536") == "2:3"
        assert _size_to_aspect_ratio("3840x2160") == "16:9"

    def test_normalized_whitespace(self):
        assert _size_to_aspect_ratio("  1024x1024  ") == "1:1"

    def test_unknown_size_returns_none(self):
        assert _size_to_aspect_ratio("2048x1152") is None
        assert _size_to_aspect_ratio("auto") is None
        assert _size_to_aspect_ratio("") is None


class TestImageBytesFromResponse:
    def test_valid_png(self):
        data = _fake_images_response(_SAMPLE_B64)
        image_bytes, fmt = _image_bytes_from_response(data, "openrouter")
        assert image_bytes == _SAMPLE_BYTES
        assert fmt == "png"

    def test_explicit_media_type_jpeg(self):
        data = _fake_images_response(_SAMPLE_B64, media_type="image/jpeg")
        _, fmt = _image_bytes_from_response(data, "openrouter")
        assert fmt == "jpeg"

    def test_svg_media_type(self):
        data = _fake_images_response(_SAMPLE_B64, media_type="image/svg+xml")
        _, fmt = _image_bytes_from_response(data, "openrouter")
        assert fmt == "svg+xml"

    def test_empty_data_raises(self):
        with pytest.raises(ProviderError, match="No image data"):
            _image_bytes_from_response({"data": []}, "openrouter")

    def test_missing_b64_raises(self):
        with pytest.raises(ProviderError, match="No image data"):
            _image_bytes_from_response(
                {"data": [{"b64_json": None}]}, "openrouter"
            )


class TestBuildRequestBody:
    def test_minimal(self):
        body = _build_request_body(
            slug="openai/gpt-5-image",
            prompt="a sunset",
            quality="auto",
            size="auto",
            output_format="auto",
            compression=100,
            background="auto",
            n=1,
        )
        assert body["model"] == "openai/gpt-5-image"
        assert body["prompt"] == "a sunset"
        assert body["n"] == 1
        assert "aspect_ratio" not in body
        assert "size" not in body
        assert "quality" not in body
        assert "output_format" not in body
        assert "background" not in body
        assert "output_compression" not in body

    def test_known_size_becomes_aspect_ratio(self):
        body = _build_request_body(
            slug="openai/gpt-5-image",
            prompt="test",
            quality="auto",
            size="1024x1024",
            output_format="auto",
            compression=100,
            background="auto",
            n=1,
        )
        assert body["aspect_ratio"] == "1:1"
        assert "size" not in body

    def test_unknown_size_passes_as_size(self):
        body = _build_request_body(
            slug="openai/gpt-5-image",
            prompt="test",
            quality="auto",
            size="2048x1152",
            output_format="auto",
            compression=100,
            background="auto",
            n=1,
        )
        assert body["size"] == "2048x1152"
        assert "aspect_ratio" not in body

    def test_quality_and_format(self):
        body = _build_request_body(
            slug="openai/gpt-5-image",
            prompt="test",
            quality="high",
            size="auto",
            output_format="jpeg",
            compression=100,
            background="auto",
            n=1,
        )
        assert body["quality"] == "high"
        assert body["output_format"] == "jpeg"

    def test_compression_for_lossy(self):
        body = _build_request_body(
            slug="openai/gpt-5-image",
            prompt="test",
            quality="auto",
            size="auto",
            output_format="jpeg",
            compression=80,
            background="auto",
            n=1,
        )
        assert body["output_compression"] == 80

    def test_compression_100_skipped(self):
        body = _build_request_body(
            slug="openai/gpt-5-image",
            prompt="test",
            quality="auto",
            size="auto",
            output_format="jpeg",
            compression=100,
            background="auto",
            n=1,
        )
        assert "output_compression" not in body

    def test_background_non_auto(self):
        body = _build_request_body(
            slug="openai/gpt-5-image",
            prompt="test",
            quality="auto",
            size="auto",
            output_format="png",
            compression=100,
            background="transparent",
            n=1,
        )
        assert body["background"] == "transparent"

    def test_input_references(self):
        refs = [{"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}]
        body = _build_request_body(
            slug="openai/gpt-5-image",
            prompt="edit this",
            quality="auto",
            size="auto",
            output_format="png",
            compression=100,
            background="auto",
            n=1,
            input_references=refs,
        )
        assert body["input_references"] == refs


class TestProviderInit:
    def test_creates_with_api_key(self):
        provider = OpenRouterProvider(
            ProviderConfig(api_key="sk-or-v1-test", enabled=True)
        )
        assert provider.is_available()

    def test_disabled_when_no_key(self):
        provider = OpenRouterProvider(
            ProviderConfig(api_key="", enabled=True)
        )
        assert not provider.is_available()

    def test_custom_headers_forwarded(self):
        provider = OpenRouterProvider(
            ProviderConfig(
                api_key="sk-or-v1-test",
                enabled=True,
                custom_headers={
                    "X-Title": "Test App",
                    "HTTP-Referer": "https://test.example",
                },
            )
        )
        assert "X-Title" in provider._client.headers
        assert "HTTP-Referer" in provider._client.headers


class TestModelRegistration:
    def test_supported_models(self):
        assert "gpt-5.4-image-2" in OpenRouterProvider.SUPPORTED_MODELS
        assert "gpt-5-image" in OpenRouterProvider.SUPPORTED_MODELS
        assert "gpt-5-image-mini" in OpenRouterProvider.SUPPORTED_MODELS

    def test_gpt_54_image_2_capabilities(self):
        cap = OpenRouterProvider.SUPPORTED_MODELS["gpt-5.4-image-2"]
        assert cap.supports_custom_sizes is True
        assert cap.supports_background is True
        assert cap.supports_compression is True
        assert cap.size_constraints is not None
        assert cap.size_constraints["max_edge"] == 3840
        assert "3840x2160" in cap.supported_sizes
        assert cap.max_images_per_request == 10

    def test_gpt_5_image_capabilities(self):
        cap = OpenRouterProvider.SUPPORTED_MODELS["gpt-5-image"]
        assert cap.supports_custom_sizes is False
        assert "auto" in cap.supported_sizes
        assert cap.max_images_per_request == 10

    def test_model_slug_raises_for_unknown(self, provider):
        with pytest.raises(ProviderError, match="not supported"):
            provider._model_slug("unknown-model")


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_successful_generation(self, provider: OpenRouterProvider):
        import httpx

        def handler(req):
            assert req.url.path.endswith("/images")
            body = req.content
            import json
            parsed = json.loads(body)
            assert parsed["model"] == "openai/gpt-5.4-image-2"
            assert parsed["prompt"] == "a sunset"
            assert "messages" not in parsed
            assert "modalities" not in parsed
            assert "image_config" not in parsed
            return httpx.Response(
                200, json=_fake_images_response(_SAMPLE_B64)
            )

        provider._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        result = await provider.generate_image(
            model="gpt-5.4-image-2",
            prompt="a sunset",
            quality="high",
            size="1024x1024",
            output_format="png",
        )
        assert result.image_data == _SAMPLE_BYTES
        assert result.metadata["model"] == "gpt-5.4-image-2"
        assert result.metadata["output_format"] == "png"
        assert result.metadata["usage"]["total_tokens"] == 2010

    @pytest.mark.asyncio
    async def test_unsupported_model_raises(self, provider: OpenRouterProvider):
        with pytest.raises(ProviderError, match="not supported"):
            await provider.generate_image(model="dall-e-3", prompt="test")

    @pytest.mark.asyncio
    async def test_no_image_data_in_response(self, provider: OpenRouterProvider):
        import httpx

        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"data": []})
        )
        provider._client = httpx.AsyncClient(
            transport=transport,
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        with pytest.raises(ProviderError, match="No image data"):
            await provider.generate_image(
                model="gpt-5-image", prompt="test"
            )

    @pytest.mark.asyncio
    async def test_http_error(self, provider: OpenRouterProvider):
        import httpx

        transport = httpx.MockTransport(
            lambda req: httpx.Response(401, json={"error": "Unauthorized"})
        )
        provider._client = httpx.AsyncClient(
            transport=transport,
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        with pytest.raises(ProviderError, match="OpenRouter API error"):
            await provider.generate_image(
                model="gpt-5-image", prompt="test"
            )

    @pytest.mark.asyncio
    async def test_size_translates_to_aspect_ratio(
        self, provider: OpenRouterProvider
    ):
        import json

        import httpx

        captured: list[dict] = []

        def handler(req):
            captured.append(json.loads(req.content))
            return httpx.Response(200, json=_fake_images_response(_SAMPLE_B64))

        provider._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        await provider.generate_image(
            model="gpt-5-image", prompt="test", size="1024x1024"
        )
        assert captured[0].get("aspect_ratio") == "1:1"
        assert "size" not in captured[0]


class TestEditImage:
    @pytest.mark.asyncio
    async def test_successful_edit_with_input_references(
        self, provider: OpenRouterProvider
    ):
        import json

        import httpx

        captured: list[dict] = []

        def handler(req):
            assert req.url.path.endswith("/images")
            captured.append(json.loads(req.content))
            return httpx.Response(
                200,
                json={
                    "created": 1700000000,
                    "data": [{"b64_json": _SAMPLE_B64}],
                },
            )

        provider._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        result = await provider.edit_image(
            model="gpt-5.4-image-2",
            image_data=_SAMPLE_BYTES,
            prompt="add a sun",
            size="1024x1024",
        )
        assert result.image_data == _SAMPLE_BYTES
        assert result.metadata["operation"] == "edit"
        body = captured[0]
        assert "messages" not in body
        assert "modalities" not in body
        refs = body.get("input_references", [])
        assert len(refs) == 1
        assert refs[0]["type"] == "image_url"
        assert refs[0]["image_url"]["url"].startswith("data:image/png;base64,")

    @pytest.mark.asyncio
    async def test_edit_with_data_url_image(self, provider: OpenRouterProvider):
        import json

        import httpx

        captured: list[dict] = []

        def handler(req):
            captured.append(json.loads(req.content))
            return httpx.Response(
                200,
                json={
                    "created": 1700000000,
                    "data": [{"b64_json": _SAMPLE_B64}],
                },
            )

        provider._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        await provider.edit_image(
            model="gpt-5.4-image-2",
            image_data=_SAMPLE_IMAGE_DATA_URL,
            prompt="edit this",
        )
        refs = captured[0].get("input_references", [])
        assert refs[0]["image_url"]["url"] == _SAMPLE_IMAGE_DATA_URL

    @pytest.mark.asyncio
    async def test_mask_data_rejected(self, provider: OpenRouterProvider):
        with pytest.raises(ProviderError, match="Mask-based editing"):
            await provider.edit_image(
                model="gpt-5.4-image-2",
                image_data=_SAMPLE_BYTES,
                prompt="test",
                mask_data=_SAMPLE_BYTES,
            )

    @pytest.mark.asyncio
    async def test_unsupported_model_raises(self, provider: OpenRouterProvider):
        with pytest.raises(ProviderError, match="not supported"):
            await provider.edit_image(
                model="dall-e-3",
                image_data=_SAMPLE_BYTES,
                prompt="test",
            )


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self, provider: OpenRouterProvider):
        import httpx

        def handler(req):
            assert req.url.path.endswith("/images/models")
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "openai/gpt-5.4-image-2"},
                        {"id": "openai/gpt-5-image"},
                        {"id": "openai/gpt-5-image-mini"},
                    ]
                },
            )

        provider._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        result = await provider.check_health()
        assert result["status"] == "healthy"
        assert "gpt-5.4-image-2" in result["models_available"]
        assert "warning" not in result

    @pytest.mark.asyncio
    async def test_partial_models_still_healthy_with_warning(
        self, provider: OpenRouterProvider
    ):
        import httpx

        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200, json={"data": [{"id": "openai/gpt-5-image"}]}
            )
        )
        provider._client = httpx.AsyncClient(
            transport=transport,
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        result = await provider.check_health()
        assert result["status"] == "healthy"
        assert "gpt-5-image" in result["models_available"]
        assert "warning" in result

    @pytest.mark.asyncio
    async def test_unhealthy_no_models(self, provider: OpenRouterProvider):
        import httpx

        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"data": []})
        )
        provider._client = httpx.AsyncClient(
            transport=transport,
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        result = await provider.check_health()
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_unhealthy_on_error(self, provider: OpenRouterProvider):
        import httpx

        transport = httpx.MockTransport(
            lambda req: httpx.Response(500, json={"error": "down"})
        )
        provider._client = httpx.AsyncClient(
            transport=transport,
            base_url=provider._base_url,
            headers=provider._client.headers,
        )

        result = await provider.check_health()
        assert result["status"] == "unhealthy"
        assert "error" in result


class TestEstimateCost:
    def test_returns_zero_with_note(self, provider):
        result = provider.estimate_cost("gpt-5-image", "test")
        assert result["estimated_cost_usd"] == 0.0
        assert "note" in result


class TestClose:
    @pytest.mark.asyncio
    async def test_close_is_idempotent(self, provider: OpenRouterProvider):
        await provider.close()
        await provider.close()
