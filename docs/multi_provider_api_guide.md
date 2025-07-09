# Multi-Provider API Guide

This guide covers the image generation APIs supported by the Image Gen MCP Server, including OpenAI and Google Gemini providers.

## Overview

The Image Gen MCP Server supports multiple AI providers through a unified interface:

- **OpenAI Provider**: gpt-image-1, dall-e-3, dall-e-2
- **Gemini Provider**: imagen-4, imagen-4-ultra, imagen-3 (via OpenAI compatibility mode)

## OpenAI Images API

### Create Image

**Endpoint**: `POST https://api.openai.com/v1/images/generations`

Creates an image given a prompt.

#### Request Body

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | Text description of the desired image(s). Max 32000 characters for `gpt-image-1`, 1000 for `dall-e-2`, 4000 for `dall-e-3` |
| `model` | string | No | Model to use: `gpt-image-1`, `dall-e-3`, or `dall-e-2` (default) |
| `n` | integer | No | Number of images to generate (1-10). For `dall-e-3`, only `n=1` is supported |
| `size` | string | No | Image size. For `gpt-image-1`: `1024x1024`, `1536x1024`, `1024x1536`, or `auto` |
| `quality` | string | No | Image quality. For `gpt-image-1`: `auto`, `high`, `medium`, `low` |
| `style` | string | No | Style for `dall-e-3`: `vivid` or `natural` |
| `output_format` | string | No | Format for `gpt-image-1`: `png`, `jpeg`, or `webp` |
| `background` | string | No | Background for `gpt-image-1`: `transparent`, `opaque`, or `auto` |
| `moderation` | string | No | Moderation level for `gpt-image-1`: `auto` or `low` |

#### Example Request

```bash
curl https://api.openai.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-image-1",
    "prompt": "A cute baby sea otter",
    "n": 1,
    "size": "1024x1024"
  }'
```

### Create Image Edit

**Endpoint**: `POST https://api.openai.com/v1/images/edits`

Creates an edited or extended image given source images and a prompt. Only supports `gpt-image-1` and `dall-e-2`.

#### Request Body

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image` | file/array | Yes | Image(s) to edit. For `gpt-image-1`: up to 16 images, PNG/WEBP/JPG < 50MB |
| `prompt` | string | Yes | Edit instructions. Max 32000 characters for `gpt-image-1`, 1000 for `dall-e-2` |
| `model` | string | No | Model to use: `gpt-image-1` or `dall-e-2` (default) |
| `mask` | file | No | PNG mask file indicating areas to edit |
| `n` | integer | No | Number of images to generate (1-10) |
| `size` | string | No | Image size |
| `quality` | string | No | Image quality |
| `output_format` | string | No | Output format for `gpt-image-1` |
| `background` | string | No | Background setting for `gpt-image-1` |

## Google Gemini Images API (OpenAI Compatible)

### Create Image

**Endpoint**: `POST https://generativelanguage.googleapis.com/v1beta/openai/images/generations`

Creates an image using Google's Imagen models through OpenAI compatibility mode.

#### Request Body

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | Text description of the desired image |
| `model` | string | No | Model to use: `imagen-4`, `imagen-4-ultra`, or `imagen-3` |
| `n` | integer | No | Number of images to generate (1-8) |
| `aspectRatio` | string | No | Aspect ratio: `1:1`, `9:16`, `16:9`, `3:4`, `4:3` |
| `outputFormat` | string | No | Output format: `png`, `jpeg` |
| `safety` | string | No | Safety filter level: `strict`, `moderate`, `permissive` |

#### Example Request

```bash
curl https://generativelanguage.googleapis.com/v1beta/openai/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GEMINI_API_KEY" \
  -d '{
    "model": "imagen-4",
    "prompt": "A beautiful sunset over mountains",
    "n": 1,
    "aspectRatio": "16:9"
  }'
```

### Parameter Translation

The MCP server automatically translates parameters between different providers:

#### OpenAI → Gemini Translation

| OpenAI Parameter | Gemini Parameter | Translation |
|------------------|------------------|-------------|
| `size` | `aspectRatio` | `1024x1024` → `1:1`, `1536x1024` → `16:10`, `1024x1536` → `10:16` |
| `output_format` | `outputFormat` | Direct mapping |
| `quality` | `quality` | `high` → `premium`, `medium` → `standard`, `low` → `fast` |
| `style` | `stylePreset` | `vivid` → `enhance`, `natural` → `realistic` |

#### Gemini → OpenAI Translation

| Gemini Parameter | OpenAI Parameter | Translation |
|------------------|------------------|-------------|
| `aspectRatio` | `size` | `1:1` → `1024x1024`, `16:9` → `1536x1024`, `9:16` → `1024x1536` |
| `outputFormat` | `output_format` | Direct mapping |
| `safety` | `moderation` | `strict` → `auto`, `permissive` → `low` |

## Supported Models

### OpenAI Models

#### gpt-image-1
- **Capabilities**: Generation, Editing
- **Max Prompt**: 32,000 characters
- **Sizes**: 1024x1024, 1536x1024, 1024x1536, auto
- **Quality**: auto, high, medium, low
- **Formats**: png, jpeg, webp
- **Background**: transparent, opaque, auto
- **Moderation**: auto, low

#### dall-e-3
- **Capabilities**: Generation only
- **Max Prompt**: 4,000 characters
- **Sizes**: 1024x1024, 1792x1024, 1024x1792
- **Quality**: hd, standard
- **Style**: vivid, natural
- **Formats**: png, jpeg (via response_format)

#### dall-e-2
- **Capabilities**: Generation, Editing
- **Max Prompt**: 1,000 characters
- **Sizes**: 256x256, 512x512, 1024x1024
- **Quality**: standard only
- **Formats**: png, jpeg (via response_format)

### Gemini Models

#### imagen-4
- **Capabilities**: Generation only
- **Max Prompt**: No official limit
- **Aspect Ratios**: 1:1, 9:16, 16:9, 3:4, 4:3
- **Formats**: png, jpeg
- **Safety**: strict, moderate, permissive

#### imagen-4-ultra
- **Capabilities**: Generation only
- **Max Prompt**: No official limit
- **Aspect Ratios**: 1:1, 9:16, 16:9, 3:4, 4:3
- **Formats**: png, jpeg
- **Safety**: strict, moderate, permissive
- **Note**: Enhanced quality version of imagen-4

#### imagen-3
- **Capabilities**: Generation only
- **Max Prompt**: No official limit
- **Aspect Ratios**: 1:1, 9:16, 16:9
- **Formats**: png, jpeg
- **Safety**: strict, moderate, permissive

## Provider Configuration

### OpenAI Provider

```bash
PROVIDERS__OPENAI__API_KEY=sk-your-openai-api-key-here
PROVIDERS__OPENAI__BASE_URL=https://api.openai.com/v1
PROVIDERS__OPENAI__ORGANIZATION=org-your-org-id
PROVIDERS__OPENAI__TIMEOUT=300.0
PROVIDERS__OPENAI__MAX_RETRIES=3
PROVIDERS__OPENAI__ENABLED=true
```

### Gemini Provider

```bash
PROVIDERS__GEMINI__API_KEY=your-gemini-api-key-here
PROVIDERS__GEMINI__BASE_URL=https://generativelanguage.googleapis.com/v1beta/
PROVIDERS__GEMINI__TIMEOUT=300.0
PROVIDERS__GEMINI__MAX_RETRIES=3
PROVIDERS__GEMINI__ENABLED=true
PROVIDERS__GEMINI__DEFAULT_MODEL=imagen-4
```

## Usage Through MCP Server

### List Available Models

```python
# Query available models and their capabilities
models = await session.call_tool("list_available_models")
```

### Generate Image with Model Selection

```python
# Generate with OpenAI model
result = await session.call_tool("generate_image", {
    "prompt": "A beautiful sunset over mountains",
    "model": "gpt-image-1",
    "quality": "high",
    "size": "1536x1024"
})

# Generate with Gemini model
result = await session.call_tool("generate_image", {
    "prompt": "A beautiful sunset over mountains", 
    "model": "imagen-4",
    "quality": "high",
    "size": "1536x1024"  # Automatically translated to aspectRatio: "16:10"
})
```

### Edit Image (OpenAI only)

```python
# Edit image using OpenAI models
result = await session.call_tool("edit_image", {
    "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "prompt": "Add a rainbow to the sky",
    "model": "gpt-image-1"
})
```

## Error Handling

### Common Error Codes

- `400`: Bad request - invalid parameters
- `401`: Unauthorized - invalid API key
- `429`: Rate limit exceeded
- `500`: Internal server error

### Provider-Specific Errors

#### OpenAI Errors
- `content_policy_violation`: Prompt violates content policy
- `billing_hard_limit_reached`: Account billing limit reached
- `invalid_image`: Invalid image format or size

#### Gemini Errors
- `SAFETY_VIOLATION`: Content violates safety guidelines
- `QUOTA_EXCEEDED`: API quota exceeded
- `INVALID_ARGUMENT`: Invalid request parameters

## Best Practices

1. **Model Selection**: Choose models based on your specific needs:
   - **gpt-image-1**: Best overall quality and features
   - **dall-e-3**: Good for creative, artistic images
   - **imagen-4**: Alternative with different style characteristics

2. **Parameter Optimization**: Use appropriate parameters for each model:
   - Adjust quality based on output requirements
   - Choose appropriate sizes/aspect ratios
   - Set moderation levels according to use case

3. **Error Handling**: Implement retry logic with exponential backoff
4. **Rate Limiting**: Respect provider rate limits
5. **Cost Management**: Monitor token usage and costs

## Migration Guide

### From Single Provider to Multi-Provider

```python
# Before (single provider)
result = await session.call_tool("generate_image", {
    "prompt": "A sunset",
    "quality": "high"
})

# After (multi-provider)
# Query available models first
models = await session.call_tool("list_available_models")

# Generate with specific model
result = await session.call_tool("generate_image", {
    "prompt": "A sunset",
    "model": "gpt-image-1",  # or "imagen-4"
    "quality": "high"
})
```

This unified approach allows you to leverage the strengths of different AI providers while maintaining a consistent interface through the MCP server.