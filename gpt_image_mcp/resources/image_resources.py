"""Image resource management for MCP server."""

import base64
import json
import logging

from ..config.settings import StorageSettings
from ..storage.manager import ImageStorageManager

logger = logging.getLogger(__name__)


class ImageResourceManager:
    """Manages MCP resources for image access and information."""

    def __init__(
        self,
        storage_manager: ImageStorageManager,
        settings: StorageSettings,
    ):
        self.storage_manager = storage_manager
        self.settings = settings

    async def get_image_resource(self, image_id: str) -> str:
        """Get a generated image by its unique ID."""
        try:
            image_data, metadata = await self.storage_manager.load_image(image_id)

            # Determine the image format
            file_format = metadata.get("file_info", {}).get("format", "PNG").lower()
            mime_type = f"image/{file_format}"

            # Encode as base64 for transport
            base64_data = base64.b64encode(image_data).decode()

            # Return as a formatted resource
            return json.dumps(
                {
                    "image_id": image_id,
                    "data_url": f"data:{mime_type};base64,{base64_data}",
                    "metadata": metadata,
                    "mime_type": mime_type,
                    "size_bytes": len(image_data),
                },
                indent=2,
            )

        except FileNotFoundError:
            return json.dumps(
                {
                    "error": f"Image {image_id} not found",
                    "image_id": image_id,
                },
                indent=2,
            )
        except Exception as e:
            logger.error(f"Error retrieving image {image_id}: {e}")
            return json.dumps(
                {
                    "error": f"Failed to retrieve image: {str(e)}",
                    "image_id": image_id,
                },
                indent=2,
            )

    async def get_recent_images(self, limit: int = 10, days: int = 7) -> str:
        """Get recent image generation history."""
        try:
            recent_images = await self.storage_manager.get_recent_images(limit, days)

            # Format for display
            formatted_images = []
            for image_metadata in recent_images:
                formatted_image = {
                    "image_id": image_metadata.get("image_id"),
                    "created_at": image_metadata.get("created_at"),
                    "prompt": image_metadata.get("prompt", "")[:100] + "..."
                    if len(image_metadata.get("prompt", "")) > 100
                    else image_metadata.get("prompt", ""),
                    "resource_uri": f"generated-images://{image_metadata.get('image_id')}",
                    "file_size_bytes": image_metadata.get("file_info", {}).get(
                        "size_bytes"
                    ),
                    "dimensions": image_metadata.get("file_info", {}).get("dimensions"),
                    "format": image_metadata.get("file_info", {}).get("format"),
                    "parameters": image_metadata.get("parameters", {}),
                    "cost_estimate": image_metadata.get("cost_info", {}).get(
                        "estimated_cost_usd"
                    ),
                }
                formatted_images.append(formatted_image)

            result = {
                "images": formatted_images,
                "total_count": len(formatted_images),
                "query_params": {
                    "limit": limit,
                    "days": days,
                },
            }

            # Add storage usage summary
            stats = await self.storage_manager.get_storage_stats()
            result["storage_summary"] = {
                "total_images": stats.get("total_images", 0),
                "storage_usage_mb": stats.get("storage_usage_mb", 0),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error retrieving recent images: {e}")
            return json.dumps(
                {
                    "error": f"Failed to retrieve recent images: {str(e)}",
                    "images": [],
                    "total_count": 0,
                },
                indent=2,
            )

    async def get_storage_stats(self) -> str:
        """Get storage statistics and management information."""
        try:
            stats = await self.storage_manager.get_storage_stats()

            # Enhanced stats with additional information
            enhanced_stats = {
                **stats,
                "retention_policy": {
                    "retention_days": self.settings.retention_days,
                    "max_size_gb": self.settings.max_size_gb,
                    "cleanup_interval_hours": self.settings.cleanup_interval_hours,
                },
                "storage_health": {
                    "status": "healthy"
                    if stats.get("storage_usage_mb", 0)
                    < (self.settings.max_size_gb * 1024 * 0.9)
                    else "near_limit",
                    "usage_percentage": round(
                        (
                            stats.get("storage_usage_mb", 0)
                            / (self.settings.max_size_gb * 1024)
                        )
                        * 100,
                        2,
                    ),
                },
                "recommendations": [],
            }

            # Add recommendations based on usage
            usage_pct = enhanced_stats["storage_health"]["usage_percentage"]
            if usage_pct > 90:
                enhanced_stats["recommendations"].append(
                    "Storage usage is high. Consider cleaning up old files or "
                    "increasing storage limit."
                )
            elif usage_pct > 75:
                enhanced_stats["recommendations"].append(
                    "Storage usage is moderate. Monitor usage and consider "
                    "cleanup policies."
                )

            if stats.get("total_images", 0) == 0:
                enhanced_stats["recommendations"].append(
                    "No images found. Start generating images to populate storage."
                )

            return json.dumps(enhanced_stats, indent=2)

        except Exception as e:
            logger.error(f"Error retrieving storage stats: {e}")
            return json.dumps(
                {
                    "error": f"Failed to retrieve storage stats: {str(e)}",
                    "total_images": 0,
                    "storage_usage_mb": 0,
                },
                indent=2,
            )
