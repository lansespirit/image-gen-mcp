"""Test fixtures and utilities shared across test modules."""

import asyncio
import shutil
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from gpt_image_mcp.config.settings import (
    CacheSettings,
    GeminiSettings,
    ImageSettings,
    Settings,
    StorageSettings,
)
from gpt_image_mcp.storage.manager import ImageStorageManager
from gpt_image_mcp.utils.cache import CacheManager
from gpt_image_mcp.utils.openai_client import OpenAIClientManager


@pytest.fixture
def temp_storage_path() -> Generator[Path, None, None]:
    """Create a temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp(prefix="gpt_image_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_openai_settings():
    """Mock OpenAI settings for testing."""
    from gpt_image_mcp.config.settings import OpenAISettings

    return OpenAISettings(
        api_key="test-api-key",
        base_url="https://api.openai.com/v1",
        organization=None,
        max_retries=3,
        timeout=30.0,
    )


@pytest.fixture
def mock_gemini_settings():
    """Mock Gemini settings for testing."""
    return GeminiSettings(api_key="test-api-key", enabled=False)


@pytest.fixture
def mock_storage_settings(temp_storage_path: Path):
    """Mock storage settings using temporary directory."""
    return StorageSettings(
        base_path=str(temp_storage_path),
        retention_days=7,
        max_size_gb=1,
        cleanup_interval_hours=1,
    )


@pytest.fixture
def mock_cache_settings():
    """Mock cache settings for testing."""
    return CacheSettings(
        enabled=True,
        backend="memory",
        ttl_hours=1,
        max_size_mb=10,
        redis_url="redis://localhost:6379/0",
    )


@pytest.fixture
def mock_image_settings():
    """Mock image settings for testing."""
    return ImageSettings(
        default_model="gpt-image-1",
        default_quality="auto",
        default_size="1024x1024",
        default_style="vivid",
        max_prompt_length=4000,
    )


@pytest.fixture
def mock_settings(
    mock_openai_settings,
    mock_gemini_settings,
    mock_storage_settings,
    mock_cache_settings,
    mock_image_settings,
):
    """Complete mock settings configuration."""
    from gpt_image_mcp.config.settings import ServerSettings

    return Settings(
        server=ServerSettings(
            name="Test Image Gen MCP Server",
            version="1.0.0-test",
            log_level="INFO",
            port=3001,
            rate_limit_rpm=10,
        ),
        openai=mock_openai_settings,
        gemini=mock_gemini_settings,
        storage=mock_storage_settings,
        cache=mock_cache_settings,
        images=mock_image_settings,
    )


@pytest_asyncio.fixture
async def storage_manager(
    mock_storage_settings,
) -> AsyncGenerator[ImageStorageManager, None]:
    """Create and initialize a storage manager for testing."""
    manager = ImageStorageManager(mock_storage_settings)
    await manager.initialize()
    try:
        yield manager
    finally:
        await manager.close()


@pytest_asyncio.fixture
async def cache_manager(mock_cache_settings) -> AsyncGenerator[CacheManager, None]:
    """Create and initialize a cache manager for testing."""
    manager = CacheManager(mock_cache_settings)
    await manager.initialize()
    try:
        yield manager
    finally:
        await manager.close()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = MagicMock()

    # Mock successful image generation response
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[
        0
    ].b64_json = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    mock_response.data[0].revised_prompt = "A test image"

    client.images.generate = AsyncMock(return_value=mock_response)
    client.images.edit = AsyncMock(return_value=mock_response)

    return client


@pytest.fixture
def mock_openai_client_manager(mock_openai_settings, mock_openai_client):
    """Mock OpenAI client manager for testing."""
    with patch.object(
        OpenAIClientManager, "_create_client", return_value=mock_openai_client
    ):
        manager = OpenAIClientManager(mock_openai_settings)
        yield manager


class MockAsyncContextManager:
    """Helper for mocking async context managers."""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def sample_image_data():
    """Sample base64 image data for testing."""
    # Tiny 1x1 PNG image encoded in base64
    return (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )


@pytest.fixture
def sample_image_bytes():
    """Sample image bytes for testing."""
    import base64

    # Tiny 1x1 PNG image
    b64_data = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    return base64.b64decode(b64_data)


def create_larger_test_image(width: int = 100, height: int = 100) -> bytes:
    """Create a larger valid PNG image for testing.

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        PNG image data as bytes
    """
    from io import BytesIO

    from PIL import Image

    # Create a simple colored image with some pattern to increase file size
    image = Image.new("RGB", (width, height), color="red")

    # Add some noise/pattern to increase file size
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    for i in range(0, width, 10):
        for j in range(0, height, 10):
            draw.rectangle([i, j, i+5, j+5], fill='blue')

    # Save to bytes
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


@pytest.fixture
def mock_mcp_context():
    """Mock MCP context for testing server functions."""
    context = MagicMock()

    # Mock request context
    context.request_context = MagicMock()
    context.request_context.lifespan_context = MagicMock()

    return context


class TestDataFactory:
    """Factory for creating test data objects."""

    @staticmethod
    def create_generation_result(
        task_id: str = "test_task_123",
        image_id: str = "img_test_456",
        prompt: str = "test prompt",
    ) -> dict:
        """Create a mock image generation result."""
        return {
            "task_id": task_id,
            "image_id": image_id,
            "image_url": (
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
            ),
            "resource_uri": f"generated-images://{image_id}",
            "metadata": {
                "prompt": prompt,
                "quality": "high",
                "size": "1024x1024",
                "style": "vivid",
                "generation_time": 2.5,
                "tokens_used": 100,
            },
        }

    @staticmethod
    def create_storage_stats() -> dict:
        """Create mock storage statistics."""
        return {
            "total_images": 42,
            "storage_usage_mb": 256.5,
            "retention_policy_days": 30,
            "last_cleanup": "2024-01-15T10:30:00Z",
            "cache_hit_rate": 0.75,
            "average_generation_time": 2.3,
        }
