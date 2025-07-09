# Image Gen MCP Server - System Design

## Overview

This document provides a comprehensive technical overview of the Image Gen MCP Server, a Model Context Protocol (MCP) server that integrates OpenAI's gpt-image-1 model for text-to-image generation services.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │   MCP Server    │    │   OpenAI API    │
│  (Claude, etc.) │◄──►│  (FastMCP)      │◄──►│ Images API      │
└─────────────────┘    └─────────────────┘    │ (gpt-image-1)   │
                              │               └─────────────────┘
                              ▼
                       ┌─────────────────┐
                       │ Local Storage   │
                       │ - Images        │
                       │ - Metadata      │
                       │ - Cache         │
                       └─────────────────┘
```

### Core Components

1. **MCP Server Core** (FastMCP)
   - Protocol handling and message routing
   - Transport layer (stdio, SSE, Streamable HTTP)
   - Session management and state handling
   - Error handling and logging

2. **OpenAI Images API Integration Layer**
   - Images API client wrapper with retry logic
   - Correct endpoint routing (/images/generations, /images/edits)
   - gpt-image-1 model parameter handling
   - Response parsing and validation
   - Cost estimation and usage tracking

3. **Local Image Storage System**
   - Organized directory structure for generated images
   - Unique task/image ID generation and management
   - File naming conventions and metadata storage
   - Image file download and local persistence
   - File cleanup with configurable retention policies

4. **Image Processing Service**
   - Image format validation and conversion
   - Base64 encoding/decoding for client responses
   - Data URL generation (data:image/png;base64,...)
   - Metadata extraction and C2PA handling
   - Size and quality optimization
   - Local file I/O operations
   - Async image reading and encoding

5. **Caching System**
   - Request/response caching with TTL
   - Cache invalidation strategies
   - Storage backend abstraction
   - Memory usage optimization

6. **Configuration Management**
   - Environment variable handling
   - Configuration file parsing
   - Runtime configuration updates
   - Validation and defaults

## Technical Specifications

### Dependencies

```toml
[dependencies]
mcp[cli]  # Latest MCP Python SDK
openai  # OpenAI Python client (Images API)
pillow  # Image processing and validation
python-dotenv  # Environment management
pydantic  # Data validation and schemas
httpx  # HTTP client for image downloads
aiofiles = "^23.0.0"  # Async file I/O operations
pathli  # Path manipulation (built-in)
uuid  # UUID generation (built-in)
redis  # Optional caching backend
```

### Python Requirements

- Python 3.9+ (recommended 3.12+)
- UV package manager for dependency management
- Minimum 1GB RAM for image processing
- 100MB+ disk space for caching

### OpenAI Images API Integration

#### Model: gpt-image-1

The server integrates with OpenAI's latest image generation model using the correct Images API endpoints:

#### 1. Image Generation Endpoint

```python
# API Endpoint
POST https://api.openai.com/v1/images/generations

# Request Structure
{
    "model": "gpt-image-1",
    "moderation": "auto",
    "prompt": "Generate an image of...",
    "n": 1,
    "size": "1536x1024",
    "quality": "auto",  # or "high", "medium", "low"
    "style": "vivid",  # or "natural"
    "output_format": "png"  # or "jpeg", "webp"
}
```

#### 2. Image Editing Endpoint

```python
# API Endpoint
POST https://api.openai.com/v1/images/edits

# Request Structure (multipart/form-data)
{
    "model": "gpt-image-1",
    "image": "<image_file>",
    "prompt": "Edit instructions...",
    "mask": "<mask_file>",  # optional
    "n": 1,
    "size": "1536x1024"
}
```


#### Parameter Translation

The system automatically translates parameters between different provider APIs:

```python
# OpenAI → Gemini Parameter Translation
{
    "size": "1536x1024" → "aspectRatio": "16:10",
    "style": "vivid" → "stylePreset": "vivid", 
    "quality": "high" → "quality": "premium"
}
```

#### Pricing Model

- Text input tokens: $5 per 1M tokens
- Image input tokens: $10 per 1M tokens  
- Image output tokens: $40 per 1M tokens

#### Rate Limits

- Default: 50 requests per minute
- Configurable per organization
- Automatic backoff and retry logic

## Local Image Storage System

### Directory Structure

```
storage/
├── images/
│   ├── 2025/
│   │   ├── 01/
│   │   │   ├── 15/
│   │   │   │   ├── img_abc123def456.png
│   │   │   │   ├── img_abc123def456.json  # metadata
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── cache/
│   ├── requests/     # Request cache
│   └── responses/    # Response cache
└── logs/
    └── storage.log
```

### Image ID Generation

- Format: `img_{timestamp}_{random_hash}`
- Example: `img_20250630143022_abc123def456`
- Unique across all generations
- URL-safe characters only

### Metadata Storage

Each generated image has an associated JSON metadata file:

```json
{
    "image_id": "img_20250630143022_abc123def456",
    "task_id": "task_uuid_here",
    "created_at": "2025-06-30T14:30:22Z",
    "prompt": "Original generation prompt",
    "parameters": {
        "model": "gpt-image-1",
        "size": "1536x1024",
        "quality": "auto",
        "style": "vivid"
    },
    "file_info": {
        "filename": "img_20250630143022_abc123def456.png",
        "size_bytes": 1572864,
        "format": "PNG",
        "dimensions": "1536x1024"
    },
    "cost_info": {
        "estimated_cost": 0.07,
        "tokens_used": {
            "text_input": 15,
            "image_output": 1750
        }
    }
}
```

### File Retention Policy

- **Default retention**: 30 days
- **Configurable via**: `STORAGE_RETENTION_DAYS` environment variable
- **Cleanup process**: Daily background task
- **Cleanup strategy**: Delete files older than retention period
- **Metadata cleanup**: Remove orphaned metadata files

### Dual-Purpose Image Handling

The system provides both immediate access and persistent storage:

#### 1. Immediate Tool Response
- **Image Data**: Base64-encoded image content in tool response
- **Data URL**: Complete data URL for direct browser/client use
- **Metadata**: Full generation details and parameters
- **Client Access**: Immediate use without additional requests

#### 2. Persistent Resource Access
- **Local Storage**: Images saved to organized directory structure
- **MCP Resources**: Access via `generated-images://{image_id}` URI
- **Future Retrieval**: Access previously generated images
- **Resource Management**: Organized storage with cleanup policies

#### 3. Response Format Options
- **Base64 String**: Raw base64-encoded image data
- **Data URL**: `data:image/png;base64,{base64_data}` format
- **Resource URI**: `generated-images://img_20250630143022_abc123def456`
- **Metadata**: Complete generation and file information

## MCP Protocol Implementation

### Tools

#### 1. list_available_models

**Purpose**: List all available image generation models and their capabilities

**Input Schema**:
```json
{
    "type": "object",
    "properties": {},
    "required": []
}
```

**Output Schema**:
```json
{
    "type": "object",
    "properties": {
        "providers": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "models": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "provider": {"type": "string"},
                                "capabilities": {
                                    "type": "object",
                                    "properties": {
                                        "generation": {"type": "boolean"},
                                        "editing": {"type": "boolean"},
                                        "supported_sizes": {"type": "array"},
                                        "supported_formats": {"type": "array"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
```

#### 2. generate_image

**Purpose**: Generate images from text descriptions

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "prompt": {"type": "string", "description": "Text description"},
        "model": {"type": "string", "description": "Model to use (e.g., 'gpt-image-1', 'dall-e-3', 'imagen-4')", "optional": true},
        "quality": {"type": "string", "enum": ["high", "medium", "low"], "default": "auto"},
        "size": {"type": "string", "enum": ["1536x1024", "1024x1536", "1024x1024"], "default": "1536x1024"},
        "style": {"type": "string", "enum": ["vivid", "natural"], "default": "vivid"},
        "moderation": {"type": "string", "enum": ["auto", "low"], "default": "auto"},
        "output_format": {"type": "string", "enum": ["png", "jpeg", "webp"], "default": "png"},
        "background": {"type": "string", "enum": ["auto", "transparent", "opaque"], "default": "auto"}
    },
    "required": ["prompt"]
}
```

**Output Schema**:
```json
{
    "type": "object",
    "properties": {
        "task_id": {"type": "string", "description": "Unique task identifier"},
        "image_id": {"type": "string", "description": "Unique image identifier"},
        "image_url": {"type": "string", "description": "Complete Data URL (data:image/png;base64,...) containing image data"},
        "resource_uri": {"type": "string", "description": "MCP resource URI for future access"},
        "metadata": {
            "type": "object",
            "properties": {
                "size": {"type": "string"},
                "quality": {"type": "string"},
                "style": {"type": "string"},
                "prompt": {"type": "string"},
                "created_at": {"type": "string"},
                "cost_estimate": {"type": "number"},
                "file_size_bytes": {"type": "integer"},
                "dimensions": {"type": "string"},
                "format": {"type": "string", "description": "Image format (PNG, JPEG)"}
            }
        }
    }
}
```

#### 2. edit_image

**Purpose**: Edit existing images with text instructions

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "image_data": {"type": "string", "description": "Base64 encoded image"},
        "prompt": {"type": "string", "description": "Edit instructions"},
        "mask_data": {"type": "string", "description": "Optional mask image"},
        "size": {"type": "string", "enum": ["1536x1024", "1024x1536", "1024x1024"]}
    },
    "required": ["image_data", "prompt"]
}
```



### Resources

#### 1. generated-images://{image_id}

**Purpose**: Access locally stored generated images by their unique ID

**URI Template**: `generated-images://{image_id}`

**Parameters**:
- `image_id`: Unique image identifier (e.g., `img_20250630143022_abc123def456`)

**Response**:
- **Content Type**: `image/png` or `image/jpeg`
- **Body**: Raw image file data
- **Headers**: Include metadata such as creation date, prompt, parameters

**Example Usage**:
```
Resource URI: generated-images://img_20250630143022_abc123def456
Returns: PNG image file with metadata headers
```

#### 2. image-history://recent

**Purpose**: View recent generation history with local file references

**Parameters**:
- `limit`: Number of recent images (default: 10, max: 100)
- `days`: Number of days to look back (default: 7)

**Response**:
```json
{
    "images": [
        {
            "image_id": "img_20250630143022_abc123def456",
            "task_id": "task_uuid_here",
            "created_at": "2025-06-30T14:30:22Z",
            "prompt": "Original prompt",
            "resource_uri": "generated-images://img_20250630143022_abc123def456",
            "file_size_bytes": 1048576,
            "parameters": {...}
        }
    ],
    "total_count": 25,
    "storage_usage_mb": 156.7
}
```

#### 3. storage-stats://overview

**Purpose**: Local storage statistics and management information

**Response**:
```json
{
    "total_images": 1250,
    "storage_usage_mb": 2048.5,
    "oldest_image": "2025-05-15T10:20:30Z",
    "newest_image": "2025-06-30T14:30:22Z",
    "retention_policy_days": 30,
    "cleanup_last_run": "2025-06-30T02:00:00Z",
    "images_cleaned_up": 45
}
```

#### 4. model-info://gpt-image-1

**Purpose**: Model capabilities and pricing information

**Response**: Model specifications, pricing, limits, features

### Prompts

#### 1. creative-image-prompt

**Purpose**: Template for creative image generation with artistic elements

**Arguments**:
- `subject` (required): Main subject of the image
- `style` (optional): Artistic style (e.g., "impressionist", "digital art", "photorealistic")
- `mood` (optional): Desired mood or atmosphere
- `color_palette` (optional): Color scheme preference

**Example Output**: "Create a {style} artwork of {subject} with a {mood} atmosphere using {color_palette} colors"

#### 2. product-image-prompt

**Purpose**: Template for product photography and commercial images

**Arguments**:
- `product` (required): Product description
- `background` (optional): Background setting (e.g., "white studio", "natural environment")
- `lighting` (optional): Lighting style (e.g., "soft natural", "dramatic studio")
- `angle` (optional): Camera angle (e.g., "front view", "45-degree angle")

**Example Output**: "Professional product photography of {product} with {lighting} lighting on {background} background, shot from {angle}"

#### 3. artistic-style-prompt

**Purpose**: Template for generating images in specific artistic styles

**Arguments**:
- `subject` (required): Subject to render
- `artist_style` (optional): Specific artist or art movement (e.g., "Van Gogh", "Art Nouveau")
- `medium` (optional): Art medium (e.g., "oil painting", "watercolor", "digital illustration")
- `era` (optional): Time period or artistic era

**Example Output**: "Render {subject} in the style of {artist_style} using {medium} technique from the {era} period"

#### 4. og-image-prompt

**Purpose**: Template for generating Open Graph (og:image) social media preview images optimized for 1200x630px

**Arguments**:
- `title` (required): Main title text to display
- `brand_name` (optional): Website or brand name
- `background_style` (optional): Background style ("gradient", "solid", "pattern", "minimal", "tech")
- `text_layout` (optional): Text arrangement ("centered", "left-aligned", "split", "overlay")
- `color_scheme` (optional): Color palette ("professional", "vibrant", "monochrome", "brand-colors")
- `include_logo` (optional): Whether to include space for logo placement

**Example Output**: "Create a social media preview image (1200x630px) with '{title}' as the main headline{brand_name ? ' for ' + brand_name : ''}, using {background_style} background with {text_layout} text layout in {color_scheme} color scheme{include_logo ? ', including space for logo placement' : ''}"

#### 5. blog-header-prompt

**Purpose**: Template for blog post header images

**Arguments**:
- `topic` (required): Blog post topic or theme
- `style` (optional): Visual style ("modern", "minimalist", "illustrative", "photographic")
- `mood` (optional): Emotional tone ("professional", "friendly", "exciting", "calm")
- `include_text_space` (optional): Reserve space for text overlay

**Example Output**: "Design a blog header image about {topic} in {style} style with {mood} mood{include_text_space ? ', leaving space for text overlay' : ''}"

#### 6. social-media-post-prompt

**Purpose**: Template for social media graphics (Instagram, Facebook, Twitter)

**Arguments**:
- `platform` (required): Target platform ("instagram", "facebook", "twitter", "linkedin")
- `content_type` (required): Type of post ("announcement", "quote", "tip", "behind-the-scenes")
- `brand_style` (optional): Brand aesthetic ("corporate", "casual", "creative", "minimalist")
- `call_to_action` (optional): Include CTA element

**Example Output**: "Create a {platform} post graphic for {content_type} content in {brand_style} style{call_to_action ? ' with call-to-action element' : ''}"

#### 7. hero-banner-prompt

**Purpose**: Template for website hero section banners

**Arguments**:
- `website_type` (required): Type of website ("business", "portfolio", "e-commerce", "blog", "saas")
- `industry` (optional): Industry or niche (e.g., "technology", "healthcare", "creative")
- `message` (optional): Key message or value proposition
- `visual_style` (optional): Design approach ("modern", "classic", "bold", "elegant")
- `include_cta_space` (optional): Reserve space for call-to-action button

**Example Output**: "Design a hero banner for a {website_type} website{industry ? ' in the ' + industry + ' industry' : ''}{message ? ' conveying: ' + message : ''}, using {visual_style} visual style{include_cta_space ? ' with space for call-to-action button' : ''}"

#### 8. email-header-prompt

**Purpose**: Template for email newsletter header images

**Arguments**:
- `newsletter_type` (required): Newsletter category ("business", "personal", "promotional", "educational")
- `brand_name` (optional): Company or brand name
- `theme` (optional): Newsletter theme or topic
- `season` (optional): Seasonal context ("spring", "summer", "fall", "winter", "holiday")
- `layout` (optional): Header layout ("banner", "logo-focused", "text-heavy")

**Example Output**: "Create an email newsletter header for {newsletter_type} newsletter{brand_name ? ' for ' + brand_name : ''}{theme ? ' with ' + theme + ' theme' : ''}{season ? ' with ' + season + ' seasonal elements' : ''} using {layout} layout"

#### 9. thumbnail-prompt

**Purpose**: Template for video thumbnails and preview images

**Arguments**:
- `content_type` (required): Content type ("tutorial", "review", "vlog", "presentation", "demo")
- `topic` (required): Video topic or subject
- `style` (optional): Thumbnail style ("bold", "clean", "dramatic", "friendly")
- `include_text` (optional): Include text overlay space
- `emotion` (optional): Emotional appeal ("exciting", "trustworthy", "curious", "urgent")

**Example Output**: "Design a video thumbnail for {content_type} about {topic} in {style} style{emotion ? ' with ' + emotion + ' emotional appeal' : ''}{include_text ? ', including space for text overlay' : ''}"

#### 10. infographic-prompt

**Purpose**: Template for infographic-style images

**Arguments**:
- `data_type` (required): Type of information ("statistics", "process", "comparison", "timeline")
- `topic` (required): Subject matter
- `visual_approach` (optional): Design approach ("modern", "corporate", "creative", "minimal")
- `color_count` (optional): Color complexity ("monochrome", "two-color", "multi-color")
- `layout` (optional): Information layout ("vertical", "horizontal", "circular", "grid")

**Example Output**: "Create an infographic showing {data_type} about {topic} using {visual_approach} design approach with {color_count} color scheme in {layout} layout"

### Prompt Template Implementation

#### Template Processing Flow

```
1. Client Request → MCP Prompt Template
2. Argument Validation → Check required/optional parameters
3. Template Rendering → Substitute variables with values
4. Optimization → Add size/quality hints for specific use cases
5. API Integration → Pass optimized prompt to gpt-image-1
6. Response → Return generated image with template metadata
```

#### Size Optimization by Template

Each template automatically suggests optimal dimensions:

```json
{
    "og-image-prompt": {
        "default_size": "1024x1024",
        "recommended_size": "1200x630",
        "aspect_ratio": "1.91:1"
    },
    "blog-header-prompt": {
        "default_size": "1024x1024",
        "recommended_size": "1200x400",
        "aspect_ratio": "3:1"
    },
    "social-media-post-prompt": {
        "instagram": "1024x1024",
        "facebook": "1024x1024",
        "twitter": "1024x1024",
        "linkedin": "1024x1024"
    }
}
```

#### Template Enhancement Features

- **Context-Aware Prompting**: Templates include context about intended use
- **Quality Optimization**: Automatic quality suggestions based on template type
- **Style Consistency**: Built-in style guidelines for professional results
- **Brand Integration**: Support for brand-specific customization
- **Responsive Design**: Consideration for different display contexts

#### Custom Template Extension

The system supports adding custom templates:

```python
# Example custom template structure
{
    "name": "custom-template-name",
    "description": "Template description",
    "arguments": {
        "required": ["arg1", "arg2"],
        "optional": ["arg3", "arg4"]
    },
    "template": "Optimized prompt template with {arg1} and {arg2}",
    "metadata": {
        "recommended_size": "1024x1024",
        "quality": "standard",
        "style": "vivid"
    }
}
```

## Data Flow

### Image Generation Flow

```
1. Client Request → MCP Server
2. Request Validation → Parameter Validation
3. Cache Check → Return if Hit (with image data)
4. Generate Task/Image ID → Unique Identifiers
5. OpenAI Images API Call → /images/generations endpoint
6. Image Download → Fetch from OpenAI URL
7. Local Storage → Save image file + metadata
8. Image Processing → Read file, encode to base64
9. Response to Client → Image data + metadata + resource URI
```

### Local Storage Flow

```
1. OpenAI Response → Extract image URL
2. HTTP Download → Fetch image data
3. File System → Create directory structure
4. Image Storage → Save PNG/JPEG file
5. Metadata Storage → Save JSON metadata
6. Image Encoding → Read file, encode to base64
7. Client Response → Return image data + metadata
8. Resource Registration → Register MCP resource
9. Cleanup Scheduling → Add to retention queue
```

### Error Handling Flow

```
1. Error Detection → Categorization
2. Retry Logic → Exponential Backoff
3. Fallback Strategies → Graceful Degradation
4. File I/O Error Handling → Storage Fallback
5. Logging → Structured Logging
6. Client Response → Error Details
```

### File I/O Error Handling

```
1. Directory Creation → Ensure path exists
2. Permission Check → Verify write access
3. Disk Space Check → Validate available space
4. Download Failure → Retry with backoff
5. File Write Error → Cleanup partial files
6. Metadata Write → Atomic operations
7. Cleanup on Error → Remove incomplete files
```

## Configuration Schema

### Environment Variables

```bash
# =============================================================================
# Provider Configuration
# =============================================================================
# OpenAI Provider (default enabled)
PROVIDERS__OPENAI__API_KEY=sk-your-openai-api-key-here
PROVIDERS__OPENAI__BASE_URL=https://api.openai.com/v1
PROVIDERS__OPENAI__ORGANIZATION=org-your-org-id
PROVIDERS__OPENAI__TIMEOUT=300.0
PROVIDERS__OPENAI__MAX_RETRIES=3
PROVIDERS__OPENAI__ENABLED=true

# Gemini Provider (default disabled)
PROVIDERS__GEMINI__API_KEY=your-gemini-api-key-here
PROVIDERS__GEMINI__BASE_URL=https://generativelanguage.googleapis.com/v1beta/
PROVIDERS__GEMINI__TIMEOUT=300.0
PROVIDERS__GEMINI__MAX_RETRIES=3
PROVIDERS__GEMINI__ENABLED=false
PROVIDERS__GEMINI__DEFAULT_MODEL=imagen-4

# =============================================================================
# Image Generation Settings
# =============================================================================
IMAGES__DEFAULT_MODEL=gpt-image-1
IMAGES__DEFAULT_QUALITY=auto
IMAGES__DEFAULT_SIZE=1536x1024
IMAGES__DEFAULT_STYLE=vivid
IMAGES__DEFAULT_MODERATION=auto
IMAGES__DEFAULT_OUTPUT_FORMAT=png
IMAGES__DEFAULT_COMPRESSION=100
IMAGES__BASE_HOST=

# =============================================================================
# Server Configuration
# =============================================================================
SERVER__NAME="Image Gen MCP Server"
SERVER__VERSION=0.1.0
SERVER__PORT=3001
SERVER__HOST=127.0.0.1
SERVER__LOG_LEVEL=INFO
SERVER__RATE_LIMIT_RPM=50

# =============================================================================
# Storage Configuration
# =============================================================================
STORAGE__BASE_PATH=./storage
STORAGE__RETENTION_DAYS=30
STORAGE__MAX_SIZE_GB=10.0
STORAGE__CLEANUP_INTERVAL_HOURS=24
STORAGE__CREATE_SUBDIRECTORIES=true
STORAGE__FILE_PERMISSIONS=644

# =============================================================================
# Cache Configuration
# =============================================================================
CACHE__ENABLED=true
CACHE__TTL_HOURS=24
CACHE__BACKEND=memory
CACHE__MAX_SIZE_MB=500
# CACHE__REDIS_URL=redis://localhost:6379
```

### Configuration File (config.json)

```json
{
    "openai_api_key": "sk-...",
    "openai_organization": "org-...",
    "default_quality": "auto",
    "default_size": "1536x1024",
    "default_style": "vivid",
    "moderation_level": "auto",
    "rate_limit_requests_per_minute": 50,
    "cache_enabled": true,
    "cache_ttl_hours": 24,
    "log_level": "INFO",
    "server_port": 3001,
    "storage": {
        "base_path": "./storage",
        "retention_days": 30,
        "max_size_gb": 10,
        "cleanup_interval_hours": 24,
        "create_subdirectories": true,
        "file_permissions": "644"
    },
    "prompt_templates": {
        "enable_custom_templates": true,
        "template_directory": "./templates",
        "auto_size_optimization": true,
        "include_metadata": true
    },
    "cache_backend": "memory",
    "max_cache_size_mb": 500
}
```

## Security Considerations

### API Key Management

- Environment variable storage (recommended)
- No hardcoded credentials in source code
- Secure configuration file permissions (600)
- Optional encryption for stored configurations

### Content Safety

- OpenAI's built-in content moderation
- Configurable moderation sensitivity levels
- Request logging for audit purposes
- Content policy compliance monitoring

### Rate Limiting

- Per-client rate limiting
- API quota management
- Cost control mechanisms
- Usage monitoring and alerts

## Performance Optimization

### Caching Strategy

- **Memory Cache**: Fast access for recent requests (includes base64 data)
- **Disk Cache**: Persistent storage for generated images
- **Redis Cache**: Distributed caching for multi-instance deployments
- **TTL Management**: Automatic cache expiration
- **Image Data Caching**: Cache both file paths and encoded image data
- **Response Caching**: Complete tool responses including image data

### Request Optimization

- Request deduplication
- Batch processing capabilities
- Asynchronous processing
- Connection pooling

### Resource Management

- Memory usage monitoring
- Disk space management
- Connection limit enforcement
- Graceful degradation under load

## Monitoring and Observability

### Logging

- Structured JSON logging
- Request/response correlation IDs
- Performance metrics
- Error tracking and categorization

### Metrics

- Request count and latency
- Cache hit/miss ratios
- API cost tracking
- Error rates by category

### Health Checks

- API connectivity status
- Cache system health
- Resource utilization
- Configuration validation

## Deployment Considerations

### Transport Options

1. **stdio**: Development and Claude Desktop integration
2. **SSE (Server-Sent Events)**: Web-based clients
3. **Streamable HTTP**: Production deployments (recommended)

### Scaling

- Stateless operation mode for horizontal scaling
- Load balancer compatibility
- Session persistence options
- Multi-instance coordination

### Production Setup

```bash
# Production deployment with Streamable HTTP
python server.py --transport streamable-http --port 3001 --stateless

# With process manager (PM2, systemd, etc.)
pm2 start server.py --name image-gen-mcp -- --transport streamable-http
```

## Testing Strategy

### Testing Framework and Tools

**Primary Testing Stack:**
- **pytest**: Main testing framework with async support
- **pytest-asyncio**: Async test execution
- **pytest-mock**: Mocking and patching
- **httpx-mock**: HTTP request mocking
- **pytest-cov**: Code coverage reporting
- **pytest-benchmark**: Performance benchmarking

**Additional Tools:**
- **Pillow**: Image validation and comparison
- **aiofiles**: Async file I/O testing
- **fakeredis**: Redis cache testing
- **factory-boy**: Test data generation


## Future Enhancements

### Planned Features

- Support for additional OpenAI models
- Advanced caching strategies
- Webhook notifications
- Usage analytics dashboard
- Multi-tenant support

### Extensibility

- Plugin architecture for custom processors
- Configurable output formats
- Custom prompt templates
- Third-party integration hooks

## Troubleshooting Guide

### Common Issues

1. **Authentication Failures**
   - Verify API key validity
   - Check organization access
   - Confirm model availability

2. **Rate Limiting**
   - Monitor request frequency
   - Implement client-side queuing
   - Adjust rate limit settings

3. **Memory Issues**
   - Monitor cache size
   - Implement cache cleanup
   - Optimize image processing

4. **Network Connectivity**
   - Check firewall settings
   - Verify DNS resolution
   - Test API endpoint accessibility

