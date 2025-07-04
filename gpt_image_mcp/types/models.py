"""Pydantic models for GPT Image MCP Server parameters."""

from pydantic import BaseModel, Field
from typing import Optional

from .enums import (
    ImageQuality,
    ImageSize,
    ImageStyle,
    ModerationLevel,
    OutputFormat,
    BackgroundType,
)


class ImageGenerationParams(BaseModel):
    """Parameters for image generation operations."""
    
    prompt: str = Field(
        ...,
        description="Text description for image generation",
        min_length=1,
        max_length=4000
    )
    
    quality: ImageQuality = Field(
        default=ImageQuality.AUTO,
        description="Image quality level"
    )
    
    size: ImageSize = Field(
        default=ImageSize.LANDSCAPE,
        description="Image dimensions"
    )
    
    style: ImageStyle = Field(
        default=ImageStyle.VIVID,
        description="Image style preference"
    )
    
    moderation: ModerationLevel = Field(
        default=ModerationLevel.AUTO,
        description="Content moderation level"
    )
    
    output_format: OutputFormat = Field(
        default=OutputFormat.PNG,
        description="Output image format"
    )
    
    compression: int = Field(
        default=100,
        ge=1,
        le=100,
        description="Image compression level (1-100)"
    )
    
    background: BackgroundType = Field(
        default=BackgroundType.AUTO,
        description="Background type for the image"
    )


class ImageEditingParams(BaseModel):
    """Parameters for image editing operations."""
    
    image_id: str = Field(
        ...,
        description="Unique identifier of the image to edit",
        min_length=1
    )
    
    prompt: str = Field(
        ...,
        description="Text instructions for image editing",
        min_length=1,
        max_length=4000
    )
    
    quality: ImageQuality = Field(
        default=ImageQuality.AUTO,
        description="Image quality level"
    )
    
    size: ImageSize = Field(
        default=ImageSize.LANDSCAPE,
        description="Image dimensions"
    )
    
    output_format: OutputFormat = Field(
        default=OutputFormat.PNG,
        description="Output image format"
    )
    
    compression: int = Field(
        default=100,
        ge=1,
        le=100,
        description="Image compression level (1-100)"
    )
    
    background: BackgroundType = Field(
        default=BackgroundType.AUTO,
        description="Background type for the edited image"
    )


class ImageMetadata(BaseModel):
    """Metadata for generated or edited images."""
    
    image_id: str = Field(description="Unique identifier of the image")
    prompt: str = Field(description="Original prompt used")
    size: ImageSize = Field(description="Image dimensions")
    format: OutputFormat = Field(description="Image format")
    created_at: str = Field(description="Creation timestamp")
    file_path: str = Field(description="Local file path")
    file_size: int = Field(description="File size in bytes")
    
    
class StorageInfo(BaseModel):
    """Storage statistics and information."""
    
    total_images: int = Field(description="Total number of stored images")
    total_size_mb: float = Field(description="Total storage size in MB")
    available_space_mb: float = Field(description="Available storage space in MB")
    oldest_image_date: Optional[str] = Field(description="Date of oldest stored image")
    newest_image_date: Optional[str] = Field(description="Date of newest stored image")