"""
Response Cache System for DenLab Chat.
Caches LLM responses with TTL to reduce API calls and improve response time.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from threading import Lock

# Import from centralized config
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import CacheConfig


# ============================================================================
# CACHE KEY GENERATION
# ============================================================================

class CacheKeyGenerator:
    """Generate unique cache keys from request parameters."""
    
    @staticmethod
    def generate(
        messages: List[Dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a deterministic cache key.
        
        Uses last 5 messages for context to balance specificity and cache hits.
        """
        # Use only last 5 messages for context (longer conversations still cache recent turns)
        recent_msgs = messages[-5:] if len(messages) > 5 else messages
        
        # Clean messages for hashing (remove timestamps, ids, etc.)
        clean_messages = []
        for msg in recent_msgs:
            clean_messages.append({
                "role": msg.get("role", ""),
                "content": msg.get("content", "")[:2000]  # Limit content length
            })
        
        # Create hash payload
        payload = {
            "messages": clean_messages,
            "model": model,
            "temperature": round(temperature, 2)
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Generate hash
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.md5(payload_str.encode()).hexdigest()
    
    @staticmethod
    def generate_image_key(
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        model: str = "flux",
        seed: Optional[int] = None
    ) -> str:
        """Generate cache key for image generation."""
        payload = {
            "prompt": prompt[:500],  # Limit prompt length
            "width": width,
            "height": height,
            "model": model
        }
        if seed:
            payload["seed"] = seed
        
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.md5(payload_str.encode()).hexdigest()


# ============================================================================
# CACHE ENTRY
# ============================================================================

class CacheEntry:
    """Single cache entry with metadata."""
    
    def __init__(
        self,
        key: str,
        response: str,
        model: str,
        created_at: Optional[datetime] = None,
        hit_count: int = 0
    ):
        self.key = key
        self.response = response
        self.model = model
        self.created_at = created_at or datetime.now()
        self.hit_count = hit_count
        self.last_accessed = self.created_at
    
    def is_expired(self, ttl: timedelta) -> bool:
        """Check if cache entry has expired."""
        return datetime.now() - self.created_at > ttl
    
    def record_hit(self):
        """Record a cache hit and update last accessed."""
        self.hit_count += 1
        self.last_accessed = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "key": self.key,
            "response": self.response,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "hit_count": self.hit_count,
            "last_accessed": self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CacheEntry":
        """Create from dictionary."""
        entry = cls(
            key=data["key"],
            response=data["response"],
            model=data["model"],
            created_at=datetime.fromisoformat(data["created_at"]),
            hit_count=data.get("hit_count", 0)
        )
        if "last_accessed" in data:
            entry.last_accessed = datetime.fromisoformat(data["last_accessed"])
        return entry


# ============================================================================
# RESPONSE CACHE (LRU with TTL)
# ============================================================================

class ResponseCache:
    """
    LRU cache for LLM responses with TTL.
    
    Features:
    - Time-to-live expiration
    - LRU eviction when full
    - Persistent storage to disk
    - Hit/miss tracking
    """
    
    def __init__(self):
        self.cache_dir = Path(CacheConfig.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_size = CacheConfig.MAX_SIZE
        self.ttl = timedelta(hours=CacheConfig.TTL_HOURS)
        self.enabled = CacheConfig.ENABLED
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._key_generator = CacheKeyGenerator()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        
        # Load existing cache
        self._load()
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def get(
        self,
        messages: List[Dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """
        Get cached response if available and not expired.
        
        Returns:
            Cached response string or None if not found/expired
        """
        if not self.enabled:
            return None
        
        key = self._key_generator.generate(messages, model, temperature, max_tokens)
        
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired(self.ttl):
                # Remove expired entry
                del self._cache[key]
                self._misses += 1
                self._save()
                return None
            
            entry.record_hit()
            self._hits += 1
            self._save()
            return entry.response
    
    def set(
        self,
        messages: List[Dict],
        model: str,
        response: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Cache a response."""
        if not self.enabled or not response:
            return
        
        key = self._key_generator.generate(messages, model, temperature, max_tokens)
        
        with self._lock:
            # Check if already exists (update hit count)
            if key in self._cache:
                self._cache[key].record_hit()
                self._save()
                return
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                response=response[:10000],  # Limit response size
                model=model
            )
            
            # Evict if at capacity
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[key] = entry
            self._save()
    
    def get_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        model: str = "flux",
        seed: Optional[int] = None
    ) -> Optional[str]:
        """Get cached image URL."""
        if not self.enabled:
            return None
        
        key = self._key_generator.generate_image_key(prompt, width, height, model, seed)
        
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired(self.ttl):
                del self._cache[key]
                self._misses += 1
                self._save()
                return None
            
            entry.record_hit()
            self._hits += 1
            self._save()
            return entry.response
    
    def set_image(
        self,
        prompt: str,
        url: str,
        width: int = 1024,
        height: int = 1024,
        model: str = "flux",
        seed: Optional[int] = None
    ):
        """Cache an image URL."""
        if not self.enabled or not url:
            return
        
        key = self._key_generator.generate_image_key(prompt, width, height, model, seed)
        
        with self._lock:
            if key in self._cache:
                return
            
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[key] = CacheEntry(key=key, response=url, model=model)
            self._save()
    
    def clear(self):
        """Clear all cached responses."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._save()
    
    def clear_expired(self):
        """Remove all expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired(self.ttl)
            ]
            for key in expired_keys:
                del self._cache[key]
            self._save()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        with self._lock:
            return {
                "enabled": self.enabled,
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_hours": CacheConfig.TTL_HOURS,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate * 100, 1),
                "total_requests": total_requests,
                "cache_dir": str(self.cache_dir)
            }
    
    def get_hot_entries(self, limit: int = 10) -> List[Dict]:
        """Get most frequently accessed cache entries."""
        with self._lock:
            sorted_entries = sorted(
                self._cache.values(),
                key=lambda x: x.hit_count,
                reverse=True
            )
            return [
                {
                    "key": e.key[:16] + "...",
                    "model": e.model,
                    "hits": e.hit_count,
                    "age_hours": round((datetime.now() - e.created_at).total_seconds() / 3600, 1)
                }
                for e in sorted_entries[:limit]
            ]
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find entry with oldest last_accessed
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        del self._cache[lru_key]
    
    def _save(self):
        """Save cache to disk."""
        try:
            data = {
                "version": "2.0",
                "updated_at": datetime.now().isoformat(),
                "entries": {k: v.to_dict() for k, v in self._cache.items()},
                "stats": {
                    "hits": self._hits,
                    "misses": self._misses
                }
            }
            
            cache_file = self.cache_dir / "cache.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _load(self):
        """Load cache from disk."""
        cache_file = self.cache_dir / "cache.json"
        
        if not cache_file.exists():
            return
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            entries = data.get("entries", {})
            for key, entry_data in entries.items():
                entry = CacheEntry.from_dict(entry_data)
                
                # Skip expired entries
                if not entry.is_expired(self.ttl):
                    self._cache[key] = entry
            
            stats = data.get("stats", {})
            self._hits = stats.get("hits", 0)
            self._misses = stats.get("misses", 0)
            
            print(f"Loaded {len(self._cache)} cache entries")
        except Exception as e:
            print(f"Error loading cache: {e}")


# ============================================================================
# CACHE MANAGER (Singleton)
# ============================================================================

_cache_instance: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCache()
    return _cache_instance


def clear_cache():
    """Clear all cached responses."""
    cache = get_cache()
    cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    cache = get_cache()
    return cache.get_stats()