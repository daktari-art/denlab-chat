"""MultiProvider AI Client with Guardrails and Fallback Support.
Supports Pollinations.ai primary with automatic fallback providers.
Includes content safety guardrails to filter harmful requests.
"""
import requests
import json
import time
import re
from typing import List, Dict, Optional, Callable, Any

class ContentGuardrails:
    """Safety guardrails to filter harmful content while allowing legitimate requests."""
    
    # Categories of harmful content to block
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
    
    # Educational/legitimate context keywords that should not be blocked
    SAFE_CONTEXTS = [
        r"\b(educational|academic|research|history|literature|fiction|story|novel|essay|analysis)\b",
        r"\b(for a game|for a movie|for a script|creative writing|hypothetical|what if)\b",
        r"\b(prevent|stop|avoid|report|therapy|counseling|mental health|crisis)\b",
        r"\b(legal advice|law|court|case study|policy|regulation)\b",
    ]
    
    def __init__(self):
        self._compiled_patterns = {}
        for category, patterns in self.HARMFUL_CATEGORIES.items():
            self._compiled_patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        self._safe_patterns = [re.compile(p, re.IGNORECASE) for p in self.SAFE_CONTEXTS]
    
    def check(self, content: str) -> Dict[str, Any]:
        """Check content against guardrails.
        
        Returns dict with 'safe' (bool), 'category' (str or None), 'reason' (str).
        """
        if not content or not isinstance(content, str):
            return {"safe": True, "category": None, "reason": "Empty content"}
        
        # Check for safe educational context first
        has_safe_context = any(p.search(content) for p in self._safe_patterns)
        
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    # If it matches harmful pattern but has safe context, allow it
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
            "child_exploitation": (
                "I cannot assist with requests involving child exploitation or abuse. "
                "This is illegal and harmful. If you have concerns about child safety, "
                "please contact the National Center for Missing & Exploited Children (1-800-THE-LOST) "
                "or your local authorities."
            ),
            "extreme_violence": (
                "I cannot provide detailed instructions for harming others. "
                "If you're experiencing thoughts of violence, please reach out to a mental health professional "
                "or crisis helpline. If you're concerned about someone else's safety, contact emergency services."
            ),
            "illegal_activities": (
                "I cannot assist with illegal activities or creating harmful materials. "
                "If you have questions about legal alternatives or safety information, I'm happy to help with that."
            ),
            "self_harm": (
                "I'm sorry you're feeling this way. I'm not able to provide that information. "
                "Please reach out for support: 988 Suicide & Crisis Lifeline (call or text 988), "
                "or Crisis Text Line (text HOME to 741741). You matter, and help is available."
            ),
            "non_consensual": (
                "I cannot assist with non-consensual sexual content or assault. "
                "If you or someone you know needs help, contact RAINN (1-800-656-HOPE) "
                "or the National Domestic Violence Hotline (1-800-799-SAFE)."
            ),
        }
        
        return responses.get(category, (
            "I'm not able to help with this request as it may involve harmful content. "
            "I'm happy to assist with other questions or topics instead."
        ))


class MultiProviderClient:
    """AI client with multi-provider fallback and content guardrails."""
    
    PROVIDERS = {
        "pollinations": {
            "base_url": "https://text.pollinations.ai/openai",
            "image_url": "https://image.pollinations.ai/prompt",
            "audio_url": "https://gen.pollinations.ai/audio",
            "models": ["openai", "openai-mini", "claude", "gemini", "llama", "mistral", "deepseek", "qwen", "kimi"],
        },
        "pollinations_backup": {
            "base_url": "https://text.pollinations.ai/openai",
            "image_url": "https://image.pollinations.ai/prompt",
            "audio_url": "https://gen.pollinations.ai/audio",
            "models": ["openai", "gemini", "llama"],
        },
    }
    
    def __init__(self, primary: str = "pollinations"):
        self.primary = primary
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.guardrails = ContentGuardrails()
        self._last_provider = None
    
    def _get_provider_url(self, provider: Optional[str] = None) -> str:
        name = provider or self.primary
        return self.PROVIDERS.get(name, self.PROVIDERS["pollinations"])["base_url"]
    
    def _do_request(self, payload: Dict, provider: Optional[str] = None, stream: bool = False) -> requests.Response:
        """Execute HTTP request with timeout and error handling."""
        url = self._get_provider_url(provider)
        
        if stream:
            return self.session.post(url, json=payload, stream=True, timeout=60)
        return self.session.post(url, json=payload, timeout=60)
    
    def chat(self, 
             messages: List[Dict], 
             model: str = "openai", 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None,
             stream: bool = False,
             tools: Optional[List[Dict]] = None,
             on_chunk: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Send chat request with multi-provider fallback.
        
        Returns dict with 'content', 'tool_calls', 'provider' keys.
        """
        # Check guardrails on the last user message
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
        
        if stream and on_chunk:
            content = self._stream_with_fallback(payload, on_chunk)
            return {"content": content, "tool_calls": None, "provider": self._last_provider}
        
        return self._sync_with_fallback(payload, model)
    
    def _sync_with_fallback(self, payload: Dict, model: str) -> Dict[str, Any]:
        """Try sync request with fallback providers."""
        providers = [self.primary, "pollinations_backup"]
        
        for provider in providers:
            try:
                resp = self._do_request(payload, provider)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        msg = data["choices"][0].get("message", {})
                        content = msg.get("content", "")
                        tool_calls = msg.get("tool_calls")
                        
                        # Validate response - reject empty content without tool_calls
                        if not content and not tool_calls:
                            continue
                        
                        self._last_provider = provider
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
        
        # All providers failed
        return {
            "content": "I'm having trouble connecting to the AI service. Please try again in a moment.",
            "tool_calls": None,
            "provider": "failed",
            "error": "All providers failed"
        }
    
    def _stream_with_fallback(self, payload: Dict, on_chunk: Callable[[str], None]) -> str:
        """Try streaming with fallback providers."""
        providers = [self.primary, "pollinations_backup"]
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
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
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
    
    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024,
                       model: str = "flux", seed: Optional[int] = None,
                       nologo: bool = True) -> str:
        """Generate image URL from prompt."""
        encoded = requests.utils.quote(prompt)
        url = f"{self.PROVIDERS[self.primary]['image_url']}/{encoded}?width={width}&height={height}&model={model}"
        if nologo:
            url += "&nologo=true"
        if seed:
            url += f"&seed={seed}"
        return url
    
    def generate_audio(self, text: str, voice: str = "nova") -> str:
        """Generate audio URL from text (TTS)."""
        encoded = requests.utils.quote(text[:500])
        return f"{self.PROVIDERS[self.primary]['audio_url']}/{encoded}?voice={voice}"
    
    def download_image(self, img_url: str) -> Optional[bytes]:
        """Download image bytes from URL."""
        try:
            resp = self.session.get(img_url, timeout=15)
            resp.raise_for_status()
            return resp.content
        except Exception:
            return None


# Convenience function
def get_client() -> MultiProviderClient:
    """Get a MultiProviderClient instance."""
    return MultiProviderClient()
