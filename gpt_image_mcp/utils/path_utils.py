"""Path utilities for image storage and URL generation."""

from datetime import datetime
from pathlib import Path
from typing import Optional


def extract_date_from_image_id(image_id: str) -> Optional[datetime]:
    """
    Extract datetime from image_id.
    
    Expected format: img_YYYYMMDDHHMMSS_{random}
    Returns datetime object or None if parsing fails.
    """
    try:
        # Split by underscore and get the timestamp part
        parts = image_id.split('_')
        if len(parts) >= 2 and parts[0] == 'img':
            timestamp_str = parts[1]
            if len(timestamp_str) == 14:  # YYYYMMDDHHMMSS
                return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
    except (ValueError, IndexError):
        pass
    return None


def build_image_storage_path(base_path: Path, image_id: str, file_format: str = "png") -> Path:
    """
    Build the full storage path for an image including date structure.
    
    Args:
        base_path: Base storage directory
        image_id: Image identifier containing timestamp
        file_format: File extension (png, jpg, etc.)
        
    Returns:
        Full path including year/month/day structure
    """
    # Extract date from image_id
    img_date = extract_date_from_image_id(image_id)
    
    if img_date:
        # Use the date from image_id
        date_path = base_path / "images" / str(img_date.year) / f"{img_date.month:02d}" / f"{img_date.day:02d}"
    else:
        # Fallback to current date if parsing fails
        now = datetime.now()
        date_path = base_path / "images" / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
    
    return date_path / f"{image_id}.{file_format.lower()}"


def build_image_url_path(image_id: str, file_format: str = "png") -> str:
    """
    Build the URL path for an image including date structure.
    
    Args:
        image_id: Image identifier containing timestamp
        file_format: File extension (png, jpg, etc.)
        
    Returns:
        URL path like "images/2024/01/15/img_20240115123456_abc123.png"
    """
    # Extract date from image_id
    img_date = extract_date_from_image_id(image_id)
    
    if img_date:
        # Use the date from image_id
        date_path = f"images/{img_date.year}/{img_date.month:02d}/{img_date.day:02d}"
    else:
        # Fallback to current date if parsing fails
        now = datetime.now()
        date_path = f"images/{now.year}/{now.month:02d}/{now.day:02d}"
    
    return f"{date_path}/{image_id}.{file_format.lower()}"


def find_existing_image_path(base_path: Path, image_id: str) -> Optional[Path]:
    """
    Find an existing image file by trying different formats and using date from image_id.
    
    Args:
        base_path: Base storage directory
        image_id: Image identifier
        
    Returns:
        Path to existing image file or None if not found
    """
    # Try different file formats
    for ext in ["png", "jpg", "jpeg", "webp", "gif"]:
        image_path = build_image_storage_path(base_path, image_id, ext)
        if image_path.exists():
            return image_path
    
    return None