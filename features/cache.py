# features/cache.py
"""Response caching to reduce API calls."""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Dict
from functools import lru_cache

class ResponseCache:
    """Cache LLM responses with TTL."""
    
    def __init__(self, cache_dir: str = "data/cache", max_size: int = 100, ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self._cache: Dict[str, Dict] = {}
        self._load()
    
    def _get_key(self, messages: list, model: str, temperature: float) -> str:
        """Generate cache key from messages and parameters."""
        # Use last 3 messages for context to avoid too-specific caching
        recent_msgs = messages[-3:] if len(messages) > 3 else messages
        content = json.dumps(recent_msgs, sort_keys=True) + model + str(temperature)
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, messages: list, model: str, temperature: float = 0.7) -> Optional[str]:
        """Get cached response if available and not expired."""
        key = self._get_key(messages, model, temperature)
        
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() - entry["timestamp"] < self.ttl:
                return entry["response"]
            else:
                # Expired, remove
                del self._cache[key]
                self._save()
        
        return None
    
    def set(self, messages: list, model: str, response: str, temperature: float = 0.7):
        """Cache a response."""
        key = self._get_key(messages, model, temperature)
        
        # Manage size
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest]
        
        self._cache[key] = {
            "response": response,
            "timestamp": datetime.now(),
            "model": model
        }
        self._save()
    
    def clear(self):
        """Clear all cached responses."""
        self._cache = {}
        self._save()
    
    def stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_hours": self.ttl.total_seconds() / 3600
        }
    
    def _load(self):
        """Load cache from disk."""
        cache_file = self.cache_dir / "cache.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    for key, entry in data.items():
                        entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
                    self._cache = data
            except Exception:
                pass
    
    def _save(self):
        """Save cache to disk."""
        cache_file = self.cache_dir / "cache.json"
        try:
            # Convert datetime to string for JSON
            data = {}
            for key, entry in self._cache.items():
                data[key] = {
                    "response": entry["response"],
                    "timestamp": entry["timestamp"].isoformat(),
                    "model": entry["model"]
                }
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


# Global cache instance
_cache = None

def get_cache() -> ResponseCache:
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache
