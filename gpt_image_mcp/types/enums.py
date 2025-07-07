"""
Enum definitions for GPT Image MCP Server parameters.

These enums provide type-safe parameter values that are automatically
exposed to LLMs through the MCP protocol's list_tools functionality.
"""

from enum import Enum


# Description mappings for enums
IMAGE_QUALITY_DESCRIPTIONS = {
    "auto": "Automatic quality selection based on prompt",
    "high": "Maximum quality with higher token usage",
    "medium": "Balanced quality and cost",
    "low": "Lower quality with reduced cost"
}

IMAGE_SIZE_DESCRIPTIONS = {
    "1024x1024": "Square format (1:1 ratio)",
    "1536x1024": "Landscape format (3:2 ratio)",
    "1024x1536": "Portrait format (2:3 ratio)"
}

IMAGE_STYLE_DESCRIPTIONS = {
    "vivid": "Vibrant, dramatic, and stylized interpretation",
    "natural": "Realistic and less stylized results"
}

MODERATION_LEVEL_DESCRIPTIONS = {
    "auto": "Standard content moderation",
    "low": "Less restrictive content filtering"
}

OUTPUT_FORMAT_DESCRIPTIONS = {
    "png": "Lossless quality, supports transparency",
    "jpeg": "Smaller files, no transparency support",
    "webp": "Modern format with good compression"
}

BACKGROUND_TYPE_DESCRIPTIONS = {
    "auto": "Automatic background selection (default)",
    "transparent": "Transparent background (PNG/WebP only)",
    "opaque": "Opaque background (solid color)"
}


class ImageQuality(str, Enum):
    """
    Image quality options for generation and editing.
    
    The quality parameter affects both the visual quality and generation cost:
    - AUTO: Let the model decide based on the prompt
    - HIGH: Maximum quality, higher cost
    - MEDIUM: Balanced quality and cost
    - LOW: Lower quality, reduced cost
    """
    
    AUTO = "auto"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    @property
    def description(self) -> str:
        """Get human-readable description of this quality level."""
        return IMAGE_QUALITY_DESCRIPTIONS.get(self.value, self.value)


class ImageSize(str, Enum):
    """
    Supported image sizes for generation and editing.
    
    All sizes maintain high resolution but different aspect ratios:
    - SQUARE: 1:1 aspect ratio, good for profile pictures, icons
    - LANDSCAPE: 3:2 aspect ratio, good for banners, headers
    - PORTRAIT: 2:3 aspect ratio, good for posters, mobile screens
    """
    
    SQUARE = "1024x1024"
    LANDSCAPE = "1536x1024"
    PORTRAIT = "1024x1536"
    AUTO = "auto"
    
    @property
    def description(self) -> str:
        """Get human-readable description of this size."""
        return IMAGE_SIZE_DESCRIPTIONS.get(self.value, self.value)

class ImageStyle(str, Enum):
    """
    Image style options for generation.
    
    The style parameter affects the artistic interpretation:
    - VIVID: More vibrant, dramatic, and stylized results
    - NATURAL: More realistic and less stylized results
    """
    
    VIVID = "vivid"
    NATURAL = "natural"
    
    @property
    def description(self) -> str:
        """Get human-readable description of this style."""
        return IMAGE_STYLE_DESCRIPTIONS.get(self.value, self.value)


class ModerationLevel(str, Enum):
    """
    Content moderation levels.
    
    Controls how strictly content is filtered:
    - AUTO: Default OpenAI moderation
    - LOW: Less restrictive filtering
    """
    
    AUTO = "auto"
    LOW = "low"
    
    @property
    def description(self) -> str:
        """Get human-readable description of this moderation level."""
        return MODERATION_LEVEL_DESCRIPTIONS.get(self.value, self.value)


class OutputFormat(str, Enum):
    """
    Supported output formats for images.
    
    Different formats offer different benefits:
    - PNG: Lossless compression, supports transparency, larger files
    - JPEG: Lossy compression, smaller files, no transparency
    - WEBP: Modern format, good compression, supports transparency
    """
    
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    
    @property
    def description(self) -> str:
        """Get human-readable description of this format."""
        return OUTPUT_FORMAT_DESCRIPTIONS.get(self.value, self.value)
    
    @property
    def supports_transparency(self) -> bool:
        """Check if this format supports transparency."""
        return self.value in ["png", "webp"]
    
    @property
    def mime_type(self) -> str:
        """Get MIME type for this format."""
        return f"image/{self.value}"


class BackgroundType(str, Enum):
    """
    Background options for image generation.
    
    Controls the background treatment for gpt-image-1:
    - AUTO: Let the model decide based on the prompt (default)
    - TRANSPARENT: Transparent background 
    - OPAQUE: Opaque background (solid color)
    """
    
    AUTO = "auto"
    TRANSPARENT = "transparent"
    OPAQUE = "opaque"
    
    @property
    def description(self) -> str:
        """Get human-readable description of this background type."""
        return BACKGROUND_TYPE_DESCRIPTIONS.get(self.value, self.value)
    
    def is_compatible_with_format(self, format: OutputFormat) -> bool:
        """Check if this background type is compatible with the given format."""
        if self == BackgroundType.TRANSPARENT:
            return format.supports_transparency
        return True