"""Image storage management system."""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

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
        
    async def initialize(self):
        """Initialize storage directories."""
        for path in [self.base_path, self.images_path, self.cache_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)
    
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
        self,
        image_data: bytes,
        metadata: Dict[str, Any],
        file_format: str = "png"
    ) -> tuple[str, Path]:
        """Save image data and metadata to storage."""
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
            **metadata
        }
        
        # Save metadata
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(complete_metadata, indent=2))
        
        return image_id, image_path
    
    async def load_image(self, image_id: str) -> tuple[bytes, Dict[str, Any]]:
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
            async with aiofiles.open(metadata_path, "r") as f:
                metadata = json.loads(await f.read())
        else:
            metadata = {"image_id": image_id, "created_at": "unknown"}
        
        return image_data, metadata
    
    async def get_recent_images(self, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
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
                            int(year_dir.name),
                            int(month_dir.name), 
                            int(day_dir.name)
                        )
                        if dir_date < cutoff_date:
                            continue
                    except ValueError:
                        continue
                    
                    # Look for metadata files
                    for metadata_file in day_dir.glob("*.json"):
                        try:
                            async with aiofiles.open(metadata_file, "r") as f:
                                metadata = json.loads(await f.read())
                            recent_images.append(metadata)
                        except Exception:
                            continue
        
        # Sort by creation date and limit results
        recent_images.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return recent_images[:limit]
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics."""
        total_images = 0
        total_size = 0
        oldest_date = None
        newest_date = None
        
        for image_file in self.images_path.rglob("*.png"):
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
        while True:
            try:
                await asyncio.sleep(self.settings.cleanup_interval_hours * 3600)
                cleaned = await self.cleanup_old_files()
                if cleaned > 0:
                    print(f"Cleaned up {cleaned} old files")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error during cleanup: {e}")
    
    async def close(self):
        """Close storage manager and cleanup resources."""
        pass