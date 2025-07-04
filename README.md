# GPT Image MCP Server

An MCP (Model Context Protocol) server that integrates with OpenAI's gpt-image-1 model for text-to-image generation services.

## Features

### <� Image Generation
- **Text-to-Image**: Generate high-quality images from text descriptions using gpt-image-1
- **Image Editing**: Edit existing images with text instructions
- **Multiple Formats**: Support for PNG, JPEG, and WebP output formats
- **Quality Control**: Auto, high, medium, and low quality settings
- **Background Control**: Transparent, opaque, or auto background options

### <� MCP Integration
- **FastMCP Framework**: Built with the latest MCP Python SDK
- **Structured Output**: Validated tool responses with proper schemas
- **Resource Access**: MCP resources for image retrieval and management
- **Prompt Templates**: 10+ built-in templates for common use cases

### =� Storage & Caching
- **Local Storage**: Organized directory structure with metadata
- **Dual Access**: Immediate base64 data + persistent resource URIs
- **Smart Caching**: Memory-based caching with TTL
- **Auto Cleanup**: Configurable file retention policies

### =� Development Features
- **Type Safety**: Full type hints with Pydantic models
- **Error Handling**: Comprehensive error handling and logging
- **Configuration**: Environment-based configuration management
- **Testing**: Pytest-based test suite with async support

## Quick Start

### Prerequisites

- Python 3.10+
- [UV package manager](https://docs.astral.sh/uv/)
- OpenAI API key

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd gpt-image-mcp
   uv sync
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Test the setup**:
   ```bash
   python scripts/dev.py setup
   python scripts/dev.py test
   ```

### Running the Server

#### Development Mode
```bash
# Run with MCP Inspector for testing
uv run mcp dev gpt_image_mcp/server.py

# Or run directly
python scripts/dev.py server
```

#### Claude Desktop Integration
```bash
# Install for Claude Desktop
uv run mcp install gpt_image_mcp/server.py --name "GPT Image Server"
```

## Usage Examples

### Basic Image Generation

```python
# Use via MCP client
result = await session.call_tool(
    "generate_image",
    arguments={
        "prompt": "A beautiful sunset over mountains, digital art style",
        "quality": "high",
        "size": "1536x1024",
        "style": "vivid"
    }
)
```

### Using Prompt Templates

```python
# Get optimized prompt for social media
prompt_result = await session.get_prompt(
    "social_media_prompt",
    arguments={
        "platform": "instagram",
        "content_type": "product announcement",
        "brand_style": "modern minimalist"
    }
)
```

### Accessing Generated Images

```python
# Access via resource URI
image_data = await session.read_resource("generated-images://img_20250630143022_abc123")

# Check recent images
history = await session.read_resource("image-history://recent?limit=5")

# Storage statistics
stats = await session.read_resource("storage-stats://overview")
```

## Available Tools

### `generate_image`
Generate images from text descriptions.

**Parameters**:
- `prompt` (required): Text description of desired image
- `quality`: "auto" | "high" | "medium" | "low" (default: "auto")
- `size`: "1024x1024" | "1536x1024" | "1024x1536" (default: "1536x1024")
- `style`: "vivid" | "natural" (default: "vivid")
- `output_format`: "png" | "jpeg" | "webp" (default: "png")
- `background`: "auto" | "transparent" | "opaque" (default: "auto")

### `edit_image`
Edit existing images with text instructions.

**Parameters**:
- `image_data` (required): Base64 encoded image or data URL
- `prompt` (required): Edit instructions
- `mask_data`: Optional mask for targeted editing
- `size`, `quality`, `output_format`: Same as generate_image

## Available Resources

- `generated-images://{image_id}` - Access specific generated images
- `image-history://recent` - Browse recent generation history
- `storage-stats://overview` - Storage usage and statistics
- `model-info://gpt-image-1` - Model capabilities and pricing

## Prompt Templates

Built-in templates for common use cases:

- **Creative Image**: Artistic image generation
- **Product Photography**: Commercial product images
- **Social Media Graphics**: Platform-optimized posts
- **Blog Headers**: Article header images
- **OG Images**: Social media preview images
- **Hero Banners**: Website hero sections
- **Email Headers**: Newsletter headers
- **Video Thumbnails**: YouTube/video thumbnails
- **Infographics**: Data visualization images
- **Artistic Style**: Specific art movement styles

## Configuration

Configure via environment variables or `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Optional - Image Defaults
DEFAULT_QUALITY=auto
DEFAULT_SIZE=1536x1024
DEFAULT_STYLE=vivid
MODERATION_LEVEL=auto

# Storage Settings
STORAGE_BASE_PATH=./storage
STORAGE_RETENTION_DAYS=30
STORAGE_MAX_SIZE_GB=10

# Caching
CACHE_ENABLED=true
CACHE_TTL_HOURS=24
MAX_CACHE_SIZE_MB=500

# Server
SERVER_PORT=3001
LOG_LEVEL=INFO
RATE_LIMIT_RPM=50
```

## Development

### Setup Development Environment
```bash
python scripts/dev.py setup
```

### Run Tests
```bash
python scripts/dev.py test
```

### Code Quality
```bash
python scripts/dev.py lint     # Check code quality
python scripts/dev.py format   # Format code
```

### Example Usage
```bash
python scripts/dev.py example  # Run example client
```

## Architecture

The server follows a modular architecture:

- **Core Server**: FastMCP-based MCP server implementation
- **OpenAI Integration**: Robust API client with retry logic
- **Storage Manager**: Organized local image storage
- **Cache Manager**: Memory-based caching system
- **Tool Layer**: Image generation and editing tools
- **Resource Layer**: MCP resources for data access
- **Prompt Layer**: Template system for optimized prompts

## Cost Estimation

The server provides cost estimation for operations:

- **Text Input**: ~$5 per 1M tokens
- **Image Output**: ~$40 per 1M tokens (~1750 tokens per image)
- **Typical Cost**: ~$0.07 per image generation

## Error Handling

Comprehensive error handling includes:

- API rate limiting and retries
- Invalid parameter validation
- Storage error recovery
- Cache failure fallbacks
- Detailed error logging

## Security

Security features include:

- OpenAI API key protection
- Input validation and sanitization
- File system access controls
- Rate limiting protection
- No credential exposure in logs

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Support

For issues and questions:

1. Check the [troubleshooting guide](docs/troubleshooting.md)
2. Review [common issues](docs/common-issues.md)
3. Open an issue on GitHub

---

**Built with d using the Model Context Protocol and OpenAI's gpt-image-1**