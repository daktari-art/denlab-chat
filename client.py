"""
MultiProvider AI Client with Guardrails, Fallback Support, Cache, and Memory.
Handles API communication with Pollinations.ai and other providers.
Imports memory, cache, and routing from features/ modules.
"""

import requests
import json
import time
from typing import List, Dict, Optional, Callable, Any

# Import from features modules (no duplication!)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    APIEndpoints, Models, SystemPrompts, 
    CacheConfig, MemoryConfig
)
from features.memory import get_memory, HierarchicalMemory
from features.cache import get_cache, ResponseCache
from features.tool_router import get_router, ToolRouter
from backend import get_tools_metadata


# ============================================================================
# CONTENT GUARDRAILS
# ============================================================================

class ContentGuardrails:
    """Safety guardrails to filter harmful content while allowing legitimate requests."""
    
    HARMFUL_CATEGORIES = {
        "child_exploitation": [
            r"\b(child porn|csam|pedo|underage.*sex|minor.*nude|kid.*naked)\b",
        ],
        "extreme_violence": [
            r"\b(how to (kill|murder|assassinate|poison).*specific person|detailed torture instructions|genocide planning)\b",
        ],
        "illegal_activities": [
            r"\b(how to (make|build|synthesize).*bomb|meth recipe|detailed.*terrorist.*attack|active.*shooter.*guide)\b",
        ],
        "self_harm": [
            r"\b(detailed suicide methods|step by step.*kill myself|most effective.*overdose)\b",
        ],
        "non_consensual": [
            r"\b(rape.*how to|sexual assault.*guide|revenge porn|hidden camera.*sex)\b",
        ],
    }
    
    SAFE_CONTEXTS = [
        r"\b(educational|academic|research|history|literature|fiction|story|novel|essay|analysis)\b",
        r"\b(for a game|for a movie|for a script|creative writing|hypothetical|what if)\b",
        r"\b(prevent|stop|avoid|report|therapy|counseling|mental health|crisis)\b",
        r"\b(legal advice|law|court|case study|policy|regulation)\b",
    ]
    
    def __init__(self):
        import re
        self._compiled_patterns = {}
        for category, patterns in self.HARMFUL_CATEGORIES.items():
            self._compiled_patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        self._safe_patterns = [re.compile(p, re.IGNORECASE) for p in self.SAFE_CONTEXTS]
    
    def check(self, content: str) -> Dict[str, Any]:
        """Check content against guardrails."""
        import re
        if not content or not isinstance(content, str):
            return {"safe": True, "category": None, "reason": "Empty content"}
        
        has_safe_context = any(p.search(content) for p in self._safe_patterns)
        
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    if has_safe_context and category not in ["child_exploitation", "non_consensual"]:
                        continue
                    return {
                        "safe": False,
                        "category": category,
                        "reason": f"Content flagged by safety guardrails: {category.replace('_', ' ')}"
                    }
        
        return {"safe": True, "category": None, "reason": "Content passed safety checks"}
    
    def get_safe_response(self, check_result: Dict[str, Any]) -> str:
        """Get a helpful, safe response when content is blocked."""
        category = check_result.get("category", "unknown")
        
        responses = {
            "child_exploitation": "I cannot assist with requests involving child exploitation or abuse. This is illegal and harmful. If you have concerns about child safety, please contact your local authorities.",
            "extreme_violence": "I cannot provide detailed instructions for harming others. If you're experiencing thoughts of violence, please reach out to a mental health professional or crisis helpline.",
            "illegal_activities": "I cannot assist with illegal activities or creating harmful materials. If you have questions about legal alternatives or safety information, I'm happy to help with that.",
            "self_harm": "I'm sorry you're feeling this way. I'm not able to provide that information. Please reach out for support: 988 Suicide & Crisis Lifeline (call or text 988). You matter, and help is available.",
            "non_consensual": "I cannot assist with non-consensual sexual content or assault. If you or someone you know needs help, contact RAINN (1-800-656-HOPE).",
        }
        
        return responses.get(category, "I'm not able to help with this request as it may involve harmful content. I'm happy to assist with other questions or topics instead.")


# ============================================================================
# MULTI-PROVIDER CLIENT
# ============================================================================

class MultiProviderClient:
    """
    AI client with multi-provider support, cache, memory, and guardrails.
    
    Features:
    - Multiple API providers with automatic fallback
    - Response caching (from features/cache.py)
    - Hierarchical memory (from features/memory.py)
    - Content guardrails for safety
    - Streaming support
    - Tool/function calling support
    """
    
    PROVIDERS = {
        "pollinations": {
            "base_url": APIEndpoints.TEXT_API,
            "image_url": APIEndpoints.IMAGE_API,
            "audio_url": APIEndpoints.AUDIO_API,
            "models": ["openai", "openai-mini", "claude", "gemini", "llama", "mistral", "deepseek", "qwen"],
        },
    }
    
    def __init__(self, primary: str = "pollinations", enable_cache: bool = True, enable_memory: bool = True):
        self.primary = primary
        self.enable_cache = enable_cache
        self.enable_memory = enable_memory
        self.session = requests.Session()
        self.session.headers.update(APIEndpoints.get_headers())
        self.guardrails = ContentGuardrails()
        self._last_provider = None
        self._cache = get_cache() if enable_cache else None
        self._router = get_router()
    
    # ========================================================================
    # Memory Management
    # ========================================================================
    
    def _get_memory(self, user_id: str) -> Optional['HierarchicalMemory']:
        """Get memory for a user (lazy-loaded)."""
        if not self.enable_memory or not user_id:
            return None
        return get_memory(user_id)
    
    def _store_in_memory(self, user_id: str, user_msg: str, assistant_msg: str):
        """Store conversation in memory."""
        memory = self._get_memory(user_id)
        if memory:
            memory.add(user_msg, "user", importance=0.6)
            memory.add(assistant_msg, "assistant", importance=0.5)
    
    def _get_memory_context(self, user_id: str, query: str) -> str:
        """Get relevant memory context for a query."""
        memory = self._get_memory(user_id)
        if memory:
            return memory.get_context(query)
        return ""
    
    # ========================================================================
    # Cache Management
    # ========================================================================
    
    def _get_cached(self, messages: List[Dict], model: str, temperature: float) -> Optional[str]:
        """Get cached response."""
        if self._cache:
            return self._cache.get(messages, model, temperature)
        return None
    
    def _set_cached(self, messages: List[Dict], model: str, response: str, temperature: float):
        """Cache a response."""
        if self._cache and response:
            self._cache.set(messages, model, response, temperature)
    
    # ========================================================================
    # API Communication
    # ========================================================================
    
    def _get_provider_url(self, provider: Optional[str] = None) -> str:
        """Get the API URL for a provider."""
        name = provider or self.primary
        return self.PROVIDERS.get(name, self.PROVIDERS["pollinations"])["base_url"]
    
    def _do_request(self, payload: Dict, provider: Optional[str] = None, stream: bool = False) -> requests.Response:
        """Execute HTTP request with timeout."""
        url = self._get_provider_url(provider)
        timeout = APIEndpoints.TIMEOUT_EXTRA_LONG if stream else APIEndpoints.TIMEOUT_LONG
        
        if stream:
            return self.session.post(url, json=payload, stream=True, timeout=timeout)
        return self.session.post(url, json=payload, timeout=timeout)
    
    def _sync_with_fallback(self, payload: Dict, model: str, messages: List[Dict], 
                            temperature: float, user_id: Optional[str]) -> Dict[str, Any]:
        """Try sync request with fallback providers."""
        providers = [self.primary]
        
        for provider in providers:
            try:
                resp = self._do_request(payload, provider)
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        msg = data["choices"][0].get("message", {})
                        content = msg.get("content", "")
                        tool_calls = msg.get("tool_calls")
                        
                        if not content and not tool_calls:
                            continue
                        
                        self._last_provider = provider
                        
                        # Cache response
                        self._set_cached(messages, model, content, temperature)
                        
                        return {
                            "content": content or "",
                            "tool_calls": tool_calls,
                            "provider": provider
                        }
                        
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.RequestException:
                continue
            except Exception:
                continue
        
        return {
            "content": "I'm having trouble connecting to the AI service. Please try again in a moment.",
            "tool_calls": None,
            "provider": "failed",
            "error": "All providers failed"
        }
    
    def _stream_with_fallback(self, payload: Dict, on_chunk: Callable[[str], None]) -> str:
        """Try streaming with fallback providers."""
        providers = [self.primary]
        full_content = ""
        
        for provider in providers:
            try:
                resp = self._do_request(payload, provider, stream=True)
                
                if resp.status_code != 200:
                    continue
                
                self._last_provider = provider
                
                for line in resp.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get('choices', [{}])[0].get('delta', {})
                                content = delta.get('content', "")
                                if content:
                                    full_content += content
                                    on_chunk(content)
                            except Exception:
                                continue
                
                if full_content.strip():
                    return full_content
                    
            except Exception:
                continue
        
        return full_content or "No response received."
    
    # ========================================================================
    # Main Chat Method
    # ========================================================================
    
    def chat(self, 
             messages: List[Dict], 
             model: str = "openai", 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None,
             stream: bool = False,
             tools: Optional[List[Dict]] = None,
             on_chunk: Optional[Callable[[str], None]] = None,
             user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send chat request with multi-provider fallback, cache, and memory.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., "openai", "claude", "gemini")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            tools: Optional list of tool definitions for function calling
            on_chunk: Callback for streaming chunks
            user_id: User ID for memory retrieval
        
        Returns:
            Dict with 'content', 'tool_calls', 'provider', and optional 'cached'
        """
        
        # Check guardrails on user message
        for msg in reversed(messages):
            if msg.get("role") == "user":
                check = self.guardrails.check(msg.get("content", ""))
                if not check["safe"]:
                    return {
                        "content": self.guardrails.get_safe_response(check),
                        "tool_calls": None,
                        "provider": "guardrails",
                        "guardrail_triggered": True
                    }
                break
        
        # Get memory context (inject into system message)
        if user_id:
            # Find last user message for context retrieval
            last_user_msg = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break
            
            if last_user_msg:
                context = self._get_memory_context(user_id, last_user_msg)
                if context:
                    # Inject context into system message or create one
                    for msg in messages:
                        if msg.get("role") == "system":
                            msg["content"] = msg.get("content", "") + "\n\n" + context
                            break
                    else:
                        messages.insert(0, {"role": "system", "content": context})
        
        # Check cache (skip for streaming and tool calls)
        if not stream and not tools:
            cached = self._get_cached(messages, model, temperature)
            if cached:
                if user_id:
                    # Store in memory even if cached
                    for msg in reversed(messages):
                        if msg.get("role") == "user":
                            self._store_in_memory(user_id, msg.get("content", ""), cached)
                            break
                return {"content": cached, "tool_calls": None, "provider": "cache", "cached": True}
        
        # Build payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        # Execute request
        if stream and on_chunk:
            content = self._stream_with_fallback(payload, on_chunk)
            result = {"content": content, "tool_calls": None, "provider": self._last_provider}
        else:
            result = self._sync_with_fallback(payload, model, messages, temperature, user_id)
        
        # Store in memory
        if user_id and result.get("content"):
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    self._store_in_memory(user_id, msg.get("content", ""), result["content"])
                    break
        
        return result
    
    # ========================================================================
    # Image Generation
    # ========================================================================
    
    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024,
                       model: str = "flux", seed: Optional[int] = None,
                       nologo: bool = True) -> str:
        """
        Generate image URL from prompt.
        
        Args:
            prompt: Image description
            width: Image width in pixels
            height: Image height in pixels
            model: Image model to use ("flux", "flux-pro", "turbo")
            seed: Optional seed for reproducibility
            nologo: Whether to hide watermark
        
        Returns:
            URL string for the generated image
        """
        # Check cache first
        cache = get_cache()
        cached_url = cache.get_image(prompt, width, height, model, seed) if cache else None
        if cached_url:
            return cached_url
        
        encoded = requests.utils.quote(prompt)
        url = f"{self.PROVIDERS[self.primary]['image_url']}/{encoded}?width={width}&height={height}&model={model}"
        if nologo:
            url += "&nologo=true"
        if seed:
            url += f"&seed={seed}"
        
        # Cache the URL
        if cache:
            cache.set_image(prompt, url, width, height, model, seed)
        
        return url
    
    # ========================================================================
    # Audio Generation
    # ========================================================================
    
    def generate_audio(self, text: str, voice: str = "nova") -> str:
        """
        Generate audio URL from text (TTS).
        
        Args:
            text: Text to convert to speech (max 500 chars)
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        
        Returns:
            URL string for the generated audio
        """
        encoded = requests.utils.quote(text[:500])
        return f"{self.PROVIDERS[self.primary]['audio_url']}/{encoded}?voice={voice}"
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def route_query(self, query: str, available_tools: List[str]) -> Dict[str, Any]:
        """Route query to appropriate tools using ToolRouter."""
        return self._router.route(query, available_tools)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        if self._cache:
            return self._cache.get_stats()
        return {"enabled": False}
    
    def clear_cache(self):
        """Clear all cached responses."""
        if self._cache:
            self._cache.clear()
    
    def clear_memory(self, user_id: str):
        """Clear memory for a specific user."""
        if self.enable_memory and user_id:
            memory = self._get_memory(user_id)
            if memory:
                memory.clear_working()
    
    def get_tools_metadata(self) -> Dict[str, Dict]:
        """Get metadata for all available tools."""
        return get_tools_metadata()


# ============================================================================
# COMPATIBILITY ALIAS
# ============================================================================

class PollinationsClient(MultiProviderClient):
    """Legacy alias for backward compatibility."""
    pass


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_client_instance: Optional[MultiProviderClient] = None


def get_client(enable_cache: bool = True, enable_memory: bool = True) -> MultiProviderClient:
    """Get or create the MultiProviderClient singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = MultiProviderClient(
            enable_cache=enable_cache,
            enable_memory=enable_memory
        )
    return _client_instance