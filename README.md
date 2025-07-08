# GPT Image MCP Server

An MCP (Model Context Protocol) server that integrates with OpenAI's gpt-image-1 model for text-to-image generation services.

> **📦 Package Manager**: This project uses [UV](https://docs.astral.sh/uv/) for fast, reliable Python package management. UV provides better dependency resolution, faster installs, and proper environment isolation compared to traditional pip/venv workflows.

## Features

### 🎨 Image Generation
- **Text-to-Image**: Generate high-quality images from text descriptions using gpt-image-1
- **Image Editing**: Edit existing images with text instructions
- **Multiple Formats**: Support for PNG, JPEG, and WebP output formats
- **Quality Control**: Auto, high, medium, and low quality settings
- **Background Control**: Transparent, opaque, or auto background options

### 🔗 MCP Integration
- **FastMCP Framework**: Built with the latest MCP Python SDK
- **Multiple Transports**: STDIO, HTTP, and SSE transport support
- **Structured Output**: Validated tool responses with proper schemas
- **Resource Access**: MCP resources for image retrieval and management
- **Prompt Templates**: 10+ built-in templates for common use cases

### 💾 Storage & Caching
- **Local Storage**: Organized directory structure with metadata
- **URL-based Access**: Transport-aware URL generation for images
- **Dual Access**: Immediate base64 data + persistent resource URIs
- **Smart Caching**: Memory-based caching with TTL and Redis support
- **Auto Cleanup**: Configurable file retention policies

### 🚀 Production Deployment
- **Docker Support**: Production-ready Docker containers
- **Multi-Transport**: STDIO for Claude Desktop, HTTP for web deployment
- **Reverse Proxy**: Nginx configuration with rate limiting
- **Monitoring**: Grafana and Prometheus integration
- **SSL/TLS**: Automatic certificate management with Certbot

### 🛠️ Development Features
- **Type Safety**: Full type hints with Pydantic models
- **Error Handling**: Comprehensive error handling and logging
- **Configuration**: Environment-based configuration management
- **Testing**: Pytest-based test suite with async support
- **Dev Tools**: Hot reload, Redis Commander, debug logging

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

   > **Note**: This project uses [UV](https://docs.astral.sh/uv/) for fast, reliable Python package management. UV provides better dependency resolution and faster installs compared to pip.

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Test the setup**:
   ```bash
   uv run python scripts/dev.py setup
   uv run python scripts/dev.py test
   ```

### Running the Server

#### Development Mode
```bash
# HTTP transport for web development and testing
./run.sh dev

# HTTP transport with development tools (Redis Commander)
./run.sh dev --tools

# STDIO transport for Claude Desktop integration  
./run.sh stdio

# Production deployment with monitoring
./run.sh prod
```

#### Manual Execution
```bash
# STDIO transport (default) - for Claude Desktop
uv run python -m gpt_image_mcp.server

# HTTP transport - for web deployment
uv run python -m gpt_image_mcp.server --transport streamable-http --port 3001

# SSE transport - for real-time applications
uv run python -m gpt_image_mcp.server --transport sse --port 8080

# With custom configuration
uv run python -m gpt_image_mcp.server --config /path/to/.env --log-level DEBUG

# Enable CORS for web development
uv run python -m gpt_image_mcp.server --transport streamable-http --cors
```

#### Command Line Options
```bash
uv run python -m gpt_image_mcp.server --help

GPT Image MCP Server - Generate and edit images using OpenAI's gpt-image-1 model

options:
  --config PATH         Path to configuration file (.env format)
  --log-level LEVEL     Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --transport TYPE      Transport method (stdio, sse, streamable-http)
  --port PORT          Port for HTTP transports (default: 3001)
  --host HOST          Host address for HTTP transports (default: 127.0.0.1)
  --cors               Enable CORS for web deployments
  --version            Show version information
  --help               Show help message

Examples:
  # Claude Desktop integration
  uv run python -m gpt_image_mcp.server

  # Web deployment with Redis cache
  uv run python -m gpt_image_mcp.server --transport streamable-http --port 3001

  # Development with debug logging and tools
  uv run python -m gpt_image_mcp.server --log-level DEBUG --cors
```

#### Claude Desktop Integration
```bash
# Option 1: Using UV (Recommended)
# Add to Claude Desktop configuration:
{
  "mcpServers": {
    "gpt-image-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/gpt-image-mcp",
        "run",
        "gpt-image-mcp"
      ],
      "env": {
        "OPENAI_API_KEY": "your-api-key-here"
      }
    }
  }
}

# Option 2: Using Python directly
{
  "mcpServers": {
    "gpt-image-mcp": {
      "command": "python",
      "args": ["-m", "gpt_image_mcp.server"],
      "cwd": "/path/to/gpt-image-mcp",
      "env": {
        "OPENAI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

> **Recommended**: Use the UV approach (Option 1) as it ensures proper dependency management and isolation.

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
# =============================================================================
# OpenAI Configuration (Required)
# =============================================================================
OPENAI__API_KEY=sk-your-api-key-here
OPENAI__BASE_URL=https://api.openai.com/v1
OPENAI__ORGANIZATION=org-your-org-id
OPENAI__TIMEOUT=300.0
OPENAI__MAX_RETRIES=3

# =============================================================================
# Image Generation Settings
# =============================================================================
IMAGES__DEFAULT_MODEL=gpt-image-1
IMAGES__DEFAULT_QUALITY=auto
IMAGES__DEFAULT_SIZE=1536x1024
IMAGES__DEFAULT_STYLE=vivid
IMAGES__DEFAULT_MODERATION=auto
IMAGES__DEFAULT_OUTPUT_FORMAT=png
# Base URL for image hosting (e.g., https://cdn.example.com for nginx/CDN)
IMAGES__BASE_HOST=

# =============================================================================
# Server Configuration
# =============================================================================
SERVER__NAME=GPT Image MCP Server
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

# =============================================================================
# Cache Configuration
# =============================================================================
CACHE__ENABLED=true
CACHE__TTL_HOURS=24
CACHE__BACKEND=memory
CACHE__MAX_SIZE_MB=500
# CACHE__REDIS_URL=redis://localhost:6379
```

## Deployment

### Production Deployment

The server supports production deployment with Docker, monitoring, and reverse proxy:

```bash
# Quick production deployment
./run.sh prod

# Manual Docker Compose deployment
docker-compose -f docker-compose.prod.yml up -d
```

**Production Stack includes:**
- **GPT Image MCP Server**: Main application container
- **Redis**: Caching and session storage
- **Nginx**: Reverse proxy with rate limiting (configured separately)
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards

**Access Points:**
- Main Service: `http://localhost:3001` (behind proxy)
- Grafana Dashboard: `http://localhost:3000`
- Prometheus: `http://localhost:9090` (localhost only)

### VPS Deployment

For VPS deployment with SSL, monitoring, and production hardening:

```bash
# Download deployment script
wget https://raw.githubusercontent.com/your-repo/gpt-image-mcp/main/deploy/vps-setup.sh
chmod +x vps-setup.sh
./vps-setup.sh
```

Features included:
- Docker containerization
- Nginx reverse proxy with SSL
- Automatic certificate management (Certbot)
- System monitoring and logging
- Firewall configuration
- Automatic backups

See [VPS Deployment Guide](deploy/VPS_DEPLOYMENT_GUIDE.md) for detailed instructions.

### Docker Configuration

Available Docker Compose profiles:

```bash
# Development with HTTP transport
docker-compose -f docker-compose.dev.yml up

# Development with Redis Commander
docker-compose -f docker-compose.dev.yml --profile tools up

# STDIO transport for desktop integration
docker-compose -f docker-compose.dev.yml --profile stdio up

# Production with monitoring
docker-compose -f docker-compose.prod.yml up -d
```

## Development

### Development Tools
```bash
# Setup development environment
uv run python scripts/dev.py setup

# Run tests
uv run python scripts/dev.py test

# Code quality and formatting
uv run python scripts/dev.py lint     # Check code quality with ruff and mypy
uv run python scripts/dev.py format   # Format code with black

# Run example client
uv run python scripts/dev.py example

# Development server with auto-reload
./run.sh dev --tools           # Includes Redis Commander UI
```

### Testing
```bash
# Run full test suite
./run.sh test

# Run specific test categories
uv run pytest tests/unit/      # Unit tests only
uv run pytest tests/integration/ # Integration tests only
uv run pytest -v --cov=gpt_image_mcp # With coverage
```

## Architecture

The server follows a modular, production-ready architecture:

**Core Components:**
- **Server Layer** (`server.py`): FastMCP-based MCP server with multi-transport support
- **Configuration** (`config/`): Environment-based settings management with validation
- **Tool Layer** (`tools/`): Image generation and editing capabilities
- **Resource Layer** (`resources/`): MCP resources for data access and model registry
- **Storage Manager** (`storage/`): Organized local image storage with cleanup
- **Cache Manager** (`utils/cache.py`): Memory and Redis-based caching system

**Infrastructure:**
- **OpenAI Integration** (`utils/openai_client.py`): Robust API client with retry logic
- **Prompt Templates** (`prompts/`): Template system for optimized prompts
- **Type System** (`types/`): Pydantic models for type safety
- **Validation** (`utils/validators.py`): Input validation and sanitization

**Deployment:**
- **Docker Support**: Development and production containers
- **Multi-Transport**: STDIO, HTTP, SSE transport layers
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Reverse Proxy**: Nginx configuration with SSL and rate limiting

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