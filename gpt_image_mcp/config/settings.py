"""Configuration settings for the GPT Image MCP Server."""

from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseModel):
    """OpenAI API configuration."""
    
    api_key: str = Field(..., description="OpenAI API key")
    organization: str | None = Field(None, description="OpenAI organization ID")
    base_url: str = Field("https://api.openai.com/v1", description="OpenAI API base URL")
    timeout: float = Field(300.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v.rstrip('/')


class ImageSettings(BaseModel):
    """Image generation default settings."""
    
    default_model: str = Field("gpt-image-1", description="Default image model")
    default_quality: Literal["auto", "high", "medium", "low"] = Field("auto", description="Default quality")
    default_size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = Field("auto", description="Default size")
    default_style: Literal["vivid", "natural"] = Field("vivid", description="Default style")
    default_moderation: Literal["auto", "low"] = Field("auto", description="Default moderation level")
    default_output_format: Literal["png", "jpeg", "webp"] = Field("png", description="Default output format")
    default_compression: int = Field(100, description="Default compression level (0-100)")
    base_host: str | None = Field(None, description="Base URL for image hosting (for nginx/CDN), if None uses MCP server host")


class StorageSettings(BaseModel):
    """Local storage configuration."""
    
    base_path: str = Field("./storage", description="Base storage directory")
    retention_days: int = Field(30, description="File retention period in days")
    max_size_gb: float = Field(10.0, description="Maximum storage size in GB")
    cleanup_interval_hours: int = Field(24, description="Cleanup interval in hours")
    create_subdirectories: bool = Field(True, description="Create date-based subdirectories")
    file_permissions: str = Field("644", description="File permissions in octal")

    @field_validator('base_path')
    @classmethod
    def validate_base_path(cls, v):
        path = Path(v)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot create or access storage path: {e}")
        return str(path.resolve())
    
    @field_validator('file_permissions')
    @classmethod
    def validate_permissions(cls, v):
        try:
            int(v, 8)
            if len(v) != 3:
                raise ValueError("File permissions must be 3 digits")
        except ValueError:
            raise ValueError("File permissions must be valid octal notation (e.g., '644')")
        return v


class CacheSettings(BaseModel):
    """Caching configuration."""
    
    enabled: bool = Field(True, description="Enable caching")
    ttl_hours: int = Field(24, description="Cache TTL in hours")
    backend: Literal["memory", "redis"] = Field("memory", description="Cache backend")
    max_size_mb: int = Field(500, description="Maximum cache size in MB")
    redis_url: str | None = Field(None, description="Redis connection URL")

    @model_validator(mode='after')
    def validate_redis_config(self):
        if self.backend == "redis" and not self.redis_url:
            raise ValueError("Redis URL is required when using redis backend")
        return self


class ServerSettings(BaseModel):
    """Server configuration."""
    
    name: str = Field("GPT Image MCP Server", description="Server name")
    version: str = Field("0.1.0", description="Server version")
    port: int = Field(3001, description="Server port")
    host: str = Field("127.0.0.1", description="Server host")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field("INFO", description="Log level")
    rate_limit_rpm: int = Field(50, description="Rate limit requests per minute")


class Settings(BaseSettings):
    """Main configuration settings with automatic environment variable handling."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra="ignore",
        env_file_alternates=[".env.local", ".env.production"],
    )
    
    # Nested settings with proper defaults
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    images: ImageSettings = Field(default_factory=ImageSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
