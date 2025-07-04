"""Test enum type definitions and MCP integration."""

import pytest
import json
from gpt_image_mcp.types.enums import (
    ImageQuality,
    ImageSize,
    ImageStyle,
    ModerationLevel,
    OutputFormat,
    BackgroundType,
)
from gpt_image_mcp.utils.validators import (
    normalize_enum_value,
    validate_image_quality,
    validate_image_size,
    validate_image_style,
    validate_compression,
    sanitize_prompt,
)


class TestEnumDefinitions:
    """Test enum properties and functionality."""
    
    def test_image_quality_enum(self):
        """Test ImageQuality enum properties."""
        assert ImageQuality.AUTO.value == "auto"
        assert ImageQuality.HIGH.description == "Maximum quality with higher token usage"
        assert isinstance(ImageQuality.AUTO, str)  # str mixin works
        assert ImageQuality.AUTO == "auto"  # Direct comparison works
    
    def test_image_size_properties(self):
        """Test ImageSize enum with additional properties."""
        landscape = ImageSize.LANDSCAPE
        assert landscape.width == 1536
        assert landscape.height == 1024
        assert landscape.aspect_ratio == 1.5
        assert landscape.description == "Landscape format (3:2 ratio)"
    
    def test_output_format_properties(self):
        """Test OutputFormat enum functionality."""
        png = OutputFormat.PNG
        assert png.supports_transparency is True
        assert png.mime_type == "image/png"
        
        jpeg = OutputFormat.JPEG
        assert jpeg.supports_transparency is False
        assert jpeg.mime_type == "image/jpeg"
    
    def test_background_compatibility(self):
        """Test background and format compatibility."""
        transparent = BackgroundType.TRANSPARENT
        assert transparent.is_compatible_with_format(OutputFormat.PNG) is True
        assert transparent.is_compatible_with_format(OutputFormat.JPEG) is False
        assert transparent.is_compatible_with_format(OutputFormat.WEBP) is True
        
        white = BackgroundType.WHITE
        assert white.is_compatible_with_format(OutputFormat.JPEG) is True


class TestValidatorFaultTolerance:
    """Test validator fault tolerance and normalization."""
    
    def test_enum_normalization_exact_match(self):
        """Test exact value matching."""
        assert normalize_enum_value("auto", ImageQuality) == ImageQuality.AUTO
        assert normalize_enum_value("high", ImageQuality) == ImageQuality.HIGH
    
    def test_enum_normalization_case_insensitive(self):
        """Test case-insensitive matching."""
        assert normalize_enum_value("AUTO", ImageQuality) == ImageQuality.AUTO
        assert normalize_enum_value("High", ImageQuality) == ImageQuality.HIGH
        assert normalize_enum_value("VIVID", ImageStyle) == ImageStyle.VIVID
    
    def test_enum_normalization_name_match(self):
        """Test enum name matching."""
        assert normalize_enum_value("LANDSCAPE", ImageSize) == ImageSize.LANDSCAPE
        assert normalize_enum_value("portrait", ImageSize) == ImageSize.PORTRAIT
    
    def test_enum_normalization_with_default(self):
        """Test fallback to default values."""
        assert normalize_enum_value("invalid", ImageQuality, ImageQuality.MEDIUM) == ImageQuality.MEDIUM
        assert normalize_enum_value(None, ImageQuality, ImageQuality.AUTO) == ImageQuality.AUTO
    
    def test_enum_normalization_special_cases(self):
        """Test special case handling for sizes."""
        # Size variations
        assert normalize_enum_value("square", ImageSize) == ImageSize.SQUARE
        assert normalize_enum_value("1024", ImageSize) == ImageSize.SQUARE
        assert normalize_enum_value("landscape", ImageSize) == ImageSize.LANDSCAPE
        assert normalize_enum_value("wide", ImageSize) == ImageSize.LANDSCAPE
        assert normalize_enum_value("tall", ImageSize) == ImageSize.PORTRAIT
    
    def test_already_enum_instance(self):
        """Test passing enum instances directly."""
        assert normalize_enum_value(ImageQuality.HIGH, ImageQuality) == ImageQuality.HIGH
        assert normalize_enum_value(ImageSize.SQUARE, ImageSize) == ImageSize.SQUARE


class TestSpecificValidators:
    """Test specific validator functions."""
    
    def test_validate_image_quality(self):
        """Test image quality validation."""
        assert validate_image_quality("high") == ImageQuality.HIGH
        assert validate_image_quality("MEDIUM") == ImageQuality.MEDIUM
        assert validate_image_quality("invalid") == ImageQuality.AUTO  # Default
        assert validate_image_quality(ImageQuality.LOW) == ImageQuality.LOW
    
    def test_validate_image_size(self):
        """Test image size validation."""
        assert validate_image_size("1536x1024") == ImageSize.LANDSCAPE
        assert validate_image_size("square") == ImageSize.SQUARE
        assert validate_image_size("portrait") == ImageSize.PORTRAIT
        assert validate_image_size("invalid") == ImageSize.LANDSCAPE  # Default
    
    def test_validate_compression(self):
        """Test compression validation."""
        assert validate_compression(50) == 50
        assert validate_compression(0) == 0
        assert validate_compression(100) == 100
        assert validate_compression(150) == 100  # Clamped to max
        assert validate_compression(-10) == 0  # Clamped to min
        assert validate_compression("50") == 50  # String conversion
        assert validate_compression("invalid") == 100  # Default
        assert validate_compression(None) == 100  # Default
    
    def test_sanitize_prompt(self):
        """Test prompt sanitization."""
        assert sanitize_prompt("  test prompt  ") == "test prompt"
        assert sanitize_prompt("valid prompt") == "valid prompt"
        
        # Test length limit
        long_prompt = "x" * 5000
        sanitized = sanitize_prompt(long_prompt)
        assert len(sanitized) == 4000
        
        # Test invalid inputs
        with pytest.raises(ValueError, match="non-empty string"):
            sanitize_prompt("")
        
        with pytest.raises(ValueError, match="non-empty string"):
            sanitize_prompt(None)
        
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_prompt("   ")


class TestMCPIntegration:
    """Test that enums work correctly with MCP schema generation."""
    
    def test_enum_json_serialization(self):
        """Test that enums serialize correctly for MCP."""
        # Enums should serialize to their string values
        assert json.dumps(ImageQuality.HIGH) == '"high"'
        assert json.dumps(ImageSize.LANDSCAPE) == '"1536x1024"'
        
        # Test in a dict (like MCP parameters)
        params = {
            "quality": ImageQuality.AUTO,
            "size": ImageSize.SQUARE,
            "style": ImageStyle.VIVID,
        }
        serialized = json.dumps(params)
        assert '"quality": "auto"' in serialized
        assert '"size": "1024x1024"' in serialized
        assert '"style": "vivid"' in serialized
    
    def test_enum_values_list(self):
        """Test getting all valid values for schema generation."""
        quality_values = [q.value for q in ImageQuality]
        assert set(quality_values) == {"auto", "high", "medium", "low"}
        
        size_values = [s.value for s in ImageSize]
        assert set(size_values) == {"1024x1024", "1536x1024", "1024x1536"}
        
        format_values = [f.value for f in OutputFormat]
        assert set(format_values) == {"png", "jpeg", "webp"}


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_normalize_with_empty_enum(self):
        """Test behavior with empty enum (edge case)."""
        # This shouldn't happen in practice, but test the fallback
        from enum import Enum
        
        class EmptyEnum(str, Enum):
            pass
        
        # Should raise StopIteration since there are no values
        with pytest.raises(StopIteration):
            normalize_enum_value("test", EmptyEnum)
    
    def test_validate_with_numeric_input(self):
        """Test validation with unexpected numeric inputs."""
        # Should handle gracefully
        assert validate_image_quality(123) == ImageQuality.AUTO
        assert validate_image_style(3.14) == ImageStyle.VIVID
    
    def test_special_string_formats(self):
        """Test handling of special string formats."""
        # Whitespace handling
        assert validate_image_quality("  high  ") == ImageQuality.HIGH
        assert validate_image_quality("\tauto\n") == ImageQuality.AUTO
        
        # Special characters (should fallback to default)
        assert validate_image_quality("high!@#") == ImageQuality.AUTO
        assert validate_image_style("vivid-style") == ImageStyle.VIVID  # Partial match might work


if __name__ == "__main__":
    pytest.main([__file__, "-v"])