"""Unified template loader and manager for JSON-based templates."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TemplateParameter:
    """Template parameter definition."""

    name: str
    type: str
    required: bool
    description: str
    default: Optional[Any] = None
    examples: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    enum: list[str] = field(default_factory=list)
    max_length: Optional[int] = None


@dataclass
class TemplateMetadata:
    """Template metadata."""

    recommended_size: str
    quality: str
    style: str


@dataclass
class TemplateExample:
    """Template usage example."""

    input: dict[str, Any]
    output: str


@dataclass
class Template:
    """Complete template definition."""

    id: str
    name: str
    title: str
    description: str
    category: str
    version: str
    template: str
    parameters: dict[str, TemplateParameter]
    metadata: TemplateMetadata
    examples: list[TemplateExample] = field(default_factory=list)
    conditional_parts: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class Category:
    """Template category definition."""

    name: str
    description: str
    icon: str


class TemplateLoader:
    """Loads and manages templates from JSON files."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize template loader.

        Args:
            data_dir: Directory containing template JSON files
        """
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"

        self.data_dir = Path(data_dir)
        self.templates: dict[str, Template] = {}
        self.categories: dict[str, Category] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load templates from JSON file."""
        template_file = self.data_dir / "templates.json"

        if not template_file.exists():
            logger.warning(f"Template file not found: {template_file}")
            return

        try:
            with open(template_file, encoding="utf-8") as f:
                data = json.load(f)

            # Load categories
            for cat_id, cat_data in data.get("categories", {}).items():
                self.categories[cat_id] = Category(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    icon=cat_data.get("icon", ""),
                )

            # Load templates
            for template_id, template_data in data.get("templates", {}).items():
                self.templates[template_id] = self._parse_template(
                    template_id, template_data
                )

        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            raise

    def _parse_template(self, template_id: str, data: dict[str, Any]) -> Template:
        """Parse template data into Template object."""
        # Parse parameters
        parameters = {}
        for param_name, param_data in data.get("parameters", {}).items():
            parameters[param_name] = TemplateParameter(
                name=param_name,
                type=param_data.get("type", "string"),
                required=param_data.get("required", False),
                description=param_data.get("description", ""),
                default=param_data.get("default"),
                examples=param_data.get("examples", []),
                suggestions=param_data.get("suggestions", []),
                enum=param_data.get("enum", []),
                max_length=param_data.get("maxLength"),
            )

        # Parse metadata
        meta_data = data.get("metadata", {})
        metadata = TemplateMetadata(
            recommended_size=meta_data.get("recommended_size", "1024x1024"),
            quality=meta_data.get("quality", "high"),
            style=meta_data.get("style", "natural"),
        )

        # Parse examples
        examples = []
        for example_data in data.get("examples", []):
            examples.append(
                TemplateExample(
                    input=example_data["input"], output=example_data["output"]
                )
            )

        return Template(
            id=template_id,
            name=data.get("name", template_id),
            title=data["title"],
            description=data["description"],
            category=data["category"],
            version=data.get("version", "1.0"),
            template=data["template"],
            parameters=parameters,
            metadata=metadata,
            examples=examples,
            conditional_parts=data.get("conditional_parts", {}),
        )

    def get_template(self, template_id: str) -> Optional[Template]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def list_templates(self) -> list[Template]:
        """List all templates."""
        return list(self.templates.values())

    def list_template_ids(self) -> list[str]:
        """List all template IDs."""
        return list(self.templates.keys())

    def list_templates_by_category(self) -> dict[str, list[Template]]:
        """List templates organized by category."""
        by_category = {}
        for template in self.templates.values():
            if template.category not in by_category:
                by_category[template.category] = []
            by_category[template.category].append(template)

        # Sort templates within each category
        for templates in by_category.values():
            templates.sort(key=lambda t: t.id)

        return by_category

    def get_category(self, category_id: str) -> Optional[Category]:
        """Get category information."""
        return self.categories.get(category_id)

    def list_categories(self) -> dict[str, Category]:
        """List all categories."""
        return self.categories.copy()


class TemplateRenderer:
    """Renders templates with parameter values."""

    def __init__(self, template_loader: TemplateLoader):
        """Initialize renderer with template loader."""
        self.loader = template_loader

    def render(self, template_id: str, **kwargs) -> tuple[str, TemplateMetadata]:
        """Render a template with provided parameters.

        Args:
            template_id: ID of the template to render
            **kwargs: Parameter values

        Returns:
            Tuple of (rendered_text, metadata)

        Raises:
            ValueError: If template not found or required parameters missing
        """
        template = self.loader.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Validate required parameters
        for param_name, param in template.parameters.items():
            if param.required and param_name not in kwargs:
                raise ValueError(
                    f"Required parameter '{param_name}' missing for template "
                    f"'{template_id}'"
                )

        # Apply defaults
        render_kwargs = {}
        for param_name, param in template.parameters.items():
            if param_name in kwargs:
                render_kwargs[param_name] = kwargs[param_name]
            elif param.default is not None:
                render_kwargs[param_name] = param.default

        # Handle conditional parts
        self._apply_conditional_parts(template, render_kwargs)

        # Render template
        try:
            rendered = template.template.format(**render_kwargs)
            return rendered, template.metadata
        except KeyError as e:
            raise ValueError(f"Template rendering failed: missing key {e}")

    def _apply_conditional_parts(
        self, template: Template, kwargs: dict[str, Any]
    ) -> None:
        """Apply conditional template parts based on parameter values."""
        for part_name, part_config in template.conditional_parts.items():
            condition = part_config.get("condition", "")
            value = part_config.get("value", "")

            # Simple condition evaluation (can be enhanced)
            if self._evaluate_condition(condition, kwargs):
                # Apply the conditional value with parameter substitution
                kwargs[part_name] = value.format(**kwargs) if "{" in value else value
            else:
                kwargs[part_name] = ""

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate a simple condition.

        Note: This is a simple implementation. In production, consider
        using a proper expression evaluator for security.
        """
        if not condition:
            return False

        # Handle simple equality checks
        if "===" in condition:
            parts = condition.split("===")
            if len(parts) == 2:
                var_name = parts[0].strip()
                expected_value = parts[1].strip()

                # Handle boolean values
                if expected_value == "true":
                    expected_value = True
                elif expected_value == "false":
                    expected_value = False
                elif expected_value == "null":
                    expected_value = None
                else:
                    # Remove quotes if present
                    expected_value = expected_value.strip("'\"")

                actual_value = context.get(var_name)
                return actual_value == expected_value

        # Handle not-null checks
        if "!=" in condition and "null" in condition:
            var_name = condition.split("!=")[0].strip()
            return context.get(var_name) is not None

        return False


class UnifiedTemplateManager:
    """Unified manager for all template operations."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the unified template manager."""
        self.loader = TemplateLoader(data_dir)
        self.renderer = TemplateRenderer(self.loader)

    def get_template(self, template_id: str) -> Optional[Template]:
        """Get a template by ID."""
        return self.loader.get_template(template_id)

    def list_templates(self) -> list[dict[str, Any]]:
        """List all templates with summary information."""
        templates = []
        for template in self.loader.list_templates():
            templates.append(
                {
                    "id": template.id,
                    "name": template.name,
                    "title": template.title,
                    "description": template.description,
                    "category": template.category,
                    "parameter_count": len(template.parameters),
                    "has_examples": len(template.examples) > 0,
                }
            )
        return templates

    def list_templates_by_category(self) -> dict[str, list[dict[str, Any]]]:
        """List templates organized by category."""
        by_category = {}
        templates_by_cat = self.loader.list_templates_by_category()

        for category_id, templates in templates_by_cat.items():
            category = self.loader.get_category(category_id)
            if category:
                by_category[category_id] = {
                    "category": {
                        "id": category_id,
                        "name": category.name,
                        "description": category.description,
                        "icon": category.icon,
                    },
                    "templates": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "title": t.title,
                            "description": t.description,
                        }
                        for t in templates
                    ],
                }

        return by_category

    def get_template_details(self, template_id: str) -> Optional[dict[str, Any]]:
        """Get detailed information about a template."""
        template = self.loader.get_template(template_id)
        if not template:
            return None

        # Convert parameters to dict format (keep as dict with param names as keys)
        parameters = {}
        for param_name, param in template.parameters.items():
            param_dict = {
                "type": param.type,
                "required": param.required,
                "description": param.description,
            }
            if param.default is not None:
                param_dict["default"] = param.default
            if param.examples:
                param_dict["examples"] = param.examples
            if param.suggestions:
                param_dict["suggestions"] = param.suggestions
            if param.enum:
                param_dict["enum"] = param.enum
            if param.max_length:
                param_dict["maxLength"] = param.max_length

            parameters[param_name] = param_dict

        return {
            "id": template.id,
            "name": template.name,
            "title": template.title,
            "description": template.description,
            "category": template.category,
            "version": template.version,
            "template": template.template,
            "parameters": parameters,
            "metadata": {
                "recommended_size": template.metadata.recommended_size,
                "quality": template.metadata.quality,
                "style": template.metadata.style,
            },
            "examples": [
                {"input": ex.input, "output": ex.output} for ex in template.examples
            ],
        }

    def render_template(self, template_id: str, **kwargs) -> tuple[str, dict[str, Any]]:
        """Render a template with parameters."""
        rendered_text, metadata = self.renderer.render(template_id, **kwargs)
        return rendered_text, {
            "recommended_size": metadata.recommended_size,
            "quality": metadata.quality,
            "style": metadata.style,
        }

    def validate_parameters(
        self, template_id: str, parameters: dict[str, Any]
    ) -> list[str]:
        """Validate parameters for a template.

        Returns:
            List of validation error messages (empty if valid)
        """
        template = self.loader.get_template(template_id)
        if not template:
            return [f"Template '{template_id}' not found"]

        errors = []

        # Check required parameters
        for param_name, param in template.parameters.items():
            if param.required and param_name not in parameters:
                errors.append(f"Required parameter '{param_name}' is missing")

        # Validate parameter types and constraints
        for param_name, value in parameters.items():
            if param_name not in template.parameters:
                continue  # Skip unknown parameters

            param = template.parameters[param_name]

            # Type validation
            if param.type == "string" and not isinstance(value, str):
                errors.append(f"Parameter '{param_name}' must be a string")
            elif param.type == "boolean" and not isinstance(value, bool):
                errors.append(f"Parameter '{param_name}' must be a boolean")

            # Enum validation
            if param.enum and value not in param.enum:
                errors.append(
                    f"Parameter '{param_name}' must be one of: {', '.join(param.enum)}"
                )

            # Length validation
            if (
                param.max_length
                and isinstance(value, str)
                and len(value) > param.max_length
            ):
                errors.append(
                    f"Parameter '{param_name}' exceeds maximum length of "
                    f"{param.max_length}"
                )

        return errors


# Global instance
template_manager = UnifiedTemplateManager()
