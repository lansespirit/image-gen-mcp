"""Configuration settings for the GPT Image MCP Server."""

import os
from typing import Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseModel):
    """OpenAI API configuration."""
    
    api_key: str = Field(..., description="OpenAI API key")
    organization: str | None = Field(None, description="OpenAI organization ID")
    base_url: str = Field("https://api.openai.com/v1", description="OpenAI API base URL")
    timeout: float = Field(60.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")


class ImageSettings(BaseModel):
    """Image generation default settings."""
    
    default_model: str = Field("gpt-image-1", description="Default image model")
    default_quality: Literal["auto", "high", "medium", "low"] = Field("auto", description="Default quality")
    default_size: Literal["1024x1024", "1536x1024", "1024x1536"] = Field("1536x1024", description="Default size")
    default_style: Literal["vivid", "natural"] = Field("vivid", description="Default style")
    default_moderation: Literal["auto", "low"] = Field("auto", description="Default moderation level")
    default_output_format: Literal["png", "jpeg", "webp"] = Field("png", description="Default output format")
    default_compression: int = Field(100, description="Default compression level (0-100)")


class StorageSettings(BaseModel):
    """Local storage configuration."""
    
    base_path: str = Field("./storage", description="Base storage directory")
    retention_days: int = Field(30, description="File retention period in days")
    max_size_gb: float = Field(10.0, description="Maximum storage size in GB")
    cleanup_interval_hours: int = Field(24, description="Cleanup interval in hours")
    create_subdirectories: bool = Field(True, description="Create date-based subdirectories")
    file_permissions: str = Field("644", description="File permissions in octal")


class CacheSettings(BaseModel):
    """Caching configuration."""
    
    enabled: bool = Field(True, description="Enable caching")
    ttl_hours: int = Field(24, description="Cache TTL in hours")
    backend: Literal["memory", "redis"] = Field("memory", description="Cache backend")
    max_size_mb: int = Field(500, description="Maximum cache size in MB")
    redis_url: str | None = Field(None, description="Redis connection URL")


class ServerSettings(BaseModel):
    """Server configuration."""
    
    name: str = Field("GPT Image MCP Server", description="Server name")
    version: str = Field("0.1.0", description="Server version")
    port: int = Field(3001, description="Server port")
    host: str = Field("127.0.0.1", description="Server host")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field("INFO", description="Log level")
    rate_limit_rpm: int = Field(50, description="Rate limit requests per minute")


class Settings(BaseSettings):
    """Main configuration settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )
    
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    images: ImageSettings = Field(default_factory=ImageSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls(
            openai=OpenAISettings(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                organization=os.getenv("OPENAI_ORGANIZATION"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            ),
            images=ImageSettings(
                default_quality=os.getenv("DEFAULT_QUALITY", "auto"),
                default_size=os.getenv("DEFAULT_SIZE", "1536x1024"),
                default_style=os.getenv("DEFAULT_STYLE", "vivid"),
                default_moderation=os.getenv("MODERATION_LEVEL", "auto"),
            ),
            storage=StorageSettings(
                base_path=os.getenv("STORAGE_BASE_PATH", "./storage"),
                retention_days=int(os.getenv("STORAGE_RETENTION_DAYS", "30")),
                max_size_gb=float(os.getenv("STORAGE_MAX_SIZE_GB", "10.0")),
                cleanup_interval_hours=int(os.getenv("STORAGE_CLEANUP_INTERVAL_HOURS", "24")),
            ),
            cache=CacheSettings(
                enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
                ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
                backend=os.getenv("CACHE_BACKEND", "memory"),
                max_size_mb=int(os.getenv("MAX_CACHE_SIZE_MB", "500")),
            ),
            server=ServerSettings(
                port=int(os.getenv("SERVER_PORT", "3001")),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                rate_limit_rpm=int(os.getenv("RATE_LIMIT_RPM", "50")),
            ),
        )