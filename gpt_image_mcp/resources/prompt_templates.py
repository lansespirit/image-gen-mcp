"""Prompt template resource adapter for MCP resources."""

from typing import Any

from ..prompts.template_manager import template_manager


class PromptTemplateResourceManager:
    """Adapter for exposing prompt templates as MCP resources."""

    def __init__(self):
        """Initialize the resource manager with template manager."""
        self.template_manager = template_manager

    def list_templates(self) -> dict[str, Any]:
        """List all available prompt templates for MCP resource."""
        templates_by_category = self.template_manager.list_templates_by_category()

        # Convert to MCP resource format
        categories_with_templates = []
        all_templates = []
        total_templates = 0

        for category_id, category_data in templates_by_category.items():
            templates = category_data.get("templates", [])
            total_templates += len(templates)

            # Add resource URIs to each template
            for template in templates:
                template["resource_uri"] = f"prompt-templates://{template['id']}"
                all_templates.append(template)

            categories_with_templates.append(
                {"category": category_data["category"], "templates": templates}
            )

        return {
            "categories": categories_with_templates,
            "templates": all_templates,
            "total_templates": total_templates,
            "usage": {
                "description": (
                    "Use prompt-templates://{template_id} to get detailed "
                    "information about specific templates"
                ),
                "example": "prompt-templates://creative_image",
            },
        }

    def get_template_details(self, template_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific template."""
        details = self.template_manager.get_template_details(template_id)

        if details:
            # Add usage information for MCP
            details["usage"] = {
                "mcp_prompt_call": f"Use as MCP prompt: {template_id}",
                "parameter_format": (
                    "Pass parameters as specified in the parameters list"
                ),
                "example_calls": self._generate_example_calls(
                    template_id, details["parameters"]
                ),
            }

        return details

    def get_template_not_found_response(self, template_id: str) -> dict[str, Any]:
        """Get a helpful response when a template is not found."""
        available_templates = self.template_manager.loader.list_template_ids()

        # Find suggestions based on similarity
        suggestions = []
        template_lower = template_id.lower().replace("-", "_").replace("_prompt", "")

        for available in available_templates:
            available_lower = available.lower()
            if template_lower in available_lower or available_lower in template_lower:
                suggestions.append(available)

        return {
            "error": "Template Not Found",
            "message": f"The prompt template '{template_id}' is not available.",
            "available_templates": available_templates,
            "suggestions": suggestions[:3] if suggestions else available_templates[:3],
            "usage": {
                "description": (
                    "Use prompt-templates://list to see all available templates"
                ),
                "example": "prompt-templates://creative_image",
            },
        }

    def _generate_example_calls(self, template_id: str, parameters: dict) -> list[str]:
        """Generate example calls for a template."""
        if not parameters:
            return [f"{template_id}()"]

        # Generate example with first 2-3 parameters
        example_params = []
        param_items = list(parameters.items())[:3]  # Get first 3 parameters
        for i, (param_name, param) in enumerate(param_items):
            if param.get("required") or i < 2:
                value = (
                    param.get("examples", [param.get("default", "value")])[0]
                    if param.get("examples")
                    else param.get("default", "value")
                )
                if isinstance(value, str):
                    example_params.append(f"{param_name}='{value}'")
                else:
                    example_params.append(f"{param_name}={value}")

        return [f"{template_id}({', '.join(example_params)})"]


# Global instance
prompt_template_resource_manager = PromptTemplateResourceManager()
