"""Main MCP server implementation for GPT Image generation."""

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union, List

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field, field_validator

from .config.settings import Settings
from .storage.manager import ImageStorageManager
from .tools.image_generation import ImageGenerationTool
from .tools.image_editing import ImageEditingTool
from .resources.image_resources import ImageResourceManager
from .prompts.templates import PromptTemplateManager
from .utils.openai_client import OpenAIClientManager
from .utils.cache import CacheManager
from .utils.validators import (
    validate_image_quality,
    validate_image_size,
    validate_image_style,
    validate_moderation_level,
    validate_output_format,
    validate_background_type,
    validate_compression,
    validate_limit,
    validate_days,
    sanitize_prompt,
    validate_base64_image,
)
from .types.enums import (
    ImageQuality,
    ImageSize,
    ImageStyle,
    ModerationLevel,
    OutputFormat,
    BackgroundType,
)

# Initialize logging
logger = logging.getLogger(__name__)


@dataclass
class ServerContext:
    """Server context containing initialized services."""
    settings: Settings
    storage_manager: ImageStorageManager
    openai_client: OpenAIClientManager
    cache_manager: CacheManager
    image_generation_tool: ImageGenerationTool
    image_editing_tool: ImageEditingTool
    resource_manager: ImageResourceManager
    prompt_manager: PromptTemplateManager


# Initialize settings at module level
settings = Settings.from_env()

# Validate required settings early
if not settings.openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[ServerContext]:
    """
    Manage server startup and shutdown lifecycle.
    
    This context manager ensures proper initialization and cleanup of all
    server resources, including storage, cache, and background tasks.
    """
    logger.info(f"Starting {settings.server.name} v{settings.server.version}")
    
    # Initialize storage directories
    storage_path = Path(settings.storage.base_path)
    for subdir in ["images", "cache", "logs"]:
        (storage_path / subdir).mkdir(parents=True, exist_ok=True)
    
    # Initialize services with dependency injection
    storage_manager = ImageStorageManager(settings.storage)
    openai_client = OpenAIClientManager(settings.openai)
    cache_manager = CacheManager(settings.cache)
    
    # Initialize tools and resources
    image_generation_tool = ImageGenerationTool(
        openai_client=openai_client,
        storage_manager=storage_manager,
        cache_manager=cache_manager,
        settings=settings.images
    )
    
    image_editing_tool = ImageEditingTool(
        openai_client=openai_client,
        storage_manager=storage_manager,
        cache_manager=cache_manager,
        settings=settings.images
    )
    
    resource_manager = ImageResourceManager(
        storage_manager=storage_manager,
        settings=settings.storage
    )
    
    prompt_manager = PromptTemplateManager()
    
    # Initialize async services
    await asyncio.gather(
        cache_manager.initialize(),
        storage_manager.initialize(),
    )
    
    # Start background tasks
    cleanup_task = asyncio.create_task(
        storage_manager.start_cleanup_task(),
        name="storage-cleanup"
    )
    
    try:
        yield ServerContext(
            settings=settings,
            storage_manager=storage_manager,
            openai_client=openai_client,
            cache_manager=cache_manager,
            image_generation_tool=image_generation_tool,
            image_editing_tool=image_editing_tool,
            resource_manager=resource_manager,
            prompt_manager=prompt_manager,
        )
    finally:
        logger.info("Shutting down server...")
        
        # Cancel background tasks gracefully
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        
        # Close services
        await asyncio.gather(
            cache_manager.close(),
            storage_manager.close(),
            return_exceptions=True
        )
        
        logger.info("Server shutdown complete")


# Create the MCP server with comprehensive configuration
mcp = FastMCP(
    name=settings.server.name,
    lifespan=server_lifespan,
    dependencies=[
        "mcp[cli]",
        "openai",
        "pillow",
        "python-dotenv",
        "pydantic",
        "httpx",
        "aiofiles",
    ],
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.server.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# Helper function to get server context
def get_server_context(ctx) -> ServerContext:
    """Get server context from MCP context."""
    return ctx.request_context.lifespan_context


@mcp.tool(
    title="Generate Image",
    description="Generate images using OpenAI's gpt-image-1 model from text descriptions"
)
async def generate_image(
    prompt: str = Field(
        ..., 
        description="Text description of the desired image",
        min_length=1,
        max_length=4000
    ),
    quality: str = Field(
        default="auto",
        description="Image quality: auto, high, medium, or low"
    ),
    size: str = Field(
        default="landscape",
        description="Image size: 1024x1024, 1536x1024, or 1024x1536"
    ),
    style: str = Field(
        default="vivid",
        description="Image style: vivid or natural"
    ),
    moderation: str = Field(
        default="auto",
        description="Content moderation level: auto or low"
    ),
    output_format: str = Field(
        default="png",
        description="Output format: png, jpeg, or webp"
    ),
    compression: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Compression level for JPEG/WebP (0-100)"
    ),
    background: str = Field(
        default="auto",
        description="Background type: auto, transparent, white, or black"
    ),
) -> dict[str, Any]:
    """
    Generate an image from a text prompt using gpt-image-1.
    
    Returns a dictionary containing:
    - task_id: Unique identifier for this generation task
    - image_id: Unique identifier for the generated image
    - image_url: Complete data URL with base64-encoded image
    - resource_uri: MCP resource URI for future access
    - metadata: Generation details and parameters
    """
    ctx = mcp.get_context()
    server_ctx = get_server_context(ctx)
    
    # Validate and sanitize inputs with fault tolerance
    validated_prompt = sanitize_prompt(prompt)
    validated_quality = validate_image_quality(quality)
    validated_size = validate_image_size(size)
    validated_style = validate_image_style(style)
    validated_moderation = validate_moderation_level(moderation)
    validated_output_format = validate_output_format(output_format)
    validated_compression = validate_compression(compression)
    validated_background = validate_background_type(background)
    
    try:
        result = await server_ctx.image_generation_tool.generate(
            prompt=validated_prompt,
            quality=validated_quality,
            size=validated_size,
            style=validated_style,
            moderation=validated_moderation,
            output_format=validated_output_format,
            compression=validated_compression,
            background=validated_background,
        )
        return result
    except Exception as e:
        logger.error(f"Image generation failed: {e}", exc_info=True)
        raise


@mcp.tool(
    title="Edit Image", 
    description="Edit existing images using OpenAI's gpt-image-1 model with text instructions"
)
async def edit_image(
    image_data: str = Field(
        ...,
        description="Base64 encoded image or data URL"
    ),
    prompt: str = Field(
        ...,
        description="Text instructions for editing the image",
        min_length=1,
        max_length=4000
    ),
    mask_data: Optional[str] = Field(
        default=None,
        description="Optional base64 encoded mask image for targeted editing"
    ),
    size: str = Field(
        default="landscape",
        description="Output image size: 1024x1024, 1536x1024, or 1024x1536"
    ),
    quality: str = Field(
        default="auto",
        description="Image quality: auto, high, medium, or low"
    ),
    output_format: str = Field(
        default="png",
        description="Output format: png, jpeg, or webp"
    ),
    compression: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Compression level for JPEG/WebP (0-100)"
    ),
    background: str = Field(
        default="auto",
        description="Background type: auto, transparent, white, or black"
    ),
) -> dict[str, Any]:
    """
    Edit an existing image with text instructions.
    
    Returns a dictionary containing:
    - task_id: Unique identifier for this editing task
    - image_id: Unique identifier for the edited image
    - image_url: Complete data URL with base64-encoded image
    - resource_uri: MCP resource URI for future access
    - operation: "edit" to indicate this was an edit operation
    - metadata: Edit details and parameters
    """
    ctx = mcp.get_context()
    server_ctx = get_server_context(ctx)
    
    # Validate inputs
    validated_image_data = validate_base64_image(image_data)
    validated_prompt = sanitize_prompt(prompt)
    validated_mask_data = validate_base64_image(mask_data) if mask_data else None
    validated_size = validate_image_size(size)
    validated_quality = validate_image_quality(quality)
    validated_output_format = validate_output_format(output_format)
    validated_compression = validate_compression(compression)
    validated_background = validate_background_type(background)
    
    try:
        result = await server_ctx.image_editing_tool.edit(
            image_data=validated_image_data,
            prompt=validated_prompt,
            mask_data=validated_mask_data,
            size=validated_size,
            quality=validated_quality,
            output_format=validated_output_format,
            compression=validated_compression,
            background=validated_background,
        )
        return result
    except Exception as e:
        logger.error(f"Image editing failed: {e}", exc_info=True)
        raise


@mcp.resource(
    "generated-images://{image_id}",
    name="get_generated_image",
    title="Generated Image Access",
    description="Access a specific generated image by its unique identifier. Returns the full image data as a base64-encoded data URL.",
    mime_type="text/plain"
)
async def get_generated_image(
    image_id: str = Field(..., description="Unique image identifier")
) -> str:
    """Access a generated image by its unique ID."""
    ctx = mcp.get_context()
    server_ctx = get_server_context(ctx)
    return await server_ctx.resource_manager.get_image_resource(image_id)


@mcp.resource(
    "image-history://recent/{limit}/{days}",
    name="get_recent_images",
    title="Image Generation History",
    description="Retrieve recent image generation history with customizable limits and time range. Returns JSON with image metadata, generation parameters, and access URIs.",
    mime_type="application/json"
)
async def get_recent_images(
    limit: int = Field(default=10, ge=1, le=100, description="Number of images to return (1-100)"),
    days: int = Field(default=7, ge=1, le=365, description="Number of days to look back (1-365)")
) -> str:
    """Get recent image generation history."""
    ctx = mcp.get_context()
    server_ctx = get_server_context(ctx)
    
    # Validate parameters
    validated_limit = validate_limit(limit, 100)
    validated_days = validate_days(days, 365)
    
    return await server_ctx.resource_manager.get_recent_images(
        limit=validated_limit,
        days=validated_days
    )


@mcp.resource(
    "storage-stats://overview",
    name="get_storage_stats",
    title="Storage Statistics",
    description="Get comprehensive storage usage statistics including total images stored, disk usage, cache status, and cleanup information.",
    mime_type="application/json"
)
async def get_storage_stats() -> str:
    """Get storage statistics and management information."""
    ctx = mcp.get_context()
    server_ctx = get_server_context(ctx)
    return await server_ctx.resource_manager.get_storage_stats()


@mcp.resource(
    "model-info://gpt-image-1",
    name="get_model_info",
    title="GPT-Image-1 Model Documentation",
    description="Complete API documentation for GPT-Image-1 model including capabilities, pricing, rate limits, available resources, and usage examples.",
    mime_type="text/markdown"
)
async def get_model_info() -> str:
    """Get gpt-image-1 model capabilities and pricing information."""
    return """# GPT-Image-1 Model Information

## Capabilities
- **Text-to-Image Generation**: High-quality image generation from text descriptions
- **Image Editing**: Edit existing images with text instructions  
- **Multiple Formats**: PNG, JPEG, WebP output formats
- **Size Options**: 1024x1024, 1536x1024 (landscape), 1024x1536 (portrait)
- **Quality Levels**: auto, high, medium, low
- **Background Control**: transparent, opaque, auto
- **Compression**: 0-100% for JPEG/WebP formats

## Available Resources

### Static Resources
- `model-info://gpt-image-1` - This model information and API documentation
- `storage-stats://overview` - Storage usage statistics and management info

### Dynamic Resources
- `generated-images://{image_id}` - Access specific generated images by ID
  - Image IDs are returned from `generate_image` and `edit_image` tool calls
  - Example: `generated-images://img_20250704102241_dc2fdea3cb88`
- `image-history://recent/{limit}/{days}` - Get recent image generation history
  - {limit}: Number of images to return (1-100)
  - {days}: Number of days to look back (1-365)
  - Example: `image-history://recent/10/7` (last 10 images from 7 days)

## Pricing (Current)
- **Text Input**: $5 per 1M tokens
- **Image Input**: $10 per 1M tokens  
- **Image Output**: $40 per 1M tokens (~1750 tokens per image)

## Rate Limits
- **Default**: 50 requests per minute
- **Configurable**: Per organization settings
- **Automatic Retry**: Built-in backoff logic

## Best Practices
- Use descriptive, detailed prompts for better results
- Consider quality vs cost tradeoffs
- Leverage caching for repeated requests
- Use appropriate output formats for use case
- Save image IDs from tool responses to access images later via resources
"""


# Register prompt templates using centralized registry
from .prompts import prompt_registry

@mcp.prompt(
    name="creative_image_prompt",
    title="Creative Image Generation",
    description="Enhanced template for creative image generation with expert art direction. Combines subject, artistic style, mood, and color palette to create vivid, artistic images."
)
def creative_image_prompt(
    subject: str = Field(..., description="Main subject of the image"),
    style: str = Field(default="digital art", description="Artistic style"),
    mood: str = Field(default="vibrant", description="Desired mood or atmosphere"),
    color_palette: str = Field(default="colorful", description="Color scheme preference")
) -> List[base.Message]:
    """Enhanced template for creative image generation with expert art direction."""
    return prompt_registry.build_creative_prompt(
        subject=subject,
        style=style,
        mood=mood,
        color_palette=color_palette
    )


@mcp.prompt(
    name="product_image_prompt",
    title="Product Photography",
    description="Professional product photography prompt with commercial specifications. Optimized for e-commerce, catalogs, and marketing materials with controlled lighting and backgrounds."
)
def product_image_prompt(
    product: str = Field(..., description="Product description"),
    background: str = Field(default="white studio", description="Background setting"),
    lighting: str = Field(default="soft natural", description="Lighting style"),
    angle: str = Field(default="front view", description="Camera angle")
) -> List[base.Message]:
    """Professional product photography prompt with commercial specifications."""
    return prompt_registry.build_product_prompt(
        product=product,
        background=background,
        lighting=lighting,
        angle=angle
    )


@mcp.prompt(
    name="social_media_prompt",
    title="Social Media Graphics",
    description="Platform-optimized social media graphics with engagement best practices. Tailored for specific platforms with brand consistency and call-to-action elements."
)
def social_media_prompt(
    platform: str = Field(..., description="Target platform (instagram, facebook, etc.)"),
    content_type: str = Field(..., description="Type of post (announcement, quote, etc.)"),
    brand_style: str = Field(default="modern", description="Brand aesthetic"),
    call_to_action: bool = Field(default=False, description="Include CTA element")
) -> List[base.Message]:
    """Platform-optimized social media graphics with engagement best practices."""
    return prompt_registry.build_social_media_prompt(
        platform=platform,
        content_type=content_type,
        brand_style=brand_style,
        call_to_action=call_to_action
    )


@mcp.prompt(
    name="artistic_style_prompt",
    title="Artistic Style Generation",
    description="Generate images in specific artistic styles and periods. Emulates famous artists, art movements, and traditional mediums with historical accuracy."
)
def artistic_style_prompt(
    subject: str = Field(..., description="Subject to render"),
    artist_style: str = Field(default="impressionist", description="Specific artist or art movement"),
    medium: str = Field(default="oil painting", description="Art medium"),
    era: str = Field(default="modern", description="Time period or artistic era")
) -> List[base.Message]:
    """Generate images in specific artistic styles and periods."""
    return prompt_registry.build_artistic_style_prompt(
        subject=subject,
        artist_style=artist_style,
        medium=medium,
        era=era
    )


@mcp.prompt(
    name="og_image_prompt",
    title="Open Graph Images",
    description="Social media preview images optimized for sharing. Creates engaging thumbnails for websites, blog posts, and social media links with proper dimensions and text placement."
)
def og_image_prompt(
    title: str = Field(..., description="Main title text to display"),
    brand_name: Optional[str] = Field(default=None, description="Website or brand name"),
    background_style: str = Field(default="gradient", description="Background style"),
    text_layout: str = Field(default="centered", description="Text arrangement"),
    color_scheme: str = Field(default="professional", description="Color palette")
) -> List[base.Message]:
    """Social media preview images optimized for sharing."""
    return prompt_registry.build_og_image_prompt(
        title=title,
        brand_name=brand_name,
        background_style=background_style,
        text_layout=text_layout,
        color_scheme=color_scheme
    )


@mcp.prompt(
    name="blog_header_prompt",
    title="Blog Header Images",
    description="Header images for blog posts and articles. Creates visually appealing banners that complement written content with optional space for text overlays."
)
def blog_header_prompt(
    topic: str = Field(..., description="Blog post topic or theme"),
    style: str = Field(default="modern", description="Visual style"),
    mood: str = Field(default="professional", description="Emotional tone"),
    include_text_space: bool = Field(default=True, description="Reserve space for text overlay")
) -> List[base.Message]:
    """Header images for blog posts and articles."""
    return prompt_registry.build_blog_header_prompt(
        topic=topic,
        style=style,
        mood=mood,
        include_text_space=include_text_space
    )


@mcp.prompt(
    name="hero_banner_prompt",
    title="Website Hero Banners",
    description="Hero section banners for websites. Creates impactful landing page visuals that communicate brand value propositions and industry-specific messaging."
)
def hero_banner_prompt(
    website_type: str = Field(..., description="Type of website"),
    industry: Optional[str] = Field(default=None, description="Industry or niche"),
    message: Optional[str] = Field(default=None, description="Key message or value proposition"),
    visual_style: str = Field(default="modern", description="Design approach")
) -> List[base.Message]:
    """Hero section banners for websites."""
    return prompt_registry.build_hero_banner_prompt(
        website_type=website_type,
        industry=industry,
        message=message,
        visual_style=visual_style
    )


@mcp.prompt(
    name="thumbnail_prompt",
    title="Video Thumbnails",
    description="Engaging thumbnails for video content. Optimized for high click-through rates with bold visual elements and emotional appeal across different content types."
)
def thumbnail_prompt(
    content_type: str = Field(..., description="Content type"),
    topic: str = Field(..., description="Video topic or subject"),
    style: str = Field(default="bold", description="Thumbnail style"),
    emotion: str = Field(default="exciting", description="Emotional appeal")
) -> List[base.Message]:
    """Engaging thumbnails for video content."""
    return prompt_registry.build_thumbnail_prompt(
        content_type=content_type,
        topic=topic,
        style=style,
        emotion=emotion
    )


@mcp.prompt(
    name="infographic_prompt",
    title="Infographic Images",
    description="Information graphics and data visualizations. Creates educational and engaging visuals that effectively communicate complex data and concepts in accessible formats."
)
def infographic_prompt(
    data_type: str = Field(..., description="Type of information"),
    topic: str = Field(..., description="Subject matter"),
    visual_approach: str = Field(default="modern", description="Design approach"),
    layout: str = Field(default="vertical", description="Information layout")
) -> List[base.Message]:
    """Information graphics and data visualizations."""
    return prompt_registry.build_infographic_prompt(
        data_type=data_type,
        topic=topic,
        visual_approach=visual_approach,
        layout=layout
    )


@mcp.prompt(
    name="email_header_prompt",
    title="Email Newsletter Headers",
    description="Header images for email newsletters. Designs branded email headers that enhance newsletter engagement with seasonal themes and consistent visual identity."
)
def email_header_prompt(
    newsletter_type: str = Field(..., description="Newsletter category"),
    brand_name: Optional[str] = Field(default=None, description="Company or brand name"),
    theme: Optional[str] = Field(default=None, description="Newsletter theme or topic"),
    season: Optional[str] = Field(default=None, description="Seasonal context")
) -> List[base.Message]:
    """Header images for email newsletters."""
    return prompt_registry.build_email_header_prompt(
        newsletter_type=newsletter_type,
        brand_name=brand_name,
        theme=theme,
        season=season
    )


def main():
    """Main entry point for the server."""
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()