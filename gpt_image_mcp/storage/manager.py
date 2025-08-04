"""Image storage management system."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
from PIL import Image

from ..config.settings import StorageSettings
from ..utils.path_utils import build_image_storage_path, find_existing_image_path


class ImageStorageManager:
    """Manages local image storage with organized directory structure."""

    def __init__(self, settings: StorageSettings):
        self.settings = settings
        self.base_path = Path(settings.base_path)
        self.images_path = self.base_path / "images"
        self.cache_path = self.base_path / "cache"
        self.logs_path = self.base_path / "logs"
        self._cleanup_task_running = False

    def generate_task_id(self) -> str:
        """Generate a unique task ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = str(uuid.uuid4()).replace("-", "")[:12]
        return f"task_{timestamp}_{random_part}"

    async def store_image(
        self, image_id: str, image_data: Any, metadata: dict[str, Any]
    ) -> None:
        """Store image data with a provided image ID.
        
        This method is primarily used in tests where you need to control
        the image ID. For production use, prefer save_image() which handles
        ID generation and organized storage.
        
        Args:
            image_id: The specific image ID to use
            image_data: Image data as bytes or base64 data URL
            metadata: Image metadata dictionary
        """
        # Determine format
        fmt = metadata.get("format", "png").lower()
        if isinstance(image_data, str) and image_data.startswith("data:image/"):
            # base64 data URL
            import base64
            import re

            match = re.match(r"data:image/(.*?);base64,(.*)", image_data)
            if not match:
                raise ValueError("Invalid data URL")
            fmt = match.group(1).lower()
            image_bytes = base64.b64decode(match.group(2))
            metadata["source_format"] = "data_url"
        elif isinstance(image_data, bytes):
            image_bytes = image_data
        else:
            raise ValueError("Unsupported image data type")

        image_path = self.images_path / f"{image_id}.{fmt}"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(image_path, "wb") as f:
            await f.write(image_bytes)

        # Enrich metadata
        enriched = dict(metadata)
        enriched["image_id"] = image_id
        enriched["created_at"] = datetime.now().isoformat()
        enriched["file_size"] = len(image_bytes)
        metadata_path = self.base_path / "metadata" / f"{image_id}.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(enriched, indent=2))

    async def retrieve_image_bytes(self, image_id: str) -> Any:
        """Retrieve image bytes by image_id."""
        for ext in ("png", "jpg", "jpeg", "webp"):
            image_path = self.images_path / f"{image_id}.{ext}"
            if image_path.exists():
                async with aiofiles.open(image_path, "rb") as f:
                    return await f.read()
        return None

    async def retrieve_image_data_url(self, image_id: str) -> Any:
        """Retrieve image as base64 data URL."""
        import base64

        for ext in ("png", "jpg", "jpeg", "webp"):
            image_path = self.images_path / f"{image_id}.{ext}"
            if image_path.exists():
                async with aiofiles.open(image_path, "rb") as f:
                    b = await f.read()
                b64 = base64.b64encode(b).decode()
                return f"data:image/{ext};base64,{b64}"
        return None

    async def get_image_metadata(self, image_id: str) -> Any:
        metadata_path = self.base_path / "metadata" / f"{image_id}.json"
        if not metadata_path.exists():
            return None
        try:
            async with aiofiles.open(metadata_path) as f:
                return json.loads(await f.read())
        except Exception:
            return None

    async def list_images(self, days: int = None, limit: int = None) -> list:
        """List stored images, optionally filtered by days and/or limit."""
        images = []
        now = datetime.now()
        metadata_dir = self.base_path / "metadata"
        if not metadata_dir.exists():
            return []
        for f in metadata_dir.glob("*.json"):
            try:
                async with aiofiles.open(f) as fh:
                    meta = json.loads(await fh.read())
                if days is not None:
                    created = meta.get("created_at")
                    if created:
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        if (now - dt).days > days:
                            continue
                images.append(meta)
            except Exception:
                continue
        images.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        if limit is not None:
            images = images[:limit]
        return images

    async def delete_image(self, image_id: str) -> bool:
        """Delete image and metadata."""
        found = False
        for ext in ("png", "jpg", "jpeg", "webp"):
            image_path = self.images_path / f"{image_id}.{ext}"
            if image_path.exists():
                image_path.unlink()
                found = True
        metadata_path = self.base_path / "metadata" / f"{image_id}.json"
        if metadata_path.exists():
            metadata_path.unlink()
            found = True
        return found

    async def cleanup_old_images(self) -> int:
        """Delete images older than retention policy."""
        retention_days = getattr(self.settings, "retention_days", 30)
        now = datetime.now()
        cleaned = 0
        metadata_dir = self.base_path / "metadata"
        if not metadata_dir.exists():
            return 0
        for f in metadata_dir.glob("*.json"):
            try:
                async with aiofiles.open(f) as fh:
                    meta = json.loads(await fh.read())
                created = meta.get("created_at")
                if created:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if (now - dt).days > retention_days:
                        image_id = meta.get("image_id")
                        await self.delete_image(image_id)
                        cleaned += 1
            except Exception:
                continue
        return cleaned

    async def cleanup_by_size(self) -> int:
        """Delete images if storage exceeds max_size_gb."""
        max_size_gb = getattr(self.settings, "max_size_gb", 10)
        metadata_dir = self.base_path / "metadata"
        if not metadata_dir.exists():
            return 0
        images = []
        for f in metadata_dir.glob("*.json"):
            try:
                async with aiofiles.open(f) as fh:
                    meta = json.loads(await fh.read())
                images.append(meta)
            except Exception:
                continue
        images.sort(key=lambda x: x.get("created_at", ""))  # oldest first

        # Calculate initial total size in GB
        total_size_bytes = 0
        for ext in ("png", "jpg", "jpeg", "webp"):
            for img in self.images_path.rglob(f"*.{ext}"):
                total_size_bytes += img.stat().st_size
        total_size_gb = total_size_bytes / (1024 * 1024 * 1024)

        cleaned = 0
        while total_size_gb > max_size_gb and images:
            meta = images.pop(0)
            image_id = meta.get("image_id")
            # Find the image file and get its size before deletion
            image_file = None
            for ext in ("png", "jpg", "jpeg", "webp"):
                candidate = self.images_path / f"{image_id}.{ext}"
                if candidate.exists():
                    image_file = candidate
                    break
            image_size_bytes = image_file.stat().st_size if image_file else 0
            await self.delete_image(image_id)
            # Subtract the deleted file size from total
            total_size_gb -= image_size_bytes / (1024 * 1024 * 1024)
            cleaned += 1
        return cleaned

    async def initialize(self):
        """Initialize storage directories."""
        for path in [
            self.base_path,
            self.images_path,
            self.cache_path,
            self.logs_path,
            self.base_path / "metadata",
        ]:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Could not create storage directory '{path}': {e}. "
                    "Please check directory permissions or try setting a different base_path."
                )
        # For tests, we'll allow this to continue without failing

    def generate_image_id(self) -> str:
        """Generate a unique image ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = str(uuid.uuid4()).replace("-", "")[:12]
        return f"img_{timestamp}_{random_part}"

    def get_image_path(self, image_id: str, file_format: str = "png") -> Path:
        """Get the full path for an image file using date from image_id."""
        return build_image_storage_path(self.base_path, image_id, file_format)

    def get_metadata_path(self, image_id: str) -> Path:
        """Get the full path for an image metadata file."""
        image_path = self.get_image_path(image_id, "png")
        return image_path.parent / f"{image_id}.json"

    async def save_image(
        self, image_data: bytes, metadata: dict[str, Any], file_format: str = "png"
    ) -> tuple[str, Path]:
        """Save image data to organized storage with auto-generated ID.
        
        This is the primary method for saving images in production. It generates
        a unique image ID, uses date-organized directory structure, and includes
        comprehensive metadata with file information and image dimensions.
        
        Args:
            image_data: Raw image data as bytes
            metadata: Image metadata dictionary
            file_format: Image file format (png, jpeg, webp)
            
        Returns:
            Tuple of (image_id, image_path)
        """
        image_id = self.generate_image_id()
        image_path = self.get_image_path(image_id, file_format)
        metadata_path = self.get_metadata_path(image_id)

        # Ensure directory exists
        image_path.parent.mkdir(parents=True, exist_ok=True)

        # Save image file
        async with aiofiles.open(image_path, "wb") as f:
            await f.write(image_data)

        # Add file info to metadata
        file_info = {
            "filename": image_path.name,
            "size_bytes": len(image_data),
            "format": file_format.upper(),
            "path": str(image_path),
        }

        # Get image dimensions
        try:
            with Image.open(image_path) as img:
                file_info["dimensions"] = f"{img.width}x{img.height}"
        except Exception:
            file_info["dimensions"] = "unknown"

        # Complete metadata
        complete_metadata = {
            "image_id": image_id,
            "created_at": datetime.now().isoformat(),
            "file_info": file_info,
            **metadata,
        }

        # Save metadata
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(complete_metadata, indent=2))

        return image_id, image_path

    async def load_image(self, image_id: str) -> tuple[bytes, dict[str, Any]]:
        """Load image data and metadata from storage."""
        # Find the image file using the utility function
        image_path = find_existing_image_path(self.base_path, image_id)

        if not image_path:
            raise FileNotFoundError(f"Image {image_id} not found")

        # Load image data
        async with aiofiles.open(image_path, "rb") as f:
            image_data = await f.read()

        # Load metadata
        metadata_path = self.get_metadata_path(image_id)
        if metadata_path.exists():
            async with aiofiles.open(metadata_path) as f:
                metadata = json.loads(await f.read())
        else:
            metadata = {"image_id": image_id, "created_at": "unknown"}

        return image_data, metadata

    async def get_recent_images(
        self, limit: int = 10, days: int = 7
    ) -> list[dict[str, Any]]:
        """Get recent images within specified time range."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_images = []

        # Search through date-organized directories
        for year_dir in self.images_path.iterdir():
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue

            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue

                for day_dir in month_dir.iterdir():
                    if not day_dir.is_dir() or not day_dir.name.isdigit():
                        continue

                    # Check if this directory is within our date range
                    try:
                        dir_date = datetime(
                            int(year_dir.name), int(month_dir.name), int(day_dir.name)
                        )
                        if dir_date < cutoff_date:
                            continue
                    except ValueError:
                        continue

                    # Look for metadata files
                    for metadata_file in day_dir.glob("*.json"):
                        try:
                            async with aiofiles.open(metadata_file) as f:
                                metadata = json.loads(await f.read())
                            recent_images.append(metadata)
                        except Exception:
                            continue

        # Sort by creation date and limit results
        recent_images.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return recent_images[:limit]

    async def get_storage_stats(self) -> dict[str, Any]:
        """Get storage usage statistics."""
        total_images = 0
        total_size = 0
        oldest_date = None
        newest_date = None

        # Check for all image file types
        for pattern in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            for image_file in self.images_path.rglob(pattern):
                total_images += 1
                total_size += image_file.stat().st_size

                created_time = datetime.fromtimestamp(image_file.stat().st_ctime)
                if oldest_date is None or created_time < oldest_date:
                    oldest_date = created_time
                if newest_date is None or created_time > newest_date:
                    newest_date = created_time

        return {
            "total_images": total_images,
            "storage_usage_mb": round(total_size / (1024 * 1024), 2),
            "oldest_image": oldest_date.isoformat() if oldest_date else None,
            "newest_image": newest_date.isoformat() if newest_date else None,
            "retention_policy_days": self.settings.retention_days,
            "cleanup_last_run": datetime.now().isoformat(),
            "base_path": str(self.base_path),
        }

    async def cleanup_old_files(self) -> int:
        """Clean up files older than retention period."""
        cutoff_date = datetime.now() - timedelta(days=self.settings.retention_days)
        cleaned_count = 0

        for image_file in self.images_path.rglob("*"):
            if not image_file.is_file():
                continue

            created_time = datetime.fromtimestamp(image_file.stat().st_ctime)
            if created_time < cutoff_date:
                try:
                    image_file.unlink()
                    cleaned_count += 1

                    # Also remove corresponding metadata file
                    if image_file.suffix in [".png", ".jpg", ".jpeg", ".webp"]:
                        metadata_file = image_file.with_suffix(".json")
                        if metadata_file.exists():
                            metadata_file.unlink()
                except Exception:
                    pass  # Continue cleaning other files

        return cleaned_count

    async def start_cleanup_task(self):
        """Start background cleanup task."""
        self._cleanup_task_running = True
        try:
            while self._cleanup_task_running:
                await asyncio.sleep(
                    getattr(self.settings, "cleanup_interval_hours", 1) * 3600
                )
                await self.cleanup_old_images()
        except asyncio.CancelledError:
            pass
        finally:
            self._cleanup_task_running = False

    async def close(self):
        """Close storage manager and cleanup resources."""
        self._cleanup_task_running = False
