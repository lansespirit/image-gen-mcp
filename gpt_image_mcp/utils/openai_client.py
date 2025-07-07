"""OpenAI API client manager with retry logic and error handling."""

import asyncio
import base64
import logging
from typing import Any, Dict, List

import httpx
from openai import AsyncOpenAI
from openai.types.images_response import ImagesResponse

from ..config.settings import OpenAISettings

logger = logging.getLogger(__name__)


class OpenAIClientManager:
    """Manages OpenAI API client with retry logic and error handling."""
    
    def __init__(self, settings: OpenAISettings):
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.api_key,
            organization=settings.organization,
            base_url=settings.base_url,
            timeout=settings.timeout,
            max_retries=settings.max_retries,
        )
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "gpt-image-1",
        quality: str = "auto",
        size: str = "1536x1024",
        style: str = "vivid",
        moderation: str = "auto",
        output_format: str = "png",
        compression: int = 100,
        background: str = "auto",
        n: int = 1,
    ) -> ImagesResponse:
        """Generate an image using OpenAI's Images API."""
        
        request_params = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "quality": quality,
            "size": size,
            "moderation": moderation,
        }
        
        # Add gpt-image-1 specific parameters
        if model == "gpt-image-1":
            request_params.update({
                "style": style,
                "output_format": output_format,
                "background": background,
            })
            
            # Add compression for JPEG/WebP
            if output_format in ["jpeg", "webp"] and compression < 100:
                request_params["output_compression"] = compression
        
        try:
            logger.info(f"Generating image with prompt: {prompt[:100]}...")
            logger.debug(f"Request parameters: {request_params}"
                         f"API KEY: {self.client.api_key}")
            
            response = await self.client.images.generate(**request_params)
            
            logger.info(f"Successfully generated {len(response.data)} image(s)")
            return response
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise
    
    async def edit_image(
        self,
        image_data: str | bytes,
        prompt: str,
        mask_data: str | bytes | None = None,
        model: str = "gpt-image-1",
        quality: str = "auto", 
        size: str = "1536x1024",
        output_format: str = "png",
        compression: int = 100,
        background: str = "auto",
        n: int = 1,
    ) -> ImagesResponse:
        """Edit an image using OpenAI's Images API."""
        
        # Convert base64 strings to bytes if needed
        if isinstance(image_data, str):
            if image_data.startswith("data:"):
                # Handle data URLs
                image_data = image_data.split(",", 1)[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        mask_bytes = None
        if mask_data:
            if isinstance(mask_data, str):
                if mask_data.startswith("data:"):
                    mask_data = mask_data.split(",", 1)[1]
                mask_bytes = base64.b64decode(mask_data)
            else:
                mask_bytes = mask_data
        
        request_params = {
            "model": model,
            "image": image_bytes,
            "prompt": prompt,
            "n": n,
            "quality": quality,
            "size": size,
        }
        
        if mask_bytes:
            request_params["mask"] = mask_bytes
        
        # Add gpt-image-1 specific parameters
        if model == "gpt-image-1":
            request_params.update({
                "output_format": output_format,
                "background": background,
            })
            
            # Add compression for JPEG/WebP
            if output_format in ["jpeg", "webp"] and compression < 100:
                request_params["output_compression"] = compression
        
        try:
            logger.info(f"Editing image with prompt: {prompt[:100]}...")
            logger.debug(f"Request parameters: {list(request_params.keys())}")
            logger.debug(f"API KEY: {self.client.api_key}")
            response = await self.client.images.edit(**request_params)
            
            logger.info(f"Successfully edited image, generated {len(response.data)} result(s)")
            return response
            
        except Exception as e:
            logger.error(f"Error editing image: {e}")
            raise
    
    def estimate_cost(self, prompt: str, image_count: int = 1) -> Dict[str, Any]:
        """Estimate the cost of image generation."""
        
        # Rough token estimation (actual tokenization may vary)
        text_tokens = len(prompt.split()) * 1.3  # Rough approximation
        
        # gpt-image-1 pricing (as of documentation)
        text_input_cost = (text_tokens / 1_000_000) * 5.0  # $5 per 1M tokens
        image_output_cost = (image_count * 1750 / 1_000_000) * 40.0  # ~1750 tokens per image, $40 per 1M
        
        total_cost = text_input_cost + image_output_cost
        
        return {
            "estimated_cost_usd": round(total_cost, 4),
            "text_input_tokens": int(text_tokens),
            "image_output_tokens": 1750 * image_count,
            "breakdown": {
                "text_input_cost": round(text_input_cost, 4),
                "image_output_cost": round(image_output_cost, 4),
            }
        }
    
    async def download_image(self, image_url: str) -> bytes:
        """Download image from URL (for dall-e models that return URLs)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content