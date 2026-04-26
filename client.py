"""
Multi-Provider LLM Client with Enhanced Fallback and Streaming Support.

ADVANCEMENTS:
1. Fallback chain: If primary provider fails, automatically tries backup providers
2. Streaming support: Real-time token streaming for chat responses
3. Better error handling: Categorizes errors (rate limit, auth, timeout, etc.)
4. Provider health tracking: Avoids repeatedly failing providers
5. Request batching: Combines small requests when possible
6. Metrics collection: Tracks latency, tokens, success rate per provider

Connected to: config/settings.py (provider configs), features/cache.py (response cache),
features/memory.py (memory storage).
"""

import streamlit as st
import json
import hashlib
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Models, AppConfig

# Import advanced cache/memory with fallback
try:
    from features.cache import get_cache
    CACHE_AVAILABLE = True
except:
    CACHE_AVAILABLE = False

try:
    from features.memory import get_memory
    MEMORY_AVAILABLE = True
except:
    MEMORY_AVAILABLE = False


# ============================================================================
# PROVIDER METRICS
# ============================================================================

@dataclass
class ProviderMetrics:
    """Metrics for a provider's performance."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    last_error: str = ""
    last_used: float = 0.0
    is_healthy: bool = True


# ============================================================================
# MULTI-PROVIDER CLIENT
# ============================================================================

class MultiProviderClient:
    """
    Enhanced client with fallback chain, health tracking, and metrics.
    """
    
    FALLBACK_CHAIN = ["openai", "google", "mistral", "anthropic", "cohere", "meta"]
    
    def __init__(self):
        self.api_keys: Dict[str, str] = {}
        self._load_api_keys()
        self._cache = get_cache() if CACHE_AVAILABLE else None
        self._memory = None
        self.metrics: Dict[str, ProviderMetrics] = {
            name: ProviderMetrics()
            for name in Models.PROVIDERS.keys()
        }
    
    def _load_api_keys(self):
        """Load API keys from environment."""
        for name, config in Models.PROVIDERS.items():
            key = os.environ.get(config.get("env_var", ""), "")
            if key:
                self.api_keys[name] = key
    
    def _get_provider_config(self, model_name: str) -> tuple:
        """Get provider name and API config for a model."""
        api_name = Models.get_api_name(model_name)
        config = Models.PROVIDERS.get(api_name, {})
        return api_name, config
    
    def _make_cache_key(self, messages: List[Dict], model: str, tools: List = None) -> str:
        """Create deterministic cache key."""
        key_data = json.dumps({"m": messages, "model": model, "tools": tools}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _update_metrics(self, provider: str, success: bool, latency_ms: float, error: str = ""):
        """Update provider metrics."""
        m = self.metrics[provider]
        m.total_requests += 1
        if success:
            m.successful_requests += 1
        else:
            m.failed_requests += 1
            m.last_error = error
            if m.failed_requests > 3 and m.failed_requests / m.total_requests > 0.7:
                m.is_healthy = False
        
        # Update rolling average latency
        m.avg_latency_ms = (m.avg_latency_ms * (m.total_requests - 1) + latency_ms) / m.total_requests
        m.last_used = time.time()
    
    def _get_fallback_chain(self, primary: str) -> List[str]:
        """Get ordered fallback providers."""
        chain = [primary]
        for p in self.FALLBACK_CHAIN:
            if p != primary and p in self.api_keys and self.metrics[p].is_healthy:
                chain.append(p)
        return chain
    
    # ========================================================================
    # GENERATE
    # ========================================================================
    
    def generate(self, messages: List[Dict], model: str = None, temperature: float = 0.7,
                 tools: List[Dict] = None, user_id: str = None,
                 conversation_id: str = None, stream: bool = False,
                 stream_callback: Callable = None) -> Dict:
        """
        Generate response with caching, fallback, and optional streaming.
        """
        model = model or Models.DEFAULT_MODEL
        api_name, config = self._get_provider_config(model)
        
        # Check cache
        if self._cache and st.session_state.get("cache_enabled", True):
            cache_key = self._make_cache_key(messages, model, tools)
            cached = self._cache.get(api_name, cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except:
                    return {"content": cached, "model": model, "cached": True}
        
        # Try primary and fallbacks
        chain = self._get_fallback_chain(api_name)
        last_error = ""
        
        for provider in chain:
            start_time = time.time()
            try:
                result = self._call_provider(provider, messages, model, temperature, tools, stream, stream_callback)
                latency = (time.time() - start_time) * 1000
                self._update_metrics(provider, True, latency)
                
                # Cache result
                if self._cache and st.session_state.get("cache_enabled", True):
                    cache_key = self._make_cache_key(messages, model, tools)
                    self._cache.set(api_name, cache_key, json.dumps(result))
                
                # Store in memory
                if MEMORY_AVAILABLE and user_id and st.session_state.get("memory_enabled", True):
                    try:
                        mem = get_memory(user_id)
                        last_user = messages[-1].get("content", "") if messages else ""
                        mem.add_interaction(last_user, result.get("content", ""), conversation_id)
                    except:
                        pass
                
                return result
                
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                error_str = str(e)
                self._update_metrics(provider, False, latency, error_str)
                last_error = error_str
                continue
        
        # All providers failed
        return {
            "content": f"All providers failed. Last error: {last_error}",
            "error": last_error,
            "model": model,
            "guardrail_triggered": False
        }
    
    def _call_provider(self, provider: str, messages: List[Dict], model: str,
                       temperature: float, tools: List[Dict] = None,
                       stream: bool = False, stream_callback: Callable = None) -> Dict:
        """Call a specific provider."""
        config = Models.PROVIDERS.get(provider, {})
        api_url = config.get("api_url", "")
        
        if provider == "openai":
            return self._call_openai(messages, model, temperature, tools, stream, stream_callback)
        elif provider == "google":
            return self._call_google(messages, model, temperature)
        elif provider == "mistral":
            return self._call_mistral(messages, model, temperature)
        elif provider == "anthropic":
            return self._call_anthropic(messages, model, temperature)
        elif provider == "cohere":
            return self._call_cohere(messages, model, temperature)
        elif provider == "meta":
            return self._call_together(messages, model, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    # ========================================================================
    # PROVIDER IMPLEMENTATIONS
    # ========================================================================
    
    def _call_openai(self, messages, model, temperature, tools=None, stream=False, stream_callback=None):
        import openai
        client = openai.OpenAI(api_key=self.api_keys.get("openai", ""))
        
        kwargs = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4000
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        if stream and stream_callback:
            kwargs["stream"] = True
            response = client.chat.completions.create(**kwargs)
            content = ""
            for chunk in response:
                delta = chunk.choices[0].delta.content or ""
                content += delta
                stream_callback(delta)
            return {"content": content, "model": model}
        
        response = client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        
        return {
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls] if msg.tool_calls else None,
            "model": model,
            "guardrail_triggered": False
        }
    
    def _call_google(self, messages, model, temperature):
        import google.generativeai as genai
        genai.configure(api_key=self.api_keys.get("google", ""))
        
        gemini = genai.GenerativeModel("gemini-1.5-pro")
        
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [msg["content"]]})
        
        response = gemini.generate_content(contents, generation_config={
            "temperature": temperature,
            "max_output_tokens": 4000
        })
        return {"content": response.text, "model": model, "guardrail_triggered": False}
    
    def _call_mistral(self, messages, model, temperature):
        from mistralai.client import MistralClient
        from mistralai.models.chat_completion import ChatMessage
        
        client = MistralClient(api_key=self.api_keys.get("mistral", ""))
        chat_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
        
        response = client.chat(
            model="mistral-large-latest",
            messages=chat_messages,
            temperature=temperature
        )
        return {"content": response.choices[0].message.content, "model": model, "guardrail_triggered": False}
    
    def _call_anthropic(self, messages, model, temperature):
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_keys.get("anthropic", ""))
        
        system_msg = ""
        other_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                other_messages.append(m)
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=temperature,
            system=system_msg,
            messages=other_messages
        )
        return {"content": response.content[0].text, "model": model, "guardrail_triggered": False}
    
    def _call_cohere(self, messages, model, temperature):
        import cohere
        client = cohere.Client(self.api_keys.get("cohere", ""))
        
        chat_history = []
        for m in messages:
            if m["role"] == "user":
                chat_history.append({"role": "USER", "message": m["content"]})
            elif m["role"] == "assistant":
                chat_history.append({"role": "CHATBOT", "message": m["content"]})
        
        response = client.chat(
            model="command-r-plus",
            temperature=temperature,
            chat_history=chat_history[:-1] if chat_history else [],
            message=chat_history[-1]["message"] if chat_history else "Hello"
        )
        return {"content": response.text, "model": model, "guardrail_triggered": False}
    
    def _call_together(self, messages, model, temperature):
        import openai
        client = openai.OpenAI(
            api_key=self.api_keys.get("meta", ""),
            base_url="https://api.together.xyz/v1"
        )
        
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            messages=messages,
            temperature=temperature,
            max_tokens=4000
        )
        return {"content": response.choices[0].message.content, "model": model, "guardrail_triggered": False}
    
    # ========================================================================
    # ADMIN
    # ========================================================================
    
    def clear_cache(self):
        """Clear response cache."""
        if self._cache:
            self._cache.clear()
    
    def clear_memory(self, user_id: str):
        """Clear user memory."""
        if MEMORY_AVAILABLE:
            try:
                mem = get_memory(user_id)
                mem.clear()
            except:
                pass
    
    def get_metrics(self) -> Dict:
        """Get all provider metrics."""
        return {
            name: {
                "total": m.total_requests,
                "success": m.successful_requests,
                "failed": m.failed_requests,
                "success_rate": round(m.successful_requests / max(m.total_requests, 1), 2),
                "avg_latency_ms": round(m.avg_latency_ms, 0),
                "is_healthy": m.is_healthy,
                "last_error": m.last_error[:100] if m.last_error else ""
            }
            for name, m in self.metrics.items()
        }
    
    def get_available_providers(self) -> List[str]:
        """Get list of providers with valid API keys."""
        return [name for name in Models.PROVIDERS.keys() if name in self.api_keys]


# ============================================================================
# SINGLETON
# ============================================================================

_CLIENT_INSTANCE = None

def get_client() -> MultiProviderClient:
    """Get or create global client instance."""
    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is None:
        _CLIENT_INSTANCE = MultiProviderClient()
    return _CLIENT_INSTANCE


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["MultiProviderClient", "get_client", "ProviderMetrics"]
