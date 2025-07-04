"""Prompt template management for various image generation use cases."""

from typing import Dict, Any, List


class PromptTemplateManager:
    """Manages prompt templates for different image generation scenarios."""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize built-in prompt templates."""
        return {
            "creative_image": {
                "name": "creative-image-prompt",
                "title": "Creative Image Generation",
                "description": "Template for creative image generation with artistic elements",
                "arguments": {
                    "subject": {"type": "string", "required": True, "description": "Main subject of the image"},
                    "style": {"type": "string", "required": False, "default": "digital art", "description": "Artistic style"},
                    "mood": {"type": "string", "required": False, "default": "vibrant", "description": "Desired mood or atmosphere"},
                    "color_palette": {"type": "string", "required": False, "default": "colorful", "description": "Color scheme preference"},
                },
                "template": "Create a {style} artwork of {subject} with a {mood} atmosphere using {color_palette} colors",
                "metadata": {
                    "recommended_size": "1024x1024",
                    "quality": "high",
                    "style": "vivid"
                }
            },
            
            "product_photography": {
                "name": "product-image-prompt", 
                "title": "Product Photography",
                "description": "Template for product photography and commercial images",
                "arguments": {
                    "product": {"type": "string", "required": True, "description": "Product description"},
                    "background": {"type": "string", "required": False, "default": "white studio", "description": "Background setting"},
                    "lighting": {"type": "string", "required": False, "default": "soft natural", "description": "Lighting style"},
                    "angle": {"type": "string", "required": False, "default": "front view", "description": "Camera angle"},
                },
                "template": "Professional product photography of {product} with {lighting} lighting on {background} background, shot from {angle}",
                "metadata": {
                    "recommended_size": "1536x1024",
                    "quality": "high",
                    "style": "natural"
                }
            },
            
            "artistic_style": {
                "name": "artistic-style-prompt",
                "title": "Artistic Style Generation",
                "description": "Template for generating images in specific artistic styles",
                "arguments": {
                    "subject": {"type": "string", "required": True, "description": "Subject to render"},
                    "artist_style": {"type": "string", "required": False, "default": "impressionist", "description": "Specific artist or art movement"},
                    "medium": {"type": "string", "required": False, "default": "oil painting", "description": "Art medium"},
                    "era": {"type": "string", "required": False, "default": "modern", "description": "Time period or artistic era"},
                },
                "template": "Render {subject} in the style of {artist_style} using {medium} technique from the {era} period",
                "metadata": {
                    "recommended_size": "1024x1024",
                    "quality": "high",
                    "style": "vivid"
                }
            },
            
            "social_media": {
                "name": "social-media-post-prompt",
                "title": "Social Media Graphics",
                "description": "Template for social media graphics",
                "arguments": {
                    "platform": {"type": "string", "required": True, "description": "Target platform"},
                    "content_type": {"type": "string", "required": True, "description": "Type of post"},
                    "brand_style": {"type": "string", "required": False, "default": "modern", "description": "Brand aesthetic"},
                    "call_to_action": {"type": "boolean", "required": False, "default": False, "description": "Whether include CTA element"},
                },
                "template": "Create a {platform} post graphic for {content_type} content in {brand_style} style{cta_part}",
                "metadata": {
                    "recommended_size": "1024x1024",
                    "quality": "medium",
                    "style": "vivid"
                }
            },
            
            "og_image": {
                "name": "og-image-prompt",
                "title": "Open Graph Images",
                "description": "Template for generating Open Graph social media preview images",
                "arguments": {
                    "title": {"type": "string", "required": True, "description": "Main title text to display"},
                    "brand_name": {"type": "string", "required": False, "description": "Website or brand name"},
                    "background_style": {"type": "string", "required": False, "default": "gradient", "description": "Background style"},
                    "text_layout": {"type": "string", "required": False, "default": "centered", "description": "Text arrangement"},
                    "color_scheme": {"type": "string", "required": False, "default": "professional", "description": "Color palette"},
                },
                "template": "Create a social media preview image (1200x630px) with '{title}' as the main headline{brand_part}, using {background_style} background with {text_layout} text layout in {color_scheme} color scheme",
                "metadata": {
                    "recommended_size": "1536x1024",
                    "quality": "medium",
                    "style": "natural"
                }
            },
            
            "blog_header": {
                "name": "blog-header-prompt",
                "title": "Blog Header Images",
                "description": "Template for blog post header images",
                "arguments": {
                    "topic": {"type": "string", "required": True, "description": "Blog post topic or theme"},
                    "style": {"type": "string", "required": False, "default": "modern", "description": "Visual style"},
                    "mood": {"type": "string", "required": False, "default": "professional", "description": "Emotional tone"},
                    "include_text_space": {"type": "boolean", "required": False, "default": True, "description": "Reserve space for text overlay"},
                },
                "template": "Design a blog header image about {topic} in {style} style with {mood} mood{text_space_part}",
                "metadata": {
                    "recommended_size": "1536x1024",
                    "quality": "medium",
                    "style": "natural"
                }
            },
            
            "hero_banner": {
                "name": "hero-banner-prompt",
                "title": "Website Hero Banners",
                "description": "Template for website hero section banners",
                "arguments": {
                    "website_type": {"type": "string", "required": True, "description": "Type of website"},
                    "industry": {"type": "string", "required": False, "description": "Industry or niche"},
                    "message": {"type": "string", "required": False, "description": "Key message or value proposition"},
                    "visual_style": {"type": "string", "required": False, "default": "modern", "description": "Design approach"},
                },
                "template": "Design a hero banner for a {website_type} website{industry_part}{message_part}, using {visual_style} visual style",
                "metadata": {
                    "recommended_size": "1536x1024",
                    "quality": "high",
                    "style": "natural"
                }
            },
            
            "thumbnail": {
                "name": "thumbnail-prompt",
                "title": "Video Thumbnails",
                "description": "Template for video thumbnails and preview images",
                "arguments": {
                    "content_type": {"type": "string", "required": True, "description": "Content type"},
                    "topic": {"type": "string", "required": True, "description": "Video topic or subject"},
                    "style": {"type": "string", "required": False, "default": "bold", "description": "Thumbnail style"},
                    "emotion": {"type": "string", "required": False, "default": "exciting", "description": "Emotional appeal"},
                },
                "template": "Design a video thumbnail for {content_type} about {topic} in {style} style with {emotion} emotional appeal",
                "metadata": {
                    "recommended_size": "1536x1024",
                    "quality": "high",
                    "style": "vivid"
                }
            },
            
            "infographic": {
                "name": "infographic-prompt",
                "title": "Infographic Images",
                "description": "Template for infographic-style images",
                "arguments": {
                    "data_type": {"type": "string", "required": True, "description": "Type of information"},
                    "topic": {"type": "string", "required": True, "description": "Subject matter"},
                    "visual_approach": {"type": "string", "required": False, "default": "modern", "description": "Design approach"},
                    "layout": {"type": "string", "required": False, "default": "vertical", "description": "Information layout"},
                },
                "template": "Create an infographic showing {data_type} about {topic} using {visual_approach} design approach in {layout} layout",
                "metadata": {
                    "recommended_size": "1024x1536",
                    "quality": "high",
                    "style": "natural"
                }
            },
            
            "email_header": {
                "name": "email-header-prompt",
                "title": "Email Newsletter Headers",
                "description": "Template for email newsletter header images",
                "arguments": {
                    "newsletter_type": {"type": "string", "required": True, "description": "Newsletter category"},
                    "brand_name": {"type": "string", "required": False, "description": "Company or brand name"},
                    "theme": {"type": "string", "required": False, "description": "Newsletter theme or topic"},
                    "season": {"type": "string", "required": False, "description": "Seasonal context"},
                },
                "template": "Create an email newsletter header for {newsletter_type} newsletter{brand_part}{theme_part}{season_part}",
                "metadata": {
                    "recommended_size": "1536x1024",
                    "quality": "medium",
                    "style": "natural"
                }
            }
        }
    
    def get_template(self, template_name: str) -> Dict[str, Any] | None:
        """Get a specific template by name."""
        return self.templates.get(template_name)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        return [
            {
                "name": template["name"],
                "title": template["title"],
                "description": template["description"],
                "arguments": template["arguments"],
            }
            for template in self.templates.values()
        ]
    
    def render_template(self, template_name: str, **kwargs) -> tuple[str, Dict[str, Any]] | None:
        """Render a template with provided arguments."""
        template = self.templates.get(template_name)
        if not template:
            return None
        
        # Validate required arguments
        for arg_name, arg_config in template["arguments"].items():
            if arg_config.get("required", False) and arg_name not in kwargs:
                raise ValueError(f"Required argument '{arg_name}' missing for template '{template_name}'")
        
        # Apply defaults for missing optional arguments
        rendered_kwargs = {}
        for arg_name, arg_config in template["arguments"].items():
            if arg_name in kwargs:
                rendered_kwargs[arg_name] = kwargs[arg_name]
            elif "default" in arg_config:
                rendered_kwargs[arg_name] = arg_config["default"]
        
        # Handle conditional parts for specific templates
        self._add_conditional_parts(template_name, rendered_kwargs)
        
        # Render the template
        try:
            rendered_prompt = template["template"].format(**rendered_kwargs)
            return rendered_prompt, template["metadata"]
        except KeyError as e:
            raise ValueError(f"Template rendering failed: missing key {e}")
    
    def _add_conditional_parts(self, template_name: str, kwargs: Dict[str, Any]) -> None:
        """Add conditional text parts based on template type and arguments."""
        
        if template_name == "social_media":
            # Handle call-to-action part
            kwargs["cta_part"] = " with call-to-action element" if kwargs.get("call_to_action", False) else ""
        
        elif template_name == "og_image":
            # Handle brand name part
            brand_name = kwargs.get("brand_name")
            kwargs["brand_part"] = f" for {brand_name}" if brand_name else ""
        
        elif template_name == "blog_header":
            # Handle text space part
            include_text_space = kwargs.get("include_text_space", True)
            kwargs["text_space_part"] = ", leaving space for text overlay" if include_text_space else ""
        
        elif template_name == "hero_banner":
            # Handle industry and message parts
            industry = kwargs.get("industry")
            message = kwargs.get("message")
            kwargs["industry_part"] = f" in the {industry} industry" if industry else ""
            kwargs["message_part"] = f": {message}" if message else ""
        
        elif template_name == "email_header":
            # Handle brand, theme, and season parts
            brand_name = kwargs.get("brand_name")
            theme = kwargs.get("theme")
            season = kwargs.get("season")
            kwargs["brand_part"] = f" for {brand_name}" if brand_name else ""
            kwargs["theme_part"] = f" with {theme} theme" if theme else ""
            kwargs["season_part"] = f" with {season} seasonal elements" if season else ""
    
    def get_template_suggestions(self, use_case: str) -> List[str]:
        """Get template suggestions based on use case."""
        use_case_lower = use_case.lower()
        suggestions = []
        
        if any(word in use_case_lower for word in ["social", "media", "post", "instagram", "facebook", "twitter"]):
            suggestions.extend(["social_media", "og_image"])
        
        if any(word in use_case_lower for word in ["blog", "article", "header"]):
            suggestions.extend(["blog_header", "hero_banner"])
        
        if any(word in use_case_lower for word in ["product", "ecommerce", "shop", "commercial"]):
            suggestions.append("product_photography")
        
        if any(word in use_case_lower for word in ["art", "creative", "artistic", "painting"]):
            suggestions.extend(["creative_image", "artistic_style"])
        
        if any(word in use_case_lower for word in ["video", "youtube", "thumbnail"]):
            suggestions.append("thumbnail")
        
        if any(word in use_case_lower for word in ["email", "newsletter"]):
            suggestions.append("email_header")
        
        if any(word in use_case_lower for word in ["data", "chart", "infographic", "statistics"]):
            suggestions.append("infographic")
        
        return suggestions