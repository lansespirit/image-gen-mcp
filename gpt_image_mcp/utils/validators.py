"""Utility functions for parameter validation and fault tolerance."""

import logging
from typing import Any, Optional, TypeVar

from ..types.enums import (
    BackgroundType,
    ImageQuality,
    ImageSize,
    ImageStyle,
    ModerationLevel,
    OutputFormat,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def normalize_enum_value(
    value: Any,
    enum_class: type[T],
    default: Optional[T] = None,
    case_sensitive: bool = False,
) -> T:
    """
    Normalize and validate enum values with fault tolerance.

    Args:
        value: The input value to normalize
        enum_class: The enum class to validate against
        default: Default value if validation fails
        case_sensitive: Whether to perform case-sensitive matching

    Returns:
        A valid enum value

    Raises:
        ValueError: If value is invalid and no default is provided
    """
    if value is None:
        if default is not None:
            return default
        # Use the first enum value as fallback
        return next(iter(enum_class))

    # If already a valid enum instance, return as-is
    if isinstance(value, enum_class):
        return value

    # Convert to string for comparison
    str_value = str(value).strip()

    # Try exact match first (case-insensitive by default for robustness)
    for enum_member in enum_class:
        if (case_sensitive and enum_member.value == str_value) or (
            not case_sensitive and enum_member.value.lower() == str_value.lower()
        ):
            return enum_member

    # Try enum name match (case-insensitive)
    if not case_sensitive:
        str_value_upper = str_value.upper()
        for enum_member in enum_class:
            if enum_member.name.upper() == str_value_upper:
                return enum_member

    # Try partial matching for common variations
    if not case_sensitive:
        str_value_lower = str_value.lower()

        # Check common aliases first
        aliases = get_common_aliases(enum_class)
        if str_value_lower in aliases:
            target_value = aliases[str_value_lower]
            for enum_member in enum_class:
                if enum_member.value == target_value:
                    return enum_member

        for enum_member in enum_class:
            # Handle common size format variations
            if enum_class.__name__ == "ImageSize":
                if "x" in str_value_lower:
                    if enum_member.value == str_value_lower:
                        return enum_member
                elif str_value_lower in ["square", "1024", "1024x1024"]:
                    if enum_member.value == "1024x1024":
                        return enum_member
                elif str_value_lower in ["landscape", "wide", "1536x1024"]:
                    if enum_member.value == "1536x1024":
                        return enum_member
                elif str_value_lower in ["portrait", "tall", "1024x1536"]:
                    if enum_member.value == "1024x1536":
                        return enum_member

    # Log the invalid value with helpful suggestion
    valid_values = [e.value for e in enum_class]
    valid_names = [e.name.lower() for e in enum_class]

    logger.warning(
        f"Invalid {enum_class.__name__} value: '{value}'. "
        f"Valid values: {valid_values} or names: {valid_names}. "
        f"Using default: {default or next(iter(enum_class)).value}"
    )

    # Return default or first enum value
    return default or next(iter(enum_class))


def get_common_aliases(enum_class: type) -> dict[str, str]:
    """Get common aliases for enum values based on enum type."""

    aliases = {}

    if enum_class.__name__ == "ImageQuality":
        aliases.update(
            {
                # Standard quality aliases
                "standard": "high",
                "best": "high",
                "maximum": "high",
                "good": "medium",
                "normal": "medium",
                "average": "medium",
                "fast": "low",
                "quick": "low",
                "draft": "low",
                "preview": "low",
                # Numeric aliases
                "0": "auto",
                "1": "low",
                "2": "medium",
                "3": "high",
            }
        )

    elif enum_class.__name__ == "ImageStyle":
        aliases.update(
            {
                "realistic": "natural",
                "photo": "natural",
                "photographic": "natural",
                "bright": "vivid",
                "colorful": "vivid",
                "saturated": "vivid",
            }
        )

    elif enum_class.__name__ == "OutputFormat":
        aliases.update(
            {
                "jpg": "jpeg",
            }
        )

    elif enum_class.__name__ == "BackgroundType":
        aliases.update(
            {
                "none": "transparent",
                "clear": "transparent",
                "remove": "transparent",
                "solid": "opaque",
            }
        )

    return aliases


def validate_image_quality(value: Any) -> ImageQuality:
    """Validate and normalize image quality parameter."""
    return normalize_enum_value(value, ImageQuality, ImageQuality.AUTO)


def validate_image_size(value: Any) -> ImageSize:
    """Validate and normalize image size parameter."""
    return normalize_enum_value(value, ImageSize, ImageSize.LANDSCAPE)


def validate_image_style(value: Any) -> ImageStyle:
    """Validate and normalize image style parameter."""
    return normalize_enum_value(value, ImageStyle, ImageStyle.VIVID)


def validate_moderation_level(value: Any) -> ModerationLevel:
    """Validate and normalize moderation level parameter."""
    return normalize_enum_value(value, ModerationLevel, ModerationLevel.AUTO)


def validate_output_format(value: Any) -> OutputFormat:
    """Validate and normalize output format parameter."""
    return normalize_enum_value(value, OutputFormat, OutputFormat.PNG)


def validate_background_type(value: Any) -> BackgroundType:
    """Validate and normalize background type parameter."""
    return normalize_enum_value(value, BackgroundType, BackgroundType.AUTO)


def validate_compression(value: Any) -> int:
    """
    Validate and normalize compression parameter.

    Args:
        value: Compression value (0-100)

    Returns:
        Valid compression value between 0-100
    """
    if value is None:
        return 100

    try:
        compression = int(value)
        # Clamp to valid range
        compression = max(0, min(100, compression))
        return compression
    except (ValueError, TypeError):
        logger.warning(f"Invalid compression value: '{value}'. Using default: 100")
        return 100


def validate_limit(value: Any, max_limit: int = 100) -> int:
    """
    Validate and normalize limit parameter.

    Args:
        value: Limit value
        max_limit: Maximum allowed limit

    Returns:
        Valid limit value
    """
    if value is None:
        return 10  # Default limit

    try:
        limit = int(value)
        # Clamp to valid range
        limit = max(1, min(max_limit, limit))
        return limit
    except (ValueError, TypeError):
        logger.warning(f"Invalid limit value: '{value}'. Using default: 10")
        return 10


def validate_days(value: Any, max_days: int = 365) -> int:
    """
    Validate and normalize days parameter.

    Args:
        value: Days value
        max_days: Maximum allowed days

    Returns:
        Valid days value
    """
    if value is None:
        return 7  # Default days

    try:
        days = int(value)
        # Clamp to valid range
        days = max(1, min(max_days, days))
        return days
    except (ValueError, TypeError):
        logger.warning(f"Invalid days value: '{value}'. Using default: 7")
        return 7


def sanitize_prompt(prompt: str) -> str:
    """
    Sanitize and validate prompt text.

    Args:
        prompt: Input prompt text

    Returns:
        Sanitized prompt text

    Raises:
        ValueError: If prompt is empty or too long
    """
    if not prompt or not isinstance(prompt, str):
        raise ValueError("Prompt must be a non-empty string")

    # Strip whitespace
    prompt = prompt.strip()

    if not prompt:
        raise ValueError("Prompt cannot be empty")

    # Check length (OpenAI has limits)
    max_length = 4000  # Conservative limit
    if len(prompt) > max_length:
        logger.warning(
            f"Prompt truncated from {len(prompt)} to {max_length} characters"
        )
        prompt = prompt[:max_length]

    return prompt


def validate_base64_image(data: str) -> str:
    """
    Validate base64 image data.

    Args:
        data: Base64 encoded image data

    Returns:
        Validated base64 data

    Raises:
        ValueError: If data is invalid
    """
    if not data or not isinstance(data, str) or not data.strip():
        raise ValueError("Image data must be a non-empty string")

    import base64

    # If already a data URL, validate and return as is
    if data.startswith("data:"):
        try:
            prefix, b64 = data.split(",", 1)
            base64.b64decode(b64, validate=True)
            return data
        except Exception:
            raise ValueError("Invalid data URL")
    # If raw base64, validate and return as data URL
    try:
        base64.b64decode(data, validate=True)
        return f"data:image/png;base64,{data}"
    except Exception as e:
        raise ValueError(f"Invalid base64 image data: {e}")
