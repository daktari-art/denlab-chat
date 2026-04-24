"""MultiProvider AI Client with Guardrails, Fallback Support, Cache, and Memory.
Supports Pollinations.ai primary with automatic fallback providers.
Includes content safety guardrails, response caching, and memory integration.
"""
import requests
import json
import time
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from functools import lru_cache

# ============ CACHE SYSTEM ============
class ResponseCache:
    """Cache LLM responses to reduce API calls."""
    
    def __init__(self, cache_dir: str = "data/cache", max_size: int = 100, ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self._cache: Dict[str, Dict] = {}
        self._load()
    
    def _get_key(self, messages: list, model: str, temperature: float) -> str:
        """Generate cache key from messages and parameters."""
        recent_msgs = messages[-3:] if len(messages) > 3 else messages
        content = json.dumps(recent_msgs, sort_keys=True) + model + str(temperature)
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, messages: list, model: str, temperature: float = 0.7) -> Optional[str]:
        """Get cached response if available."""
        key = self._get_key(messages, model, temperature)
        
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() - entry["timestamp"] < self.ttl:
                return entry["response"]
            else:
                del self._cache[key]
                self._save()
        return None
    
    def set(self, messages: list, model: str, response: str, temperature: float = 0.7):
        """Cache a response."""
        key = self._get_key(messages, model, temperature)
        
        if len(self._cache) >= self.max_size:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest]
        
        self._cache[key] = {
            "response": response,
            "timestamp": datetime.now(),
            "model": model
        }
        self._save()
    
    def clear(self):
        self._cache = {}
        self._save()
    
    def stats(self) -> Dict:
        return {"size": len(self._cache), "max_size": self.max_size}
    
    def _load(self):
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
        cache_file = self.cache_dir / "cache.json"
        try:
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


# ============ HIERARCHICAL MEMORY ============
from dataclasses import dataclass

@dataclass
class MemoryEntry:
    content: str
    role: str
    timestamp: datetime
    importance: float = 0.5

class HierarchicalMemory:
    """Three-tier memory: working, episodic, semantic."""
    
    def __init__(self, user_id: str, persist_dir: str = "data/memories"):
        self.user_id = user_id
        self.persist_dir = Path(persist_dir) / user_id
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.working: List[MemoryEntry] = []
        self.episodic: List[Dict] = []
        self.semantic: Dict[str, Any] = {}
        self._load()
    
    def add(self, content: str, role: str, importance: float = 0.5):
        entry = MemoryEntry(content=content, role=role, timestamp=datetime.now(), importance=importance)
        self.working.append(entry)
        self._save()
        
        if len(self.working) > 15:
            self._consolidate()
    
    def _consolidate(self):
        if len(self.working) < 5:
            return
        
        points = []
        for entry in self.working[-10:]:
            if entry.role == "user" and len(entry.content) > 20:
                points.append(f"- {entry.content[:100]}")
        
        self.episodic.append({
            "summary": "\n".join(points) if points else "No key points",
            "timestamp": datetime.now().isoformat(),
            "message_count": len(self.working)
        })
        
        self.working = self.working[-5:]
        self._save()
    
    def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict]:
        results = []
        query_lower = query.lower()
        
        for entry in reversed(self.working[-5:]):
            if any(word in query_lower for word in entry.content.lower().split()[:5]):
                results.append({
                    "type": "working",
                    "content": entry.content[:500],
                    "role": entry.role,
                    "relevance": 0.9
                })
        
        for ep in self.episodic[-5:]:
            if any(word in query_lower for word in ep["summary"].lower().split()[:10]):
                results.append({
                    "type": "episodic",
                    "content": ep["summary"],
                    "relevance": 0.7
                })
        
        for key, value in list(self.semantic.items())[-10:]:
            if key in query_lower:
                results.append({
                    "type": "semantic",
                    "content": str(value)[:500],
                    "relevance": 0.8
                })
        
        return sorted(results, key=lambda x: x["relevance"], reverse=True)[:limit]
    
    def store_knowledge(self, key: str, value: Any):
        self.semantic[key.lower()] = value
        self._save()
    
    def get_context(self, query: str, max_tokens: int = 1000) -> str:
        memories = self.retrieve_relevant(query, limit=3)
        if not memories:
            return ""
        
        parts = ["## Relevant Memories\n"]
        for mem in memories:
            parts.append(f"[{mem['type'].upper()}] {mem['content']}\n")
        return "\n".join(parts)[:max_tokens]
    
    def clear_working(self):
        self.working = []
        self._save()
    
    def _save(self):
        data = {
            "working": [(e.content, e.role, e.timestamp.isoformat(), e.importance) for e in self.working],
            "episodic": self.episodic,
            "semantic": self.semantic
        }
        with open(self.persist_dir / "memory.json", "w") as f:
            json.dump(data, f, indent=2)
    
    def _load(self):
        memory_file = self.persist_dir / "memory.json"
        if memory_file.exists():
            try:
                with open(memory_file) as f:
                    data = json.load(f)
                self.working = [
                    MemoryEntry(content=c, role=r, timestamp=datetime.fromisoformat(t), importance=imp)
                    for c, r, t, imp in data.get("working", [])
                ]
                self.episodic = data.get("episodic", [])
                self.semantic = data.get("semantic", {})
            except Exception:
                pass


# ============ CONTENT GUARDRAILS ============
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
        self._compiled_patterns = {}
        for category, patterns in self.HARMFUL_CATEGORIES.items():
            self._compiled_patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        self._safe_patterns = [re.compile(p, re.IGNORECASE) for p in self.SAFE_CONTEXTS]
    
    def check(self, content: str) -> Dict[str, Any]:
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
        category = check_result.get("category", "unknown")
        
        responses = {
            "child_exploitation": "I cannot assist with requests involving child exploitation or abuse...",
            "extreme_violence": "I cannot provide detailed instructions for harming others...",
            "illegal_activities": "I cannot assist with illegal activities or creating harmful materials...",
            "self_harm": "I'm sorry you're feeling this way. Please reach out for support: 988 Suicide & Crisis Lifeline...",
            "non_consensual": "I cannot assist with non-consensual sexual content or assault...",
        }
        
        return responses.get(category, "I'm not able to help with this request as it may involve harmful content.")


# ============ TOOL ROUTER ============
class ToolRouter:
    """Intelligent tool selection based on query intent."""
    
    def __init__(self):
        self.intents = [
            {"name": "research", "keywords": ["research", "find", "search", "look up", "what is", "who is"], "tools": ["web_search", "deep_research"]},
            {"name": "code", "keywords": ["code", "script", "program", "execute", "run", "calculate"], "tools": ["execute_code"]},
            {"name": "file_ops", "keywords": ["read file", "write file", "save", "load", "open file"], "tools": ["read_file", "write_file"]},
            {"name": "web_scrape", "keywords": ["scrape", "fetch url", "get website", "extract from"], "tools": ["fetch_url"]},
            {"name": "image_analysis", "keywords": ["analyze image", "describe image", "what's in this image"], "tools": ["analyze_image"]},
            {"name": "audio", "keywords": ["read aloud", "speak", "audio", "text to speech"], "tools": ["generate_audio"]},
        ]
        
        self.boost_patterns = {
            "deep_research": r"\b(deep|thorough|comprehensive|detailed)\s+(research|analysis)\b",
            "execute_code": r"\b(run|execute|calculate)\b.*\b(code|script|program)\b",
            "web_search": r"\b(current|latest|recent)\s+(news|information|data)\b",
        }
    
    def route(self, query: str, available_tools: List[str]) -> Dict[str, any]:
        query_lower = query.lower()
        selected_tools = []
        primary_intent = None
        confidence = 0.0
        
        for intent in self.intents:
            if any(kw in query_lower for kw in intent["keywords"]):
                for tool in intent["tools"]:
                    if tool in available_tools and tool not in selected_tools:
                        selected_tools.append(tool)
                if primary_intent is None:
                    primary_intent = intent["name"]
                    confidence = 0.6
        
        for tool, pattern in self.boost_patterns.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                if tool not in selected_tools and tool in available_tools:
                    selected_tools.append(tool)
                confidence = min(confidence + 0.2, 1.0)
        
        depth = 3 if any(w in query_lower for w in ["thorough", "comprehensive", "deep"]) else 2 if "detailed" in query_lower else 1
        
        return {
            "selected_tools": selected_tools,
            "primary_intent": primary_intent or "general",
            "confidence": confidence,
            "depth": depth,
            "needs_agent": len(selected_tools) > 0
        }


# ============ MULTI-PROVIDER CLIENT ============
class MultiProviderClient:
    """AI client with multi-provider fallback, cache, memory, and guardrails."""
    
    PROVIDERS = {
        "pollinations": {
            "base_url": "https://text.pollinations.ai/openai",
            "image_url": "https://image.pollinations.ai/prompt",
            "audio_url": "https://gen.pollinations.ai/audio",
            "models": ["openai", "openai-mini", "claude", "gemini", "llama", "mistral", "deepseek", "qwen", "kimi"],
        },
    }
    
    def __init__(self, primary: str = "pollinations", enable_cache: bool = True, enable_memory: bool = True):
        self.primary = primary
        self.enable_cache = enable_cache
        self.enable_memory = enable_memory
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.guardrails = ContentGuardrails()
        self.router = ToolRouter()
        self._last_provider = None
        self._cache = ResponseCache() if enable_cache else None
        self._memory: Dict[str, HierarchicalMemory] = {}
    
    def _get_memory(self, user_id: str) -> Optional[HierarchicalMemory]:
        if not self.enable_memory:
            return None
        if user_id not in self._memory:
            self._memory[user_id] = HierarchicalMemory(user_id)
        return self._memory[user_id]
    
    def _get_provider_url(self, provider: Optional[str] = None) -> str:
        name = provider or self.primary
        return self.PROVIDERS.get(name, self.PROVIDERS["pollinations"])["base_url"]
    
    def _do_request(self, payload: Dict, provider: Optional[str] = None, stream: bool = False) -> requests.Response:
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
             on_chunk: Optional[Callable[[str], None]] = None,
             user_id: Optional[str] = None) -> Dict[str, Any]:
        """Send chat request with multi-provider fallback, cache, and memory."""
        
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
        
        # Get memory context
        if user_id:
            memory = self._get_memory(user_id)
            if memory:
                last_user_msg = ""
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        last_user_msg = msg.get("content", "")
                        break
                if last_user_msg:
                    context = memory.get_context(last_user_msg)
                    if context:
                        for msg in messages:
                            if msg.get("role") == "system":
                                msg["content"] = msg.get("content", "") + "\n\n" + context
                                break
                        else:
                            messages.insert(0, {"role": "system", "content": context})
        
        # Check cache
        if self._cache and not stream:
            cached = self._cache.get(messages, model, temperature)
            if cached:
                if user_id and self._get_memory(user_id):
                    mem = self._get_memory(user_id)
                    for msg in reversed(messages):
                        if msg.get("role") == "user":
                            mem.add(msg.get("content", ""), "user")
                            break
                    mem.add(cached, "assistant")
                return {"content": cached, "tool_calls": None, "provider": "cache", "cached": True}
        
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
        
        return self._sync_with_fallback(payload, model, messages, temperature, user_id)
    
    def _sync_with_fallback(self, payload: Dict, model: str, messages: List[Dict], temperature: float, user_id: Optional[str]) -> Dict[str, Any]:
        providers = [self.primary, "pollinations_backup"] if hasattr(self, 'PROVIDERS') and "pollinations_backup" in self.PROVIDERS else [self.primary]
        
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
                        if self._cache and content:
                            self._cache.set(messages, model, content, temperature)
                        
                        # Store in memory
                        if user_id and content:
                            memory = self._get_memory(user_id)
                            if memory:
                                for msg in reversed(messages):
                                    if msg.get("role") == "user":
                                        memory.add(msg.get("content", ""), "user")
                                        break
                                memory.add(content, "assistant")
                        
                        return {
                            "content": content or "",
                            "tool_calls": tool_calls,
                            "provider": provider
                        }
            except Exception:
                continue
        
        return {
            "content": "I'm having trouble connecting to the AI service. Please try again.",
            "tool_calls": None,
            "provider": "failed",
            "error": "All providers failed"
        }
    
    def _stream_with_fallback(self, payload: Dict, on_chunk: Callable[[str], None]) -> str:
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
    
    def route_query(self, query: str, available_tools: List[str]) -> Dict[str, any]:
        """Route query to appropriate tools."""
        return self.router.route(query, available_tools)
    
    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024,
                       model: str = "flux", seed: Optional[int] = None,
                       nologo: bool = True) -> str:
        encoded = requests.utils.quote(prompt)
        url = f"{self.PROVIDERS[self.primary]['image_url']}/{encoded}?width={width}&height={height}&model={model}"
        if nologo:
            url += "&nologo=true"
        if seed:
            url += f"&seed={seed}"
        return url
    
    def generate_audio(self, text: str, voice: str = "nova") -> str:
        encoded = requests.utils.quote(text[:500])
        return f"{self.PROVIDERS[self.primary]['audio_url']}/{encoded}?voice={voice}"
    
    def download_image(self, img_url: str) -> Optional[bytes]:
        try:
            resp = self.session.get(img_url, timeout=15)
            resp.raise_for_status()
            return resp.content
        except Exception:
            return None
    
    def get_cache_stats(self) -> Dict:
        if self._cache:
            return self._cache.stats()
        return {"enabled": False}
    
    def clear_cache(self):
        if self._cache:
            self._cache.clear()
    
    def clear_memory(self, user_id: str):
        if user_id in self._memory:
            self._memory[user_id].clear_working()


# Singleton
_client_instance = None

def get_client(enable_cache: bool = True, enable_memory: bool = True) -> MultiProviderClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = MultiProviderClient(enable_cache=enable_cache, enable_memory=enable_memory)
    return _client_instance
