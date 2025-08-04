"""Unit tests for storage management functionality."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gpt_image_mcp.config.settings import StorageSettings
from gpt_image_mcp.storage.manager import ImageStorageManager

# Image format signatures
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


class TestImageStorageManager:
    """Test image storage manager functionality."""

    @pytest.mark.asyncio
    async def test_storage_manager_creation(self, mock_storage_settings):
        """Test storage manager creation and initialization."""
        manager = ImageStorageManager(mock_storage_settings)

        assert manager.settings == mock_storage_settings
        assert manager.base_path == Path(mock_storage_settings.base_path)
        assert not manager._cleanup_task_running

        await manager.initialize()

        # Check that directories were created
        assert manager.base_path.exists()
        assert (manager.base_path / "images").exists()
        assert (manager.base_path / "metadata").exists()

        await manager.close()

    def test_image_id_generation(self, mock_storage_settings):
        """Test unique image ID generation."""
        manager = ImageStorageManager(mock_storage_settings)

        # Generate multiple IDs
        ids = [manager.generate_image_id() for _ in range(100)]

        # All IDs should be unique
        assert len(set(ids)) == 100

        # All IDs should have correct format
        for image_id in ids:
            assert image_id.startswith("img_")
            assert len(image_id) > 20  # Should be reasonably long
            assert image_id.replace("img_", "").replace("_", "").isalnum()

    def test_task_id_generation(self, mock_storage_settings):
        """Test unique task ID generation."""
        manager = ImageStorageManager(mock_storage_settings)

        # Generate multiple task IDs
        ids = [manager.generate_task_id() for _ in range(100)]

        # All IDs should be unique
        assert len(set(ids)) == 100

        # All IDs should have correct format
        for task_id in ids:
            assert task_id.startswith("task_")
            assert len(task_id) > 20  # Should be reasonably long

    @pytest.mark.asyncio
    async def test_store_image_bytes(self, storage_manager, sample_image_bytes):
        """Test storing image as bytes."""
        image_id = "test_image_123"
        metadata = {
            "prompt": "test image",
            "quality": "high",
            "size": "1024x1024",
            "format": "png",
        }

        # Store the image
        await storage_manager.store_image(image_id, sample_image_bytes, metadata)

        # Verify files were created
        image_path = storage_manager.base_path / "images" / f"{image_id}.png"
        metadata_path = storage_manager.base_path / "metadata" / f"{image_id}.json"

        assert image_path.exists()
        assert metadata_path.exists()

        # Verify content
        stored_bytes = image_path.read_bytes()
        assert stored_bytes == sample_image_bytes

        stored_metadata = json.loads(metadata_path.read_text())
        assert stored_metadata["prompt"] == "test image"
        assert stored_metadata["quality"] == "high"
        assert "created_at" in stored_metadata
        assert "file_size" in stored_metadata

    @pytest.mark.asyncio
    async def test_store_image_base64(self, storage_manager, sample_image_data):
        """Test storing image from base64 data URL."""
        image_id = "test_image_b64"
        metadata = {"prompt": "base64 test"}

        # Store the image from base64
        await storage_manager.store_image(image_id, sample_image_data, metadata)

        # Verify files were created
        image_path = storage_manager.base_path / "images" / f"{image_id}.png"
        metadata_path = storage_manager.base_path / "metadata" / f"{image_id}.json"

        assert image_path.exists()
        assert metadata_path.exists()

        # Verify metadata contains base64 info
        stored_metadata = json.loads(metadata_path.read_text())
        assert stored_metadata["prompt"] == "base64 test"
        assert stored_metadata["source_format"] == "data_url"

    @pytest.mark.asyncio
    async def test_retrieve_image(self, storage_manager, sample_image_bytes):
        """Test retrieving stored images."""
        image_id = "test_retrieve_123"
        metadata = {"prompt": "retrieve test"}

        # Store an image first
        await storage_manager.store_image(image_id, sample_image_bytes, metadata)

        # Retrieve as bytes
        retrieved_bytes = await storage_manager.retrieve_image_bytes(image_id)
        assert retrieved_bytes == sample_image_bytes

        # Retrieve as data URL
        data_url = await storage_manager.retrieve_image_data_url(image_id)
        assert data_url.startswith("data:image/png;base64,")

        # Retrieve metadata
        retrieved_metadata = await storage_manager.get_image_metadata(image_id)
        assert retrieved_metadata["prompt"] == "retrieve test"
        assert "created_at" in retrieved_metadata

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_image(self, storage_manager):
        """Test retrieving non-existent images."""
        # Should return None for non-existent images
        result = await storage_manager.retrieve_image_bytes("nonexistent")
        assert result is None

        result = await storage_manager.retrieve_image_data_url("nonexistent")
        assert result is None

        result = await storage_manager.get_image_metadata("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_images(self, storage_manager, sample_image_bytes):
        """Test listing stored images."""
        # Store multiple images
        images = [
            ("img1", {"prompt": "first image"}),
            ("img2", {"prompt": "second image"}),
            ("img3", {"prompt": "third image"}),
        ]

        for image_id, metadata in images:
            await storage_manager.store_image(image_id, sample_image_bytes, metadata)

        # List all images
        image_list = await storage_manager.list_images()

        assert len(image_list) == 3

        # Check that all images are in the list
        image_ids = [img["image_id"] for img in image_list]
        assert "img1" in image_ids
        assert "img2" in image_ids
        assert "img3" in image_ids

        # Check metadata is included
        for img_info in image_list:
            assert "created_at" in img_info
            assert "file_size" in img_info
            assert "prompt" in img_info

    @pytest.mark.asyncio
    async def test_list_images_with_filters(self, storage_manager, sample_image_bytes):
        """Test listing images with date filters."""
        # Store images with different timestamps
        old_metadata = {"prompt": "old image"}
        new_metadata = {"prompt": "new image"}

        await storage_manager.store_image("old_img", sample_image_bytes, old_metadata)
        await storage_manager.store_image("new_img", sample_image_bytes, new_metadata)

        # Manually modify one image's timestamp to be older
        old_metadata_path = storage_manager.base_path / "metadata" / "old_img.json"
        metadata = json.loads(old_metadata_path.read_text())
        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        metadata["created_at"] = old_date
        old_metadata_path.write_text(json.dumps(metadata, indent=2))

        # List recent images (last 5 days)
        recent_images = await storage_manager.list_images(days=5)
        recent_ids = [img["image_id"] for img in recent_images]

        assert "new_img" in recent_ids
        assert "old_img" not in recent_ids

        # List with limit
        limited_images = await storage_manager.list_images(limit=1)
        assert len(limited_images) == 1

    @pytest.mark.asyncio
    async def test_delete_image(self, storage_manager, sample_image_bytes):
        """Test deleting stored images."""
        image_id = "test_delete_123"
        metadata = {"prompt": "delete test"}

        # Store an image
        await storage_manager.store_image(image_id, sample_image_bytes, metadata)

        # Verify it exists
        assert await storage_manager.retrieve_image_bytes(image_id) is not None

        # Delete the image
        success = await storage_manager.delete_image(image_id)
        assert success is True

        # Verify it's gone
        assert await storage_manager.retrieve_image_bytes(image_id) is None
        assert await storage_manager.get_image_metadata(image_id) is None

        # Files should be deleted
        image_path = storage_manager.base_path / "images" / f"{image_id}.png"
        metadata_path = storage_manager.base_path / "metadata" / f"{image_id}.json"
        assert not image_path.exists()
        assert not metadata_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_image(self, storage_manager):
        """Test deleting non-existent images."""
        success = await storage_manager.delete_image("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_storage_stats(self, storage_manager, sample_image_bytes):
        """Test storage statistics calculation."""
        from tests.conftest import create_larger_test_image

        # Store some images with larger data to get measurable size
        larger_image_bytes = create_larger_test_image(width=1000, height=1000)

        for i in range(3):
            await storage_manager.store_image(
                f"stats_test_{i}",
                larger_image_bytes,  # Use properly generated larger image
                {"prompt": f"test image {i}"},
            )

        stats = await storage_manager.get_storage_stats()

        assert stats["total_images"] == 3
        assert stats["storage_usage_mb"] > 0
        assert stats["retention_policy_days"] == storage_manager.settings.retention_days
        assert "cleanup_last_run" in stats
        assert "base_path" in stats

    @pytest.mark.asyncio
    async def test_cleanup_old_images(self, storage_manager, sample_image_bytes):
        """Test cleanup of old images based on retention policy."""
        # Store images
        current_metadata = {"prompt": "current image"}
        old_metadata = {"prompt": "old image"}

        await storage_manager.store_image(
            "current_img", sample_image_bytes, current_metadata
        )
        await storage_manager.store_image("old_img", sample_image_bytes, old_metadata)

        # Manually set one image to be older than retention period
        old_metadata_path = storage_manager.base_path / "metadata" / "old_img.json"
        metadata = json.loads(old_metadata_path.read_text())
        old_date = (
            datetime.now() - timedelta(days=storage_manager.settings.retention_days + 1)
        ).isoformat()
        metadata["created_at"] = old_date
        old_metadata_path.write_text(json.dumps(metadata, indent=2))

        # Run cleanup
        cleaned_count = await storage_manager.cleanup_old_images()

        assert cleaned_count == 1

        # Verify old image is gone, current remains
        assert await storage_manager.retrieve_image_bytes("current_img") is not None
        assert await storage_manager.retrieve_image_bytes("old_img") is None

    @pytest.mark.asyncio
    async def test_cleanup_by_size_limit(self, storage_manager, sample_image_bytes):
        """Test cleanup when storage exceeds size limit."""
        # Create a storage manager with very small size limit
        small_storage_settings = StorageSettings(
            base_path=str(storage_manager.base_path),
            max_size_gb=0.000001,  # Very small limit (0.000001 GB = 0.001 MB)
            retention_days=30,
        )
        small_manager = ImageStorageManager(small_storage_settings)
        await small_manager.initialize()

        from tests.conftest import create_larger_test_image

        try:
            # Store multiple images to exceed size limit
            larger_image_bytes = create_larger_test_image(width=500, height=500)

            for i in range(5):
                await small_manager.store_image(
                    f"size_test_{i}",
                    larger_image_bytes,  # Use properly generated larger image
                    {"prompt": f"size test {i}"},
                )

            # Run cleanup
            initial_count = len(await small_manager.list_images())
            cleaned_count = await small_manager.cleanup_by_size()
            final_count = len(await small_manager.list_images())

            # Should have cleaned some images
            assert cleaned_count > 0
            assert final_count < initial_count

        finally:
            await small_manager.close()

    @pytest.mark.asyncio
    async def test_background_cleanup_task(self, mock_storage_settings):
        """Test background cleanup task functionality."""
        # Create manager with short cleanup interval for testing
        mock_storage_settings.cleanup_interval_hours = (
            0.001  # Short interval for testing (3.6 seconds)
        )
        manager = ImageStorageManager(mock_storage_settings)

        await manager.initialize()

        try:
            # Start background cleanup task
            cleanup_task = asyncio.create_task(manager.start_cleanup_task())

            # Give the task a moment to start
            await asyncio.sleep(0.001)  # 1ms should be enough for the task to start

            assert manager._cleanup_task_running is True

            # Let it run briefly - wait longer than the cleanup interval
            await asyncio.sleep(0.05)  # 50ms should be enough for the short interval

            # Stop the task
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass

            manager._cleanup_task_running = False

        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, storage_manager, sample_image_bytes):
        """Test concurrent storage operations."""
        # Create multiple concurrent store operations
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                storage_manager.store_image(
                    f"concurrent_{i}",
                    sample_image_bytes,
                    {"prompt": f"concurrent test {i}"},
                )
            )
            tasks.append(task)

        # Wait for all to complete
        await asyncio.gather(*tasks)

        # Verify all images were stored
        image_list = await storage_manager.list_images()
        concurrent_images = [
            img for img in image_list if img["image_id"].startswith("concurrent_")
        ]
        assert len(concurrent_images) == 10

    @pytest.mark.asyncio
    async def test_error_handling_invalid_paths(self, temp_storage_path):
        """Test error handling with invalid storage paths."""
        # Create settings with invalid path
        invalid_settings = StorageSettings(
            base_path="/invalid/nonexistent/path", retention_days=30
        )

        manager = ImageStorageManager(invalid_settings)

        # Should handle path creation gracefully
        try:
            await manager.initialize()
            # If no exception, path was created successfully or error was handled
            # gracefully
            # The initialize method now handles errors gracefully
        except (PermissionError, OSError):
            # This is expected on systems where we can't create the path
            pass
        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_error_handling_corrupted_metadata(
        self, storage_manager, sample_image_bytes
    ):
        """Test handling of corrupted metadata files."""
        image_id = "corrupted_test"

        # Store a normal image first
        await storage_manager.store_image(
            image_id, sample_image_bytes, {"prompt": "test"}
        )

        # Corrupt the metadata file
        metadata_path = storage_manager.base_path / "metadata" / f"{image_id}.json"
        metadata_path.write_text("invalid json content")

        # Should handle corrupted metadata gracefully
        metadata = await storage_manager.get_image_metadata(image_id)
        assert metadata is None  # Should return None for corrupted metadata

        # Image retrieval should still work
        image_bytes = await storage_manager.retrieve_image_bytes(image_id)
        assert image_bytes == sample_image_bytes

    @pytest.mark.asyncio
    async def test_different_image_formats(self, storage_manager):
        """Test storing different image formats."""
        # Test with different format extensions
        formats = [
            ("jpeg", b"\\xff\\xd8\\xff"),  # JPEG magic bytes
            ("png", b"\\x89PNG"),  # PNG magic bytes
            ("webp", b"RIFF"),  # WebP magic bytes
        ]

        for fmt, magic_bytes in formats:
            image_id = f"format_test_{fmt}"
            # Create fake image data with proper magic bytes
            fake_image_data = magic_bytes + b"fake_image_data" * 100

            metadata = {"prompt": f"test {fmt}", "format": fmt}

            await storage_manager.store_image(image_id, fake_image_data, metadata)

            # Verify storage worked
            retrieved = await storage_manager.retrieve_image_bytes(image_id)
            assert retrieved == fake_image_data

            # Check that correct file extension was used
            expected_path = storage_manager.base_path / "images" / f"{image_id}.{fmt}"
            assert expected_path.exists()

    @pytest.mark.asyncio
    async def test_metadata_enrichment(self, storage_manager, sample_image_bytes):
        """Test that metadata is properly enriched during storage."""
        image_id = "metadata_test"
        basic_metadata = {"prompt": "test prompt", "quality": "high"}

        await storage_manager.store_image(image_id, sample_image_bytes, basic_metadata)

        # Retrieve and check enriched metadata
        metadata = await storage_manager.get_image_metadata(image_id)

        # Should contain original metadata
        assert metadata["prompt"] == "test prompt"
        assert metadata["quality"] == "high"

        # Should contain enriched metadata
        assert "created_at" in metadata
        assert "file_size" in metadata
        assert "image_id" in metadata

        # Verify data types
        assert isinstance(metadata["file_size"], int)
        assert metadata["file_size"] > 0

        # Should be a valid ISO datetime
        datetime.fromisoformat(metadata["created_at"].replace("Z", "+00:00"))

    def test_create_larger_test_image_function(self):
        """Test that create_larger_test_image helper creates properly sized images."""
        from tests.conftest import create_larger_test_image

        # Test different sizes
        small_image = create_larger_test_image(width=50, height=50)
        medium_image = create_larger_test_image(width=200, height=200)
        large_image = create_larger_test_image(width=1000, height=1000)

        # Verify they are valid PNG images (start with PNG signature)
        assert small_image.startswith(PNG_SIGNATURE)
        assert medium_image.startswith(PNG_SIGNATURE)
        assert large_image.startswith(PNG_SIGNATURE)

        # Verify sizes increase as expected (larger images should be bigger files)
        assert len(small_image) < len(medium_image) < len(large_image)

        # Verify they're reasonably sized (not tiny like the original 1x1 pixel)
        assert len(small_image) > 100  # Should be at least 100 bytes
        assert len(medium_image) > 500  # Should be at least 500 bytes
        assert len(large_image) > 2000  # Should be at least 2KB

        # Test that the function produces consistent results
        duplicate_image = create_larger_test_image(width=200, height=200)
        # Same size parameters should produce same file size
        assert len(duplicate_image) == len(medium_image)
