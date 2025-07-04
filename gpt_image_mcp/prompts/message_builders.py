"""Message builders for MCP-compliant prompt structures."""

from typing import List
from mcp.server.fastmcp.prompts import base


class MessageBuilder:
    """Builds structured Message lists following MCP best practices."""
    
    @staticmethod
    def build_creative_prompt(
        subject: str,
        style: str = "digital art",
        mood: str = "vibrant", 
        color_palette: str = "colorful"
    ) -> List[base.Message]:
        """Build creative image generation prompt with conversation flow."""
        return [
            base.UserMessage(
                "I need help creating a compelling image prompt. Please act as a professional "
                "art director with expertise in visual composition and artistic techniques."
            ),
            base.AssistantMessage(
                "I'll help you create an artistic prompt that captures your vision perfectly! "
                "Let me analyze your requirements and provide detailed creative direction."
            ),
            base.UserMessage(
                f"Create an image prompt with these specifications:\n"
                f"• Subject: {subject}\n"
                f"• Style: {style}\n"
                f"• Mood: {mood}\n"
                f"• Color palette: {color_palette}\n\n"
                f"Please include specific details about composition, lighting, and artistic techniques."
            ),
            base.AssistantMessage(
                f"**Artistic Vision Prompt:**\n\n"
                f"Create a {style} artwork featuring {subject}, capturing a {mood} atmosphere "
                f"with a {color_palette} color palette.\n\n"
                f"**Technical Direction:**\n"
                f"- Composition: Dynamic, well-balanced visual flow\n"
                f"- Lighting: Professional, mood-appropriate illumination that enhances the {mood} feel\n"
                f"- Detail level: High quality with sharp focus on key elements\n"
                f"- Artistic approach: Authentic {style} techniques and visual language\n"
                f"- Color harmony: {color_palette} tones that support the overall {mood} atmosphere\n\n"
                f"This prompt balances creative vision with technical precision for optimal artistic results."
            )
        ]
    
    @staticmethod
    def build_product_prompt(
        product: str,
        background: str = "white studio",
        lighting: str = "soft natural",
        angle: str = "front view"
    ) -> List[base.Message]:
        """Build product photography prompt with professional guidance."""
        return [
            base.UserMessage(
                "I need professional product photography guidance. Please act as an experienced "
                "commercial photographer specializing in high-end product shoots."
            ),
            base.AssistantMessage(
                "Perfect! I'll create a comprehensive product photography prompt with "
                "professional specifications for lighting, composition, and technical quality."
            ),
            base.UserMessage(
                f"Product photography requirements:\n"
                f"• Product: {product}\n"
                f"• Background: {background}\n"
                f"• Lighting setup: {lighting}\n"
                f"• Camera angle: {angle}\n\n"
                f"Please provide detailed technical specifications for commercial-quality results."
            ),
            base.AssistantMessage(
                f"**Professional Product Photography Prompt:**\n\n"
                f"Professional product photography of {product} with {lighting} lighting "
                f"on {background} background, shot from {angle}.\n\n"
                f"**Technical Specifications:**\n"
                f"- Camera quality: High-resolution commercial grade with perfect focus\n"
                f"- Lighting setup: {lighting} with professional color temperature and shadow control\n"
                f"- Composition: {angle} perspective showcasing product features optimally\n"
                f"- Background: {background} setting with clean, distraction-free presentation\n"
                f"- Post-processing: Professional color accuracy, balanced exposure, market-ready finish\n\n"
                f"**Quality Standards:**\n"
                f"- Commercial grade resolution and clarity\n"
                f"- E-commerce ready with consistent brand aesthetic\n"
                f"- Professional retouching quality with natural product representation"
            )
        ]
    
    @staticmethod
    def build_social_media_prompt(
        platform: str,
        content_type: str,
        brand_style: str = "modern",
        call_to_action: bool = False
    ) -> List[base.Message]:
        """Build social media graphics prompt with platform optimization."""
        
        # Platform-specific optimization guidance
        platform_guides = {
            "instagram": "Square 1080x1080 or vertical 1080x1350, vibrant colors, mobile-first design",
            "facebook": "Landscape 1200x630, clear readable text, engagement-focused layout",
            "twitter": "Landscape 1200x675, bold typography, high contrast for quick impact",
            "linkedin": "Landscape 1200x627, professional aesthetic, business-appropriate design",
            "tiktok": "Vertical 1080x1920, dynamic layout, trend-aware visual style",
            "pinterest": "Vertical 1000x1500, inspirational design, discovery-optimized"
        }
        
        platform_spec = platform_guides.get(platform.lower(), "Standard social media dimensions with platform best practices")
        
        return [
            base.UserMessage(
                f"I need to create engaging {platform} graphics. Please act as a social media "
                f"designer with expertise in {platform}-specific content optimization."
            ),
            base.AssistantMessage(
                f"Great! I'll help you create {platform}-optimized graphics that maximize "
                f"engagement and follow platform best practices for visual content."
            ),
            base.UserMessage(
                f"Social media design requirements:\n"
                f"• Platform: {platform}\n"
                f"• Content type: {content_type}\n"
                f"• Brand style: {brand_style}\n"
                f"• Call-to-action: {'Required' if call_to_action else 'Not needed'}\n\n"
                f"Please create a platform-optimized design prompt with engagement best practices."
            ),
            base.AssistantMessage(
                f"**{platform.title()} Social Media Design Prompt:**\n\n"
                f"Create a {platform} post graphic for {content_type} content in {brand_style} style"
                + (" with prominent call-to-action element" if call_to_action else "") + ".\n\n"
                f"**Platform Optimization:**\n"
                f"- Dimensions: {platform_spec}\n"
                f"- Visual style: {brand_style} aesthetic optimized for {platform} audience\n"
                f"- Typography: Mobile-readable hierarchy with platform-appropriate font sizing\n"
                f"- Color scheme: High-contrast {brand_style} palette for maximum visibility\n"
                + (f"- Call-to-action: Clear, compelling CTA prominently positioned for engagement\n" if call_to_action else "")
                + f"\n**Engagement Optimization:**\n"
                f"- Layout: Scroll-stopping appeal designed for {platform} feed behavior\n"
                f"- Content focus: {content_type} messaging that resonates with {platform} users\n"
                f"- Brand consistency: {brand_style} elements that maintain visual identity\n"
                f"- Technical quality: High-resolution, ready-to-post format"
            )
        ]
    
    @staticmethod
    def build_template_prompt(template_name: str, **kwargs) -> List[base.Message]:
        """Build prompt from template system with enhanced messaging."""
        from .templates import PromptTemplateManager
        
        manager = PromptTemplateManager()
        template = manager.get_template(template_name)
        
        if not template:
            return [base.UserMessage(f"Template '{template_name}' not found.")]
        
        try:
            rendered_prompt, metadata = manager.render_template(template_name, **kwargs)
            
            # Create enhanced conversation flow
            return [
                base.UserMessage(
                    f"I need help with {template['title'].lower()}. Please provide expert guidance "
                    f"based on the following requirements."
                ),
                base.AssistantMessage(
                    f"I'll help you create an optimized {template['title'].lower()} prompt. "
                    f"Let me analyze your specifications and provide detailed guidance."
                ),
                base.UserMessage(
                    f"Requirements: {', '.join(f'{k}: {v}' for k, v in kwargs.items())}\n\n"
                    f"Please create a detailed prompt following best practices for this use case."
                ),
                base.AssistantMessage(
                    f"**{template['title']} Prompt:**\n\n"
                    f"{rendered_prompt}\n\n"
                    f"**Recommended Settings:**\n"
                    f"- Size: {metadata.get('recommended_size', '1024x1024')}\n"
                    f"- Quality: {metadata.get('quality', 'high')}\n"
                    f"- Style: {metadata.get('style', 'vivid')}\n\n"
                    f"This prompt is optimized for {template['description'].lower()}."
                )
            ]
            
        except Exception as e:
            return [
                base.UserMessage(f"Error building prompt from template '{template_name}': {str(e)}")
            ]