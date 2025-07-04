"""Central registry for MCP prompt functions."""

from typing import List, Dict, Any, Callable
from mcp.server.fastmcp.prompts import base
from pydantic import Field

from .message_builders import MessageBuilder
from .templates import PromptTemplateManager


class PromptRegistry:
    """Central registry for managing MCP prompt functions."""
    
    def __init__(self):
        self.message_builder = MessageBuilder()
        self.template_manager = PromptTemplateManager()
    
    # Main prompt builders following MCP best practices
    def build_creative_prompt(
        self,
        subject: str,
        style: str = "digital art",
        mood: str = "vibrant",
        color_palette: str = "colorful"
    ) -> List[base.Message]:
        """Build creative image generation prompt with expert art direction."""
        return self.message_builder.build_creative_prompt(
            subject=subject,
            style=style, 
            mood=mood,
            color_palette=color_palette
        )
    
    def build_product_prompt(
        self,
        product: str,
        background: str = "white studio",
        lighting: str = "soft natural", 
        angle: str = "front view"
    ) -> List[base.Message]:
        """Build professional product photography prompt."""
        return self.message_builder.build_product_prompt(
            product=product,
            background=background,
            lighting=lighting,
            angle=angle
        )
    
    def build_social_media_prompt(
        self,
        platform: str,
        content_type: str,
        brand_style: str = "modern",
        call_to_action: bool = False
    ) -> List[base.Message]:
        """Build platform-optimized social media graphics prompt."""
        return self.message_builder.build_social_media_prompt(
            platform=platform,
            content_type=content_type,
            brand_style=brand_style,
            call_to_action=call_to_action
        )
    
    # Template-based prompt builders
    def build_artistic_style_prompt(
        self,
        subject: str,
        artist_style: str = "impressionist",
        medium: str = "oil painting",
        era: str = "modern"
    ) -> List[base.Message]:
        """Build artistic style generation prompt."""
        return self.message_builder.build_template_prompt(
            "artistic_style",
            subject=subject,
            artist_style=artist_style,
            medium=medium,
            era=era
        )
    
    def build_og_image_prompt(
        self,
        title: str,
        brand_name: str = None,
        background_style: str = "gradient",
        text_layout: str = "centered",
        color_scheme: str = "professional"
    ) -> List[base.Message]:
        """Build Open Graph image prompt."""
        kwargs = {
            "title": title,
            "background_style": background_style,
            "text_layout": text_layout,
            "color_scheme": color_scheme
        }
        if brand_name:
            kwargs["brand_name"] = brand_name
            
        return self.message_builder.build_template_prompt("og_image", **kwargs)
    
    def build_blog_header_prompt(
        self,
        topic: str,
        style: str = "modern",
        mood: str = "professional",
        include_text_space: bool = True
    ) -> List[base.Message]:
        """Build blog header image prompt."""
        return self.message_builder.build_template_prompt(
            "blog_header",
            topic=topic,
            style=style,
            mood=mood,
            include_text_space=include_text_space
        )
    
    def build_hero_banner_prompt(
        self,
        website_type: str,
        industry: str = None,
        message: str = None,
        visual_style: str = "modern"
    ) -> List[base.Message]:
        """Build website hero banner prompt."""
        kwargs = {
            "website_type": website_type,
            "visual_style": visual_style
        }
        if industry:
            kwargs["industry"] = industry
        if message:
            kwargs["message"] = message
            
        return self.message_builder.build_template_prompt("hero_banner", **kwargs)
    
    def build_thumbnail_prompt(
        self,
        content_type: str,
        topic: str,
        style: str = "bold",
        emotion: str = "exciting"
    ) -> List[base.Message]:
        """Build video thumbnail prompt."""
        return self.message_builder.build_template_prompt(
            "thumbnail",
            content_type=content_type,
            topic=topic,
            style=style,
            emotion=emotion
        )
    
    def build_infographic_prompt(
        self,
        data_type: str,
        topic: str,
        visual_approach: str = "modern",
        layout: str = "vertical"
    ) -> List[base.Message]:
        """Build infographic image prompt."""
        return self.message_builder.build_template_prompt(
            "infographic",
            data_type=data_type,
            topic=topic,
            visual_approach=visual_approach,
            layout=layout
        )
    
    def build_email_header_prompt(
        self,
        newsletter_type: str,
        brand_name: str = None,
        theme: str = None,
        season: str = None
    ) -> List[base.Message]:
        """Build email newsletter header prompt."""
        kwargs = {"newsletter_type": newsletter_type}
        if brand_name:
            kwargs["brand_name"] = brand_name
        if theme:
            kwargs["theme"] = theme  
        if season:
            kwargs["season"] = season
            
        return self.message_builder.build_template_prompt("email_header", **kwargs)
    
    # Utility methods
    def get_available_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get list of all available prompt types with their parameters."""
        return {
            "creative_image": {
                "title": "Creative Image Generation",
                "description": "Enhanced template for creative image generation with expert art direction",
                "parameters": ["subject", "style", "mood", "color_palette"]
            },
            "product_photography": {
                "title": "Product Photography", 
                "description": "Professional product photography prompt with commercial specifications",
                "parameters": ["product", "background", "lighting", "angle"]
            },
            "social_media": {
                "title": "Social Media Graphics",
                "description": "Platform-optimized social media graphics with engagement best practices", 
                "parameters": ["platform", "content_type", "brand_style", "call_to_action"]
            },
            "artistic_style": {
                "title": "Artistic Style Generation",
                "description": "Generate images in specific artistic styles and periods",
                "parameters": ["subject", "artist_style", "medium", "era"]
            },
            "og_image": {
                "title": "Open Graph Images",
                "description": "Social media preview images optimized for sharing",
                "parameters": ["title", "brand_name", "background_style", "text_layout", "color_scheme"]
            },
            "blog_header": {
                "title": "Blog Header Images", 
                "description": "Header images for blog posts and articles",
                "parameters": ["topic", "style", "mood", "include_text_space"]
            },
            "hero_banner": {
                "title": "Website Hero Banners",
                "description": "Hero section banners for websites",
                "parameters": ["website_type", "industry", "message", "visual_style"]
            },
            "thumbnail": {
                "title": "Video Thumbnails",
                "description": "Engaging thumbnails for video content",
                "parameters": ["content_type", "topic", "style", "emotion"]
            },
            "infographic": {
                "title": "Infographic Images",
                "description": "Information graphics and data visualizations",
                "parameters": ["data_type", "topic", "visual_approach", "layout"]
            },
            "email_header": {
                "title": "Email Newsletter Headers",
                "description": "Header images for email newsletters",
                "parameters": ["newsletter_type", "brand_name", "theme", "season"]
            }
        }


# Global instance for use in server.py
prompt_registry = PromptRegistry()