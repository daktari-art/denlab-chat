"""
Multi-Provider LLM Client with Pollinations.ai as Default Free Provider.
Uses Pollinations.ai (no API key required) as primary, with optional paid fallbacks.
"""

import streamlit as st
import json
import hashlib
import time
import requests
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
# MULTI-PROVIDER CLIENT (Pollinations.ai as Primary)
# ============================================================================

class MultiProviderClient:
    """
    LLM client with Pollinations.ai as the free default provider.
    Falls back to paid providers only if API keys are configured.
    """
    
    # Pollinations is always first since it's free and requires no API key
    FALLBACK_CHAIN = ["pollinations", "openai", "google", "mistral", "anthropic", "cohere", "meta"]
    
    def __init__(self):
        self.api_keys: Dict[str, str] = {}
        self._load_api_keys()
        self._cache = get_cache() if CACHE_AVAILABLE else None
        self._memory = None
        self.metrics: Dict[str, ProviderMetrics] = {
            name: ProviderMetrics()
            for name in self.FALLBACK_CHAIN
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
        if provider not in self.metrics:
            self.metrics[provider] = ProviderMetrics()
        m = self.metrics[provider]
        m.total_requests += 1
        if success:
            m.successful_requests += 1
        else:
            m.failed_requests += 1
            m.last_error = error
            if m.failed_requests > 3 and m.total_requests > 0 and m.failed_requests / m.total_requests > 0.7:
                m.is_healthy = False
        m.avg_latency_ms = (m.avg_latency_ms * (m.total_requests - 1) + latency_ms) / max(m.total_requests, 1)
        m.last_used = time.time()
    
    def _get_fallback_chain(self, primary: str) -> List[str]:
        """Get ordered fallback providers. Pollinations is always available."""
        chain = []
        
        # Always try Pollinations first if no API keys are set
        if primary == "pollinations" or not self.api_keys:
            chain.append("pollinations")
        
        # Add the primary if it's not pollinations
        if primary != "pollinations" and primary in self.api_keys:
            chain.append(primary)
        
        # Add remaining providers that have API keys and are healthy
        for p in self.FALLBACK_CHAIN:
            if p not in chain and p != "pollinations":
                if p in self.api_keys:
                    chain.append(p)
        
        # Ensure pollinations is always available as last resort
        if "pollinations" not in chain:
            chain.append("pollinations")
        
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
        Uses Pollinations.ai as the free default.
        """
        model = model or Models.DEFAULT_MODEL
        api_name, config = self._get_provider_config(model)
        
        # If no API keys are set at all, force Pollinations
        if not self.api_keys:
            api_name = "pollinations"
        
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
        
        if provider == "pollinations":
            return self._call_pollinations(messages, model, temperature, stream, stream_callback)
        elif provider == "openai":
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
            # Unknown provider - try Pollinations as ultimate fallback
            return self._call_pollinations(messages, model, temperature, stream, stream_callback)
    
    # ========================================================================
    # POLLINATIONS.AI (Free, no API key required)
    # ========================================================================
    
    def _call_pollinations(self, messages, model, temperature, stream=False, stream_callback=None):
        """Call Pollinations.ai - completely free, no API key needed."""
        url = "https://text.pollinations.ai/openai"
        
        payload = {
            "model": "openai",
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        if stream and stream_callback:
            payload["stream"] = True
            full_response = ""
            try:
                response = requests.post(url, json=payload, stream=True, timeout=120)
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_response += content
                                stream_callback(content)
                        except json.JSONDecodeError:
                            continue
                return {"content": full_response, "model": model, "guardrail_triggered": False}
            except Exception as e:
                raise Exception(f"Pollinations.ai error: {str(e)}")
        
        # Non-streaming
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return {
                "content": content,
                "model": model,
                "guardrail_triggered": False
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Pollinations.ai request failed: {str(e)}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise Exception(f"Pollinations.ai response parsing failed: {str(e)}")
    
    # ========================================================================
    # OPENAI (Requires API Key)
    # ========================================================================
    
    def _call_openai(self, messages, model, temperature, tools=None, stream=False, stream_callback=None):
        """Call OpenAI - requires OPENAI_API_KEY."""
        try:
            import openai
        except ImportError:
            raise Exception("OpenAI package not installed. Run: pip install openai")
        
        api_key = self.api_keys.get("openai", "")
        if not api_key:
            raise Exception("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
        
        client = openai.OpenAI(api_key=api_key)
        
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
        try:
            import google.generativeai as genai
        except ImportError:
            raise Exception("Google Generative AI package not installed. Run: pip install google-generativeai")
        
        api_key = self.api_keys.get("google", "")
        if not api_key:
            raise Exception("Google API key not configured.")
        
        genai.configure(api_key=api_key)
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
        try:
            from mistralai.client import MistralClient
            from mistralai.models.chat_completion import ChatMessage
        except ImportError:
            raise Exception("Mistral package not installed.")
        
        api_key = self.api_keys.get("mistral", "")
        if not api_key:
            raise Exception("Mistral API key not configured.")
        
        client = MistralClient(api_key=api_key)
        chat_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
        
        response = client.chat(
            model="mistral-large-latest",
            messages=chat_messages,
            temperature=temperature
        )
        return {"content": response.choices[0].message.content, "model": model, "guardrail_triggered": False}
    
    def _call_anthropic(self, messages, model, temperature):
        try:
            import anthropic
        except ImportError:
            raise Exception("Anthropic package not installed.")
        
        api_key = self.api_keys.get("anthropic", "")
        if not api_key:
            raise Exception("Anthropic API key not configured.")
        
        client = anthropic.Anthropic(api_key=api_key)
        
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
        try:
            import cohere
        except ImportError:
            raise Exception("Cohere package not installed.")
        
        api_key = self.api_keys.get("cohere", "")
        if not api_key:
            raise Exception("Cohere API key not configured.")
        
        client = cohere.Client(api_key)
        
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
        try:
            import openai
        except ImportError:
            raise Exception("OpenAI package not installed.")
        
        api_key = self.api_keys.get("meta", "")
        if not api_key:
            raise Exception("Together API key not configured.")
        
        client = openai.OpenAI(
            api_key=api_key,
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
        """Get list of available providers."""
        available = ["pollinations"]  # Always available
        for name in Models.PROVIDERS.keys():
            if name in self.api_keys:
                available.append(name)
        return available


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