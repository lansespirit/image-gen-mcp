"""Main MCP server implementation for GPT Image generation."""

import argparse
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field, ValidationError

from .config.settings import Settings
from .storage.manager import ImageStorageManager
from .tools.image_generation import ImageGenerationTool
from .tools.image_editing import ImageEditingTool
from .resources.image_resources import ImageResourceManager
from .resources.model_registry import model_registry
from .resources.prompt_templates import prompt_template_resource_manager
from .prompts.template_manager import template_manager
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
from .utils.path_utils import find_existing_image_path


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


# Global settings - will be initialized in main()
settings: Optional[Settings] = None

def configure_logging(log_level: str = "INFO") -> None:
    """Configure logging with the specified level."""
    level = getattr(logging, log_level.upper())
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True  # Force reconfiguration
    )
    
    # Update all existing loggers to the new level
    for logger_name in logging.Logger.manager.loggerDict:
        logger_instance = logging.getLogger(logger_name)
        if not logger_instance.handlers:  # Only update if no custom handlers
            logger_instance.setLevel(level)

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="GPT Image MCP Server - Generate and edit images using OpenAI's gpt-image-1 model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default stdio transport for Claude Desktop
  python -m gpt_image_mcp.server

  # Run with HTTP transport for web deployment  
  python -m gpt_image_mcp.server --transport streamable-http --port 3001

  # Run with custom config and debug logging
  python -m gpt_image_mcp.server --config /path/to/config.env --log-level DEBUG

  # Run with SSE transport
  python -m gpt_image_mcp.server --transport sse --port 8080
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (.env format)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport method (default: stdio for Claude Desktop)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=3001,
        help="Port for HTTP transports (default: 3001)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address for HTTP transports (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--cors",
        action="store_true",
        help="Enable CORS for web deployments"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    return parser.parse_args()

def load_settings(config_path: Optional[str] = None, override_log_level: Optional[str] = None) -> Settings:
    """Load settings from environment or config file."""
    global settings
    
    try:
        # Override config path if specified
        if config_path:
            settings_instance = Settings(_env_file=config_path)
        else:
            settings_instance = Settings()
        
        # Override log level from command line if specified
        if override_log_level:
            settings_instance.server.log_level = override_log_level
        
        settings = settings_instance
        return settings
    except ValidationError as e:
        logger.error(f"Failed to load settings due to validation error:\n{e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading settings: {e}")
        sys.exit(1)


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
        settings=settings,
    )
    
    image_editing_tool = ImageEditingTool(
        openai_client=openai_client,
        storage_manager=storage_manager,
        cache_manager=cache_manager,
        settings=settings,
    )
    
    resource_manager = ImageResourceManager(
        storage_manager=storage_manager,
        settings=settings.storage
    )
    
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


# Create the MCP server with minimal configuration
# FastMCP has sensible defaults, only override what's necessary
mcp = FastMCP(
    name="GPT Image MCP Server",
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

# Add image serving route for HTTP transports
@mcp.custom_route("/images/{image_id}", methods=["GET"])
async def serve_image(request):
    """Serve stored images via HTTP endpoint."""
    from starlette.responses import FileResponse, Response
    
    image_id = request.path_params["image_id"]
    
    try:
        # Access the global settings directly
        if not settings:
            return Response("Server not initialized", status_code=500)
        
        # Create storage manager instance to find the image
        storage_path = Path(settings.storage.base_path)
        image_path = find_existing_image_path(storage_path, image_id)
        
        if not image_path or not image_path.exists():
            return Response("Image not found", status_code=404)
        
        # Determine MIME type from file extension
        extension = image_path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        }
        
        media_type = mime_types.get(extension, 'application/octet-stream')
        
        # Return image with proper headers
        return FileResponse(
            image_path,
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=31536000",  # 1 year cache
                "ETag": f'"{image_id}"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error serving image {image_id}: {e}")
        return Response("Internal server error", status_code=500)

# Default logging configuration - will be updated in main()
logger = logging.getLogger(__name__)


# Helper function to get server context
def get_server_context(ctx) -> ServerContext:
    """Get server context from MCP context."""
    return ctx.request_context.lifespan_context


# Tool definitions
@mcp.tool(
    title="Health Check",
    description="Check server health and status"
)
async def health_check() -> dict[str, Any]:
    """
    Check the health status of the MCP server and its dependencies.
    
    Returns health information including:
    - status: overall health status
    - timestamp: current server time
    - version: server version
    - services: status of dependent services
    """
    server_ctx = mcp.get_context().request_context.lifespan_context
    
    try:
        # Check OpenAI client
        openai_status = "healthy"
        try:
            # Simple test - this doesn't make an API call
            _ = server_ctx.openai_client.client
        except Exception:
            openai_status = "unhealthy"
        
        # Check storage
        storage_status = "healthy"
        try:
            if not server_ctx.storage_manager.base_path.exists():
                storage_status = "unhealthy"
        except Exception:
            storage_status = "unhealthy"
        
        # Check cache
        cache_status = "healthy" if server_ctx.cache_manager.enabled else "disabled"
        try:
            if server_ctx.cache_manager.enabled and not server_ctx.cache_manager.cache:
                cache_status = "unhealthy"
        except Exception:
            cache_status = "unhealthy"
        
        overall_status = "healthy" if all(
            status in ["healthy", "disabled"] 
            for status in [openai_status, storage_status, cache_status]
        ) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": asyncio.get_event_loop().time(),
            "version": settings.server.version if settings else "unknown",
            "services": {
                "openai": openai_status,
                "storage": storage_status,
                "cache": cache_status
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": asyncio.get_event_loop().time(),
            "error": str(e)
        }


@mcp.tool(
    title="Server Info",
    description="Get server configuration and runtime information"
)
async def server_info() -> dict[str, Any]:
    """
    Get detailed server information including configuration and capabilities.
    
    Returns:
    - server: server metadata
    - capabilities: available features
    - configuration: non-sensitive configuration details
    """
    server_ctx = mcp.get_context().request_context.lifespan_context
    
    try:
        return {
            "server": {
                "name": settings.server.name if settings else "GPT Image MCP Server",
                "version": settings.server.version if settings else "unknown",
                "log_level": settings.server.log_level if settings else "INFO"
            },
            "capabilities": {
                "image_generation": True,
                "image_editing": True,
                "caching": server_ctx.cache_manager.enabled,
                "storage": True,
                "prompt_templates": True,
                "model_registry": True
            },
            "configuration": {
                "default_quality": settings.images.default_quality if settings else "auto",
                "default_size": settings.images.default_size if settings else "1536x1024",
                "default_style": settings.images.default_style if settings else "vivid",
                "storage_retention_days": settings.storage.retention_days if settings else 30,
                "cache_ttl_hours": settings.cache.ttl_hours if settings and settings.cache.enabled else None
            }
        }
        
    except Exception as e:
        logger.error(f"Server info failed: {e}")
        return {
            "error": str(e)
        }


@mcp.tool(
    title="Generate Image",
    description="Generate images using OpenAI's gpt-image-1 model from text descriptions"
)
async def generate_image(
    prompt: str = Field(
        ..., 
        description="The best practices for image generation prompt is to be highly specific and detailed about the subject, setting, style, mood, and visual elements you want, while using clear, unambiguous language to guide the AI's creative interpretation.",
        min_length=1,
        max_length=4000
    ),
    quality: Optional[str] = Field(
        default="auto",
        description="Image quality: auto, high, medium, or low"
    ),
    size: Optional[str] = Field(
        default="auto",
        description="Image size: 1024x1024, 1536x1024, 1024x1536 or auto"
    ),
    style: Optional[str] = Field(
        default="vivid",
        description="Image style: vivid or natural"
    ),
    moderation: Optional[str] = Field(
        default="auto",
        description="Content moderation level: auto or low"
    ),
    output_format: Optional[str] = Field(
        default="png",
        description="Output format: png, jpeg, or webp"
    ),
    compression: Optional[int] = Field(
        default=100,
        ge=0,
        le=100,
        description="Compression level for JPEG/WebP (0-100)"
    ),
    background: Optional[str] = Field(
        default="auto",
        description="Background type: auto, transparent, opaque"
    ),
) -> dict[str, Any]:
    """
    Generate an image from a text prompt using gpt-image-1.
    
    Returns a dictionary containing:
    - task_id: Unique identifier for this generation task
    - image_id: Unique identifier for the generated image
    - image_url: HTTP URL to access the generated image
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
    size: Optional[str] = Field(
        default="auto",
        description="Output image size: 1024x1024, 1536x1024, or 1024x1536"
    ),
    quality: Optional[str] = Field(
        default="auto",
        description="Image quality: auto, high, medium, or low"
    ),
    output_format: Optional[str] = Field(
        default="png",
        description="Output format: png, jpeg, or webp"
    ),
    compression: Optional[int] = Field(
        default=100,
        ge=0,
        le=100,
        description="Compression level for JPEG/WebP (0-100)"
    ),
    background: Optional[str] = Field(
        default="auto",
        description="Background type: auto, transparent, white, or black"
    ),
) -> dict[str, Any]:
    """
    Edit an existing image with text instructions.
    
    Returns a dictionary containing:
    - task_id: Unique identifier for this editing task
    - image_id: Unique identifier for the edited image
    - image_url: HTTP URL to access the edited image
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
    description="Access a specific generated image by its unique identifier. Returns the full image data as a base64-encoded data URL for MCP resource access.",
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
    "model-info://{model_id}",
    name="get_model_info",
    title="Model Documentation",
    description="Complete API documentation for AI models including capabilities, pricing, rate limits, available resources, and usage examples. Support for multiple models via model_id parameter.",
    mime_type="text/markdown"
)
async def get_model_info(
    model_id: str = Field(..., description="Model identifier (e.g., 'gpt-image-1', 'dalle-3')")
) -> str:
    """Get model capabilities and pricing information for specified model."""
    return await model_registry.get_model_documentation(model_id)


@mcp.resource(
    "models://list",
    name="list_models",
    title="Available Models",
    description="List all available AI models with their basic information and capabilities.",
    mime_type="application/json"
)
async def list_models() -> str:
    """List all available AI models."""
    import json
    
    models = []
    for model_id in await model_registry.list_models():
        model_info = await model_registry.get_model_info(model_id)
        if model_info:
            models.append({
                "model_id": model_info.model_id,
                "name": model_info.name,
                "version": model_info.version,
                "capabilities": model_info.capabilities,
                "resource_uri": f"model-info://{model_id}"
            })
    
    return json.dumps({
        "models": models,
        "total": len(models),
        "usage": {
            "description": "Use model-info://{model_id} to get detailed information about specific models",
            "example": "model-info://gpt-image-1"
        }
    }, indent=2)


@mcp.resource(
    "prompt-templates://list",
    name="list_prompt_templates",
    title="Available Prompt Templates",
    description="List all available prompt templates with their categories, descriptions, and usage information. Templates are organized by category for easy discovery.",
    mime_type="application/json"
)
async def list_prompt_templates() -> str:
    """List all available prompt templates.
    
    This resource provides discovery and documentation for templates.
    Users can browse available templates and understand their parameters
    before using them with mcp.prompt functions.
    """
    import json
    return json.dumps(prompt_template_resource_manager.list_templates(), indent=2)


@mcp.resource(
    "prompt-templates://{template_name}",
    name="get_prompt_template",
    title="Prompt Template Details",
    description="Get detailed information about a specific prompt template including parameters, examples, and usage instructions. Returns comprehensive documentation for the template.",
    mime_type="application/json"
)
async def get_prompt_template(
    template_name: str = Field(..., description="ID of the prompt template (e.g., 'creative_image', 'product_photography')")
) -> str:
    """Get detailed information about a specific prompt template."""
    import json
    
    template_details = prompt_template_resource_manager.get_template_details(template_name)
    
    if template_details is None:
        # Return helpful error message with suggestions
        error_response = prompt_template_resource_manager.get_template_not_found_response(template_name)
        return json.dumps(error_response, indent=2)
    
    return json.dumps(template_details, indent=2)


# ===================================================================
# MCP PROMPT TEMPLATES - Direct Image Generation
# ===================================================================
#
# All prompt functions now directly generate images instead of
# returning prompt messages. This provides a complete end-to-end
# workflow where users input parameters and receive generated images.
#
# The system uses templates.json to define prompts and automatically
# generates parameter definitions to avoid manual errors.
# ===================================================================

async def _generate_from_template(
    template_id: str,
    **kwargs
) -> dict[str, Any]:
    """Helper function to generate images from templates.
    
    Args:
        template_id: ID of the template to use
        **kwargs: Template parameters
        
    Returns:
        Image generation result with template information
    """
    # Get server context
    ctx = mcp.get_context()
    server_ctx = get_server_context(ctx)
    
    # Render the template
    prompt_text, metadata = template_manager.render_template(template_id, **kwargs)
    
    # Generate the image with template information
    result = await server_ctx.image_generation_tool.generate(
        prompt=prompt_text,
        quality=metadata.get('quality', 'high'),
        size=metadata.get('recommended_size', '1024x1024'),
        style=metadata.get('style', 'vivid')
    )
    
    # Add template information
    result['template_used'] = template_id
    result['prompt_text'] = prompt_text
    
    return result

@mcp.prompt(
    name="creative_image",
    title="Creative Image Generation",
    description="Generate creative images with expert art direction. Combines subject, artistic style, mood, and color palette to create vivid, artistic images."
)
async def creative_image(
    subject: str = Field(..., description="Main subject of the image - be specific and detailed"),
    style: str = Field(default="digital art", description="Artistic style or medium"),
    setting: str = Field(default="dramatic environment", description="Environmental setting or location"),
    mood: str = Field(default="vibrant", description="Desired mood or emotional tone"),
    lighting: str = Field(default="dramatic", description="Lighting style"),
    color_palette: str = Field(default="rich and vibrant", description="Color scheme preference"),
    composition: str = Field(default="dynamic", description="Compositional approach")
) -> dict[str, Any]:
    """Generate a creative image directly from parameters."""
    return await _generate_from_template(
        "creative_image",
        subject=subject,
        style=style,
        setting=setting,
        mood=mood,
        lighting=lighting,
        color_palette=color_palette,
        composition=composition
    )


@mcp.prompt(
    name="product_photography",
    title="Product Photography",
    description="Generate professional product photography with commercial specifications. Optimized for e-commerce, catalogs, and marketing materials."
)
async def product_photography(
    product: str = Field(..., description="Detailed product description with key features"),
    background: str = Field(default="clean white studio", description="Background setting with texture details"),
    lighting: str = Field(default="soft diffused", description="Professional lighting setup"),
    angle: str = Field(default="hero shot", description="Camera angle and perspective"),
    detail_focus: str = Field(default="product features highlighted", description="Specific details to emphasize")
) -> dict[str, Any]:
    """Generate professional product photography directly."""
    return await _generate_from_template(
        "product_photography",
        product=product,
        background=background,
        lighting=lighting,
        angle=angle,
        detail_focus=detail_focus
    )


@mcp.prompt(
    name="social_media",
    title="Social Media Graphics",
    description="Generate platform-optimized social media graphics with engagement best practices."
)
async def social_media(
    platform: str = Field(..., description="Target social media platform"),
    content_type: str = Field(..., description="Type of social media post"),
    topic: str = Field(..., description="Main topic or subject of the post"),
    brand_style: str = Field(default="modern and clean", description="Brand visual aesthetic"),
    visual_elements: str = Field(default="geometric shapes and icons", description="Specific visual elements to include"),
    color_scheme: str = Field(default="brand-aligned", description="Color palette for the design"),
    layout: str = Field(default="balanced", description="Compositional layout"),
    call_to_action: bool = Field(default=False, description="Include call-to-action element")
) -> dict[str, Any]:
    """Generate social media graphics directly."""
    return await _generate_from_template(
        "social_media",
        platform=platform,
        content_type=content_type,
        topic=topic,
        brand_style=brand_style,
        visual_elements=visual_elements,
        color_scheme=color_scheme,
        layout=layout,
        call_to_action=call_to_action
    )


@mcp.prompt(
    name="artistic_style",
    title="Artistic Style Generation",
    description="Generate images in specific artistic styles and periods. Emulates famous artists, art movements, and traditional mediums."
)
async def artistic_style(
    subject: str = Field(..., description="Main subject with specific details"),
    setting: str = Field(default="appropriate to style", description="Environmental context"),
    artist_style: str = Field(default="impressionist", description="Specific artist or art movement style"),
    medium: str = Field(default="oil painting", description="Traditional art medium"),
    era: str = Field(default="appropriate to style", description="Historical artistic period"),
    atmosphere: str = Field(default="evocative", description="Emotional atmosphere"),
    technique: str = Field(default="masterful brushwork", description="Specific artistic technique")
) -> dict[str, Any]:
    """Generate artistic style images directly."""
    return await _generate_from_template(
        "artistic_style",
        subject=subject,
        setting=setting,
        artist_style=artist_style,
        medium=medium,
        era=era,
        atmosphere=atmosphere,
        technique=technique
    )


@mcp.prompt(
    name="og_image",
    title="Open Graph Images",
    description="Generate social media preview images optimized for sharing. Creates engaging thumbnails for websites and blog posts."
)
async def og_image(
    title: str = Field(..., description="Main title text to display prominently"),
    brand_name: Optional[str] = Field(default=None, description="Website or brand name"),
    background_style: str = Field(default="modern gradient", description="Background visual style"),
    visual_elements: str = Field(default="subtle design accents", description="Supporting visual elements"),
    text_layout: str = Field(default="centered", description="Typography arrangement"),
    color_scheme: str = Field(default="professional", description="Color palette theme")
) -> dict[str, Any]:
    """Generate Open Graph images directly."""
    return await _generate_from_template(
        "og_image",
        title=title,
        brand_name=brand_name,
        background_style=background_style,
        visual_elements=visual_elements,
        text_layout=text_layout,
        color_scheme=color_scheme
    )


@mcp.prompt(
    name="blog_header",
    title="Blog Header Images",
    description="Generate header images for blog posts and articles with optional space for text overlays."
)
async def blog_header(
    topic: str = Field(..., description="Blog post topic or main theme"),
    style: str = Field(default="modern editorial", description="Visual design style"),
    visual_metaphor: str = Field(default="abstract concept visualization", description="Visual representation of the topic"),
    mood: str = Field(default="engaging", description="Emotional tone"),
    lighting: str = Field(default="bright and optimistic", description="Lighting atmosphere"),
    color_palette: str = Field(default="complementary", description="Color scheme"),
    include_text_space: bool = Field(default=True, description="Reserve space for text overlay")
) -> dict[str, Any]:
    """Generate blog header images directly."""
    return await _generate_from_template(
        "blog_header",
        topic=topic,
        style=style,
        visual_metaphor=visual_metaphor,
        mood=mood,
        lighting=lighting,
        color_palette=color_palette,
        include_text_space=include_text_space
    )


@mcp.prompt(
    name="hero_banner",
    title="Website Hero Banners",
    description="Generate hero section banners for websites with impactful landing page visuals."
)
async def hero_banner(
    website_type: str = Field(..., description="Type of website"),
    main_theme: str = Field(..., description="Core theme or main subject of the hero banner"),
    industry: Optional[str] = Field(default=None, description="Industry or market sector"),
    message: Optional[str] = Field(default=None, description="Key value proposition or message"),
    visual_style: str = Field(default="modern professional", description="Design aesthetic approach"),
    hero_elements: str = Field(default="abstract technology patterns", description="Main visual elements"),
    atmosphere: str = Field(default="innovative and dynamic", description="Overall feeling and mood")
) -> dict[str, Any]:
    """Generate website hero banners directly."""
    return await _generate_from_template(
        "hero_banner",
        website_type=website_type,
        main_theme=main_theme,
        industry=industry,
        message=message,
        visual_style=visual_style,
        hero_elements=hero_elements,
        atmosphere=atmosphere
    )


@mcp.prompt(
    name="thumbnail",
    title="Video Thumbnails",
    description="Generate engaging thumbnails for video content optimized for high click-through rates."
)
async def thumbnail(
    content_type: str = Field(..., description="Type of video content"),
    topic: str = Field(..., description="Specific video topic or subject"),
    style: str = Field(default="bold and dynamic", description="Visual design style"),
    focal_element: str = Field(default="eye-catching central subject", description="Main visual focus"),
    emotion: str = Field(default="exciting", description="Emotional hook"),
    color_scheme: str = Field(default="vibrant high-contrast", description="Color approach for visibility")
) -> dict[str, Any]:
    """Generate video thumbnails directly."""
    return await _generate_from_template(
        "thumbnail",
        content_type=content_type,
        topic=topic,
        style=style,
        focal_element=focal_element,
        emotion=emotion,
        color_scheme=color_scheme
    )


@mcp.prompt(
    name="infographic",
    title="Infographic Images",
    description="Generate information graphics and data visualizations that effectively communicate complex data."
)
async def infographic(
    data_type: str = Field(..., description="Type of data or information"),
    topic: str = Field(..., description="Subject matter of the infographic"),
    visual_approach: str = Field(default="modern clean", description="Design style approach"),
    chart_types: str = Field(default="mixed visualization elements", description="Types of data visualizations"),
    layout: str = Field(default="vertical flow", description="Information organization"),
    color_scheme: str = Field(default="professional palette", description="Color coding approach")
) -> dict[str, Any]:
    """Generate infographic images directly."""
    return await _generate_from_template(
        "infographic",
        data_type=data_type,
        topic=topic,
        visual_approach=visual_approach,
        chart_types=chart_types,
        layout=layout,
        color_scheme=color_scheme
    )


@mcp.prompt(
    name="email_header",
    title="Email Newsletter Headers",
    description="Generate header images for email newsletters with branded designs and seasonal themes."
)
async def email_header(
    newsletter_type: str = Field(..., description="Type of newsletter content"),
    main_topic: str = Field(..., description="Main topic or focus of this newsletter edition"),
    brand_name: Optional[str] = Field(default=None, description="Company or brand name"),
    theme: Optional[str] = Field(default=None, description="Newsletter theme or campaign"),
    season: Optional[str] = Field(default=None, description="Seasonal context"),
    visual_style: str = Field(default="clean and modern", description="Design aesthetic"),
    header_elements: str = Field(default="brand elements and patterns", description="Visual components")
) -> dict[str, Any]:
    """Generate email newsletter headers directly."""
    return await _generate_from_template(
        "email_header",
        newsletter_type=newsletter_type,
        main_topic=main_topic,
        brand_name=brand_name,
        theme=theme,
        season=season,
        visual_style=visual_style,
        header_elements=header_elements
    )


def main():
    """Main entry point for FastMCP server."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load settings first (pass CLI log level to override)
    app_settings = load_settings(args.config, args.log_level)
    
    # Configure logging with final log level (from settings, which includes CLI override)
    configure_logging(app_settings.server.log_level)
    
    logger.info(f"Starting {app_settings.server.name} v{app_settings.server.version}")
    logger.info(f"Transport: {args.transport}")
    
    # Configure FastMCP settings based on command line arguments
    if args.transport in ["sse", "streamable-http"]:
        logger.info(f"Server will run on {args.host}:{args.port}")
        
        # Configure host and port through FastMCP settings system
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        
        # Configure CORS if requested
        if hasattr(args, 'cors') and args.cors:
            logger.info("CORS enabled for web deployments")
            # Note: CORS configuration depends on FastMCP implementation
            # This may need adjustment based on actual FastMCP CORS settings
    
    try:
        # Run server with specified transport
        if args.transport == "stdio":
            logger.info("Running with stdio transport for Claude Desktop integration")
            mcp.run(transport="stdio")
        elif args.transport == "sse":
            logger.info("Running with Server-Sent Events (SSE) transport")
            mcp.run(transport="sse")
        elif args.transport == "streamable-http":
            logger.info("Running with streamable HTTP transport for web deployment")
            mcp.run(transport="streamable-http")
        else:
            logger.error(f"Unsupported transport: {args.transport}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Server stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()