# Environment Variables Configuration

## Overview
This document describes the standardized environment variable naming conventions for the GPT Image MCP Server, following Pydantic BaseSettings best practices.

## Naming Convention
Environment variables use the pattern: `SECTION__FIELD_NAME` where `__` is the nested delimiter.

## Available Environment Variables

### OpenAI Configuration
- `OPENAI__API_KEY` (required) - OpenAI API key
- `OPENAI__ORGANIZATION` (optional) - OpenAI organization ID  
- `OPENAI__BASE_URL` (default: "https://api.openai.com/v1") - OpenAI API base URL
- `OPENAI__TIMEOUT` (default: 300.0) - Request timeout in seconds
- `OPENAI__MAX_RETRIES` (default: 3) - Maximum number of retries

### Image Generation Settings
- `IMAGES__DEFAULT_MODEL` (default: "gpt-image-1") - Default image model
- `IMAGES__DEFAULT_QUALITY` (default: "auto") - Default quality: auto, high, medium, low
- `IMAGES__DEFAULT_SIZE` (default: "1536x1024") - Default size: 1024x1024, 1536x1024, 1024x1536
- `IMAGES__DEFAULT_STYLE` (default: "vivid") - Default style: vivid, natural
- `IMAGES__DEFAULT_MODERATION` (default: "auto") - Default moderation: auto, low
- `IMAGES__DEFAULT_OUTPUT_FORMAT` (default: "png") - Default format: png, jpeg, webp
- `IMAGES__DEFAULT_COMPRESSION` (default: 100) - Default compression level (0-100)

### Storage Configuration
- `STORAGE__BASE_PATH` (default: "./storage") - Base storage directory
- `STORAGE__RETENTION_DAYS` (default: 30) - File retention period in days
- `STORAGE__MAX_SIZE_GB` (default: 10.0) - Maximum storage size in GB
- `STORAGE__CLEANUP_INTERVAL_HOURS` (default: 24) - Cleanup interval in hours
- `STORAGE__CREATE_SUBDIRECTORIES` (default: true) - Create date-based subdirectories
- `STORAGE__FILE_PERMISSIONS` (default: "644") - File permissions in octal

### Cache Configuration
- `CACHE__ENABLED` (default: true) - Enable caching
- `CACHE__TTL_HOURS` (default: 24) - Cache TTL in hours
- `CACHE__BACKEND` (default: "memory") - Cache backend: memory, redis
- `CACHE__MAX_SIZE_MB` (default: 500) - Maximum cache size in MB
- `CACHE__REDIS_URL` (optional) - Redis connection URL

### Server Configuration
- `SERVER__NAME` (default: "GPT Image MCP Server") - Server name
- `SERVER__VERSION` (default: "0.1.0") - Server version
- `SERVER__PORT` (default: 3001) - Server port
- `SERVER__HOST` (default: "127.0.0.1") - Server host
- `SERVER__LOG_LEVEL` (default: "INFO") - Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `SERVER__RATE_LIMIT_RPM` (default: 50) - Rate limit requests per minute

## Example .env File

```bash
# Required
OPENAI__API_KEY=sk-your-api-key-here

# Optional overrides
IMAGES__DEFAULT_QUALITY=high
IMAGES__DEFAULT_SIZE=1024x1024
STORAGE__BASE_PATH=/var/storage/images
CACHE__BACKEND=redis
CACHE__REDIS_URL=redis://localhost:6379
SERVER__LOG_LEVEL=DEBUG
```

## Migration from Old Environment Variables

If you're migrating from the previous manual environment variable system, update your configuration:

| Old Variable | New Variable |
|--------------|--------------|
| `OPENAI_API_KEY` | `OPENAI__API_KEY` |
| `DEFAULT_QUALITY` | `IMAGES__DEFAULT_QUALITY` |
| `DEFAULT_SIZE` | `IMAGES__DEFAULT_SIZE` |
| `STORAGE_BASE_PATH` | `STORAGE__BASE_PATH` |
| `CACHE_ENABLED` | `CACHE__ENABLED` |
| `SERVER_PORT` | `SERVER__PORT` |
| `SERVER_HOST` | `SERVER__HOST` |
| `LOG_LEVEL` | `SERVER__LOG_LEVEL` |

## Best Practices

1. **Use .env files** for development environments
2. **Set environment variables** directly in production
3. **Never commit .env files** containing secrets to version control
4. **Use the nested delimiter** `__` for organized configuration
5. **Follow boolean conventions** - use "true"/"false" strings for boolean values