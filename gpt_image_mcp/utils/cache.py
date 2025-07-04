"""Cache management for the MCP server."""

import hashlib
import json
import time
from typing import Any, Dict, Optional

from ..config.settings import CacheSettings


class MemoryCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, max_size_mb: int = 500, default_ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.current_size = 0
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        return time.time() > entry["expires_at"]
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate the size of data in bytes."""
        if isinstance(data, str):
            return len(data.encode('utf-8'))
        elif isinstance(data, bytes):
            return len(data)
        elif isinstance(data, dict):
            return len(json.dumps(data).encode('utf-8'))
        else:
            return len(str(data).encode('utf-8'))
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time > entry["expires_at"]
        ]
        
        for key in expired_keys:
            entry = self.cache.pop(key)
            self.current_size -= entry["size"]
    
    def _evict_lru(self, needed_size: int):
        """Evict least recently used entries to make space."""
        if not self.cache:
            return
        
        # Sort by last access time
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1]["last_accessed"]
        )
        
        freed_size = 0
        for key, entry in sorted_entries:
            if freed_size >= needed_size:
                break
            
            freed_size += entry["size"]
            self.current_size -= entry["size"]
            del self.cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if self._is_expired(entry):
            del self.cache[key]
            self.current_size -= entry["size"]
            return None
        
        # Update last accessed time
        entry["last_accessed"] = time.time()
        return entry["data"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if ttl is None:
            ttl = self.default_ttl
        
        # Clean up expired entries first
        self._cleanup_expired()
        
        # Estimate size of new entry
        data_size = self._estimate_size(value)
        entry_size = data_size + len(key.encode('utf-8')) + 100  # overhead
        
        # Check if entry would exceed cache size
        if entry_size > self.max_size_bytes:
            return False  # Entry too large
        
        # Make space if needed
        available_space = self.max_size_bytes - self.current_size
        if entry_size > available_space:
            self._evict_lru(entry_size - available_space)
        
        # Remove existing entry if present
        if key in self.cache:
            old_entry = self.cache[key]
            self.current_size -= old_entry["size"]
        
        # Add new entry
        current_time = time.time()
        self.cache[key] = {
            "data": value,
            "size": entry_size,
            "created_at": current_time,
            "last_accessed": current_time,
            "expires_at": current_time + ttl,
        }
        self.current_size += entry_size
        
        return True
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.current_size -= entry["size"]
            return True
        return False
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.current_size = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {
            "entries": len(self.cache),
            "size_mb": round(self.current_size / (1024 * 1024), 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "utilization": round(self.current_size / self.max_size_bytes * 100, 2),
        }


class CacheManager:
    """Cache manager with pluggable backends."""
    
    def __init__(self, settings: CacheSettings):
        self.settings = settings
        self.enabled = settings.enabled
        
        if not self.enabled:
            self.cache = None
            return
        
        if settings.backend == "memory":
            self.cache = MemoryCache(
                max_size_mb=settings.max_size_mb,
                default_ttl=settings.ttl_hours * 3600
            )
        elif settings.backend == "redis":
            # Redis implementation would go here
            raise NotImplementedError("Redis backend not yet implemented")
        else:
            raise ValueError(f"Unknown cache backend: {settings.backend}")
    
    def _make_key(self, prefix: str, **kwargs) -> str:
        """Create a cache key from parameters."""
        # Sort kwargs for consistent keys
        sorted_kwargs = sorted(kwargs.items())
        key_data = json.dumps([prefix, sorted_kwargs], sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    async def initialize(self):
        """Initialize cache backend."""
        pass
    
    async def get_image_generation(self, **params) -> Optional[Dict[str, Any]]:
        """Get cached image generation result."""
        if not self.enabled:
            return None
        
        key = self._make_key("image_gen", **params)
        return self.cache.get(key)
    
    async def set_image_generation(self, result: Dict[str, Any], **params) -> bool:
        """Cache image generation result."""
        if not self.enabled:
            return False
        
        key = self._make_key("image_gen", **params)
        return self.cache.set(key, result)
    
    async def get_image_edit(self, **params) -> Optional[Dict[str, Any]]:
        """Get cached image edit result."""
        if not self.enabled:
            return None
        
        # Don't include actual image data in key, use hash
        cache_params = {k: v for k, v in params.items() if k != "image_data"}
        if "image_data" in params:
            image_hash = hashlib.sha256(params["image_data"].encode()).hexdigest()[:16]
            cache_params["image_hash"] = image_hash
        
        key = self._make_key("image_edit", **cache_params)
        return self.cache.get(key)
    
    async def set_image_edit(self, result: Dict[str, Any], **params) -> bool:
        """Cache image edit result."""
        if not self.enabled:
            return False
        
        # Don't include actual image data in key, use hash
        cache_params = {k: v for k, v in params.items() if k != "image_data"}
        if "image_data" in params:
            image_hash = hashlib.sha256(params["image_data"].encode()).hexdigest()[:16]
            cache_params["image_hash"] = image_hash
        
        key = self._make_key("image_edit", **cache_params)
        return self.cache.set(key, result)
    
    async def clear(self):
        """Clear all cache entries."""
        if self.enabled and self.cache:
            self.cache.clear()
    
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}
        
        cache_stats = self.cache.stats()
        cache_stats["enabled"] = True
        cache_stats["backend"] = self.settings.backend
        return cache_stats
    
    async def close(self):
        """Close cache connections."""
        pass