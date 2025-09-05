# Adding New Models to the Registry

This document explains how to add new AI models to the MCP server's model registry.

## Model Configuration Structure

Each model is defined by a JSON configuration file in `./image_gen_mcp/resources/models/`. The file should be named `{model_id}.json` where `model_id` is the unique identifier for the model.

## Configuration Fields

```json
{
  "model_id": "unique-model-identifier",
  "name": "Human-readable Model Name",
  "version": "1.0",
  "capabilities": [
    "List of model capabilities",
    "Each capability as a string"
  ],
  "pricing": {
    "pricing_type": "price description",
    "another_pricing_type": "another price description"
  },
  "rate_limits": {
    "default": "rate limit description",
    "configurable": "configuration info"
  },
  "size_options": [
    "1024x1024",
    "1536x1024 (landscape)"
  ],
  "quality_levels": [
    "auto",
    "high",
    "medium",
    "low"
  ],
  "formats": [
    "PNG",
    "JPEG",
    "WebP"
  ],
  "features": {
    "feature_name": "feature description",
    "another_feature": "another description"
  },
  "best_practices": [
    "Best practice recommendations",
    "Usage guidelines"
  ],
  "examples": [
    "Example usage patterns",
    "Sample API calls"
  ]
}
```

## Adding a New Model

1. Create a new JSON file in `./image_gen_mcp/resources/models/`
2. Name it `{model_id}.json` (e.g., `dalle-3.json`)
3. Fill in all required fields
4. The model will be automatically available via the resource URIs

## Resource URIs

Once configured, models are accessible via:

- `model-info://{model_id}` - Get detailed documentation for a specific model
- `models://list` - List all available models

## Examples

### GPT-Image-1 (existing)
```
model-info://gpt-image-1
```

### DALL-E 3 (example)
```
model-info://dalle-3
```

### List All Models
```
models://list
```

## Custom Documentation

For more detailed documentation, you can also create a `{model_id}.md` file alongside the JSON configuration. This will be used instead of the auto-generated documentation.

## Programmatic Registration

You can also register models programmatically using the `model_registry`:

```python
from image_gen_mcp.resources.model_registry import model_registry, ModelInfo

new_model = ModelInfo(
    model_id="my-model",
    name="My Model",
    version="1.0",
    capabilities=["capability1", "capability2"],
    pricing={"generation": "$0.01 per image"},
    rate_limits={"default": "100 requests per minute"},
    size_options=["1024x1024"],
    quality_levels=["standard", "high"],
    formats=["PNG"],
    features={"feature1": "description"},
    best_practices=["practice1", "practice2"],
    examples=["example1", "example2"]
)

model_registry.register_model(new_model)
```
