"""Model information and metadata for different AI models."""

import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import aiofiles


@dataclass
class ModelInfo:
    """Model information structure."""

    model_id: str
    name: str
    version: str
    capabilities: list[str]
    pricing: dict[str, Any]
    rate_limits: dict[str, Any]
    size_options: list[str]
    quality_levels: list[str]
    formats: list[str]
    features: dict[str, Any]
    best_practices: list[str]
    examples: list[str]


class ModelRegistry:
    """Registry for managing different AI model information with caching."""

    def __init__(self, models_dir: Optional[Path] = None):
        """Initialize the model registry.

        Args:
            models_dir: Directory containing model configuration files.
        """
        if models_dir is None:
            models_dir = Path(__file__).parent / "models"

        self.models_dir = Path(models_dir)
        self._model_cache: dict[str, ModelInfo] = {}
        self._documentation_cache: dict[str, str] = {}
        self._cache_lock = asyncio.Lock()

        # Ensure models directory exists
        self.models_dir.mkdir(exist_ok=True)

    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get model information by ID with caching.

        Args:
            model_id: The model identifier (e.g., 'gpt-image-1')

        Returns:
            ModelInfo object or None if not found
        """
        # Check cache first
        async with self._cache_lock:
            if model_id in self._model_cache:
                return self._model_cache[model_id]

        # Try to load from file
        model_file = self.models_dir / f"{model_id}.json"
        if model_file.exists():
            try:
                async with aiofiles.open(model_file, encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)

                model_info = ModelInfo(**data)

                # Cache the loaded model
                async with self._cache_lock:
                    self._model_cache[model_id] = model_info

                return model_info

            except Exception as e:
                print(f"Error loading model {model_id}: {e}")
                return None

        return None

    async def register_model(self, model_info: ModelInfo) -> None:
        """Register a new model or update existing model information.

        Args:
            model_info: The model information to register
        """
        # Cache the model info
        async with self._cache_lock:
            self._model_cache[model_info.model_id] = model_info
            # Clear documentation cache for this model
            self._documentation_cache.pop(model_info.model_id, None)

        # Save to file
        model_file = self.models_dir / f"{model_info.model_id}.json"
        async with aiofiles.open(model_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(asdict(model_info), indent=2, ensure_ascii=False))

    async def list_models(self) -> list[str]:
        """List all available model IDs."""
        model_files = list(self.models_dir.glob("*.json"))
        return [f.stem for f in model_files]

    async def get_model_documentation(self, model_id: str) -> str:
        """Get formatted documentation for a model with proper error handling.

        Args:
            model_id: The model identifier

        Returns:
            Formatted markdown documentation (includes 'not found' message if
            model doesn't exist)
        """
        # Check documentation cache first
        async with self._cache_lock:
            if model_id in self._documentation_cache:
                return self._documentation_cache[model_id]

        model_info = await self.get_model_info(model_id)

        if not model_info:
            # Return helpful error message with available models
            available_models = await self.list_models()
            error_doc = f"""# Model Not Found

The model `{model_id}` is not available.

## Available Models
{chr(10).join(f"- {model}" for model in available_models)}

## Usage
Use the resource URI format: `model-info://{{model_id}}`

Examples:
- `model-info://gpt-image-1`
- `model-info://dalle-3`
"""
            return error_doc

        # Check for custom documentation file
        doc_file = self.models_dir / f"{model_id}.md"
        if doc_file.exists():
            try:
                async with aiofiles.open(doc_file, encoding="utf-8") as f:
                    doc_content = await f.read()

                # Cache the documentation
                async with self._cache_lock:
                    self._documentation_cache[model_id] = doc_content

                return doc_content
            except Exception as e:
                print(f"Error reading custom documentation for {model_id}: {e}")
                # Fall through to auto-generated documentation

        # Generate documentation from model info
        generated_doc = self._generate_documentation(model_info)

        # Cache the generated documentation
        async with self._cache_lock:
            self._documentation_cache[model_id] = generated_doc

        return generated_doc

    def _generate_documentation(self, model_info: ModelInfo) -> str:
        """Generate markdown documentation from model info."""
        doc = f"""# {model_info.name}

**Model ID:** `{model_info.model_id}`
**Version:** {model_info.version}

## Capabilities
{chr(10).join(f"- {cap}" for cap in model_info.capabilities)}

## Pricing
"""

        for key, value in model_info.pricing.items():
            doc += f"- **{key.replace('_', ' ').title()}**: {value}\n"

        doc += "\n## Rate Limits\n"
        for key, value in model_info.rate_limits.items():
            doc += f"- **{key.replace('_', ' ').title()}**: {value}\n"

        doc += "\n## Size Options\n"
        doc += f"{chr(10).join(f'- {size}' for size in model_info.size_options)}\n"

        doc += "\n## Quality Levels\n"
        doc += (
            f"{chr(10).join(f'- {quality}' for quality in model_info.quality_levels)}\n"
        )

        doc += "\n## Supported Formats\n"
        doc += f"{chr(10).join(f'- {fmt}' for fmt in model_info.formats)}\n"

        if model_info.features:
            doc += "\n## Features\n"
            for key, value in model_info.features.items():
                doc += f"- **{key.replace('_', ' ').title()}**: {value}\n"

        if model_info.best_practices:
            doc += "\n## Best Practices\n"
            doc += (
                f"{chr(10).join(f'- {practice}' for practice in model_info.best_practices)}\n"
            )

        if model_info.examples:
            doc += "\n## Examples\n"
            doc += (
                f"{chr(10).join(f'- {example}' for example in model_info.examples)}\n"
            )

        return doc

    async def clear_cache(self) -> None:
        """Clear all cached data."""
        async with self._cache_lock:
            self._model_cache.clear()
            self._documentation_cache.clear()

    async def reload_model(self, model_id: str) -> Optional[ModelInfo]:
        """Reload a specific model from disk, bypassing cache.

        Args:
            model_id: The model identifier to reload

        Returns:
            Reloaded ModelInfo or None if not found
        """
        # Clear caches for this model
        async with self._cache_lock:
            self._model_cache.pop(model_id, None)
            self._documentation_cache.pop(model_id, None)

        # Load fresh from disk
        return await self.get_model_info(model_id)

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "models_cached": len(self._model_cache),
            "documentation_cached": len(self._documentation_cache),
            "cached_models": list(self._model_cache.keys()),
        }


# Global model registry instance
model_registry = ModelRegistry()
