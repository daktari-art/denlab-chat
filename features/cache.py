"""
Advanced Response Cache with Adaptive TTL and Compression.

ADVANCEMENTS:
1. Adaptive TTL: Frequently accessed entries live longer; stale entries expire faster
2. Compression: Large responses are compressed to save memory
3. Semantic keys: Use content hash for cache keys instead of raw text
4. Size limits: LRU eviction when cache grows too large
5. Hit rate tracking: Monitor cache effectiveness
6. Namespace isolation: Separate caches per user

Connected to: client.py (caching LLM responses), config/settings.py (cache config).
"""

import hashlib
import json
import time
import zlib
from typing import Optional, Dict, Any, List
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AppConfig


class AdaptiveCache:
    """
    Advanced cache with adaptive TTL, compression, and LRU eviction.
    
    Each entry stores:
    - value (compressed if large)
    - created_at, accessed_at, access_count
    - ttl_seconds (adapts based on hit frequency)
    """
    
    DEFAULT_TTL = 3600  # 1 hour base
    MAX_SIZE = 1000
    COMPRESS_THRESHOLD = 1024  # Compress if > 1KB
    MAX_TTL = 86400  # 24 hours max
    MIN_TTL = 300    # 5 minutes min
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, namespace: str, data: str) -> str:
        """Create a semantic hash key."""
        content_hash = hashlib.sha256(data.encode()).hexdigest()[:16]
        return f"{namespace}:{content_hash}"
    
    def _compress(self, value: str) -> bytes:
        """Compress large values."""
        raw = value.encode('utf-8')
        if len(raw) > self.COMPRESS_THRESHOLD:
            return zlib.compress(raw)
        return raw
    
    def _decompress(self, value: bytes) -> str:
        """Decompress value."""
        try:
            return zlib.decompress(value).decode('utf-8')
        except:
            return value.decode('utf-8')
    
    def _is_expired(self, entry: Dict) -> bool:
        """Check if entry is expired with adaptive TTL."""
        age = time.time() - entry.get("created_at", 0)
        
        # Adaptive TTL: popular entries live longer
        access_count = entry.get("access_count", 1)
        base_ttl = entry.get("ttl_seconds", self.DEFAULT_TTL)
        adaptive_ttl = min(base_ttl * (1 + access_count * 0.1), self.MAX_TTL)
        
        return age > adaptive_ttl
    
    def _evict_if_needed(self):
        """LRU eviction when cache is too large."""
        if len(self._cache) <= self.MAX_SIZE:
            return
        
        # Sort by last access time, evict oldest
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1].get("accessed_at", 0)
        )
        
        to_evict = len(sorted_items) - int(self.MAX_SIZE * 0.8)
        for key, _ in sorted_items[:to_evict]:
            del self._cache[key]
    
    def get(self, namespace: str, key_data: str) -> Optional[str]:
        """Get cached value."""
        key = self._make_key(namespace, key_data)
        entry = self._cache.get(key)
        
        if not entry:
            self._misses += 1
            return None
        
        if self._is_expired(entry):
            del self._cache[key]
            self._misses += 1
            return None
        
        # Update access stats
        entry["access_count"] = entry.get("access_count", 0) + 1
        entry["accessed_at"] = time.time()
        
        self._hits += 1
        
        value = entry["value"]
        if isinstance(value, bytes):
            return self._decompress(value)
        return value
    
    def set(self, namespace: str, key_data: str, value: str, ttl_seconds: int = None):
        """Cache a value with optional TTL."""
        self._evict_if_needed()
        
        key = self._make_key(namespace, key_data)
        compressed = self._compress(value)
        
        self._cache[key] = {
            "value": compressed,
            "created_at": time.time(),
            "accessed_at": time.time(),
            "access_count": 0,
            "ttl_seconds": ttl_seconds or self.DEFAULT_TTL,
            "size": len(compressed)
        }
    
    def invalidate(self, namespace: str = None):
        """Invalidate cache entries."""
        if namespace:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{namespace}:")]
            for k in keys_to_remove:
                del self._cache[k]
        else:
            self._cache.clear()
    
    def clear(self):
        """Clear entire cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        
        now = time.time()
        valid_entries = sum(1 for e in self._cache.values() if not self._is_expired(e))
        total_size = sum(e.get("size", 0) for e in self._cache.values())
        
        oldest_age = 0
        if self._cache:
            oldest_age = now - min(e.get("created_at", now) for e in self._cache.values())
        
        return {
            "size": len(self._cache),
            "valid_entries": valid_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 3),
            "total_size_bytes": total_size,
            "memory_usage_mb": round(total_size / (1024 * 1024), 2),
            "oldest_entry_age_seconds": round(oldest_age, 0),
            "max_size": self.MAX_SIZE,
            "compress_threshold": self.COMPRESS_THRESHOLD
        }


# ============================================================================
# SINGLETON
# ============================================================================

_CACHE_INSTANCE = None

def get_cache() -> AdaptiveCache:
    """Get or create global cache instance."""
    global _CACHE_INSTANCE
    if _CACHE_INSTANCE is None:
        _CACHE_INSTANCE = AdaptiveCache()
    return _CACHE_INSTANCE


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["AdaptiveCache", "get_cache"]
