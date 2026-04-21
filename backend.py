"""Enhanced backend API for DenLab v4.0.
Handles model communication, image generation, file analysis, and tool execution.
"""
import requests
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any

# ============ API CONFIGURATION ============
API_URL = "https://text.pollinations.ai/openai"
IMAGE_API = "https://image.pollinations.ai/prompt"
AUDIO_API = "https://gen.pollinations.ai/audio"
HEADERS = {"Content-Type": "application/json"}

# ============ MODEL REGISTRY ============
MODELS = {
    "GPT-4o": {"name": "openai", "provider": "pollinations", "capabilities": ["text", "vision", "tools"]},
    "GPT-4o mini": {"name": "openai-mini", "provider": "pollinations", "capabilities": ["text", "vision", "tools"]},
    "Claude 3.5 Sonnet": {"name": "claude", "provider": "pollinations", "capabilities": ["text", "vision", "tools"]},
    "Gemini 2.0 Flash": {"name": "gemini", "provider": "pollinations", "capabilities": ["text", "vision", "tools"]},
    "Llama 3.3 70B": {"name": "llama", "provider": "pollinations", "capabilities": ["text", "tools"]},
    "Mistral Large": {"name": "mistral", "provider": "pollinations", "capabilities": ["text", "tools"]},
    "DeepSeek-V3": {"name": "deepseek", "provider": "pollinations", "capabilities": ["text", "tools"]},
    "Qwen 2.5 72B": {"name": "qwen", "provider": "pollinations", "capabilities": ["text", "vision", "tools"]},
    "Kimi K2.5": {"name": "kimi", "provider": "pollinations", "capabilities": ["text", "vision", "tools"]},
}

# ============ SYSTEM PROMPTS ============
SYSTEM_PROMPT = """You are DenLab, an advanced AI research assistant with tool-use capabilities.

Guidelines:
1. Be helpful, accurate, and thorough in your responses
2. Use available tools when they would improve the answer
3. Provide clear explanations with examples when helpful
4. Break down complex tasks into steps
5. Write clean, well-documented code when requested
6. Research topics thoroughly using search when current information is needed
7. Respect user autonomy and provide factual information
8. Decline requests that would cause harm, but remain helpful for legitimate uses

Available tools:
- web_search: Search the live web for current information
- deep_research: Multi-hop research across sources
- execute_code: Run Python code in sandboxed environment
- fetch_url: Scrape specific web pages
- read_file: Read uploaded file contents
- write_file: Save generated content to files

When using tools, think step by step and explain your reasoning."""

CODE_SYSTEM_PROMPT = "You are an expert Python programmer. Write clean, well-documented, production-ready code."

ANALYSIS_SYSTEM_PROMPT = "You are a senior code reviewer and software architect. Provide thorough technical analysis."

# ============ API CLIENT ============
class PollinationsClient:
    """Enhanced client for Pollinations.ai API with streaming and tool support."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def chat(self, 
             messages: List[Dict], 
             model: str = "openai", 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None,
             stream: bool = False,
             tools: Optional[List[Dict]] = None,
             on_chunk: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Send chat request with full streaming and tool support."""
        
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
            return {"content": self._stream(payload, on_chunk), "tool_calls": None}
        
        return self._sync(payload)
    
    def _sync(self, payload: Dict) -> Dict[str, Any]:
        """Non-streaming request."""
        resp = self.session.post(API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        message = data["choices"][0]["message"]
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls")
        }
    
    def _stream(self, payload: Dict, on_chunk: Callable[[str], None]) -> str:
        """Streaming request with chunk callback."""
        full = []
        resp = self.session.post(API_URL, json={**payload, "stream": True}, 
                                stream=True, timeout=60)
        
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
                        if delta.get('content'):
                            full.append(delta['content'])
                            on_chunk(delta['content'])
                    except (json.JSONDecodeError, KeyError):
                        continue
        return ''.join(full)
    
    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024, 
                       model: str = "flux", seed: Optional[int] = None) -> str:
        """Generate image URL from prompt with optional parameters."""
        encoded = requests.utils.quote(prompt)
        url = f"{IMAGE_API}/{encoded}?width={width}&height={height}&model={model}&nologo=true"
        if seed:
            url += f"&seed={seed}"
        return url
    
    def generate_audio(self, text: str, voice: str = "nova") -> str:
        """Generate audio URL from text (TTS)."""
        encoded = requests.utils.quote(text[:500])
        return f"{AUDIO_API}/{encoded}?voice={voice}"
    
    def download_image(self, img_url: str) -> Optional[bytes]:
        """Download image bytes from URL."""
        try:
            resp = self.session.get(img_url, timeout=15)
            resp.raise_for_status()
            return resp.content
        except Exception:
            return None


# ============ API FUNCTIONS ============
def chat_api(messages: List[Dict], 
             model_key: str = "openai", 
             temperature: float = 0.7,
             retries: int = 2) -> str:
    """Send chat request with model-specific handling and retries."""
    
    client = PollinationsClient()
    
    for attempt in range(retries + 1):
        try:
            payload = {
                "model": model_key,
                "messages": messages,
                "stream": False,
                "temperature": temperature
            }
            
            # Model-specific parameters
            if "deepseek" in model_key:
                payload["max_tokens"] = 2000
            elif "llama" in model_key:
                payload["temperature"] = min(temperature, 0.6)
            
            resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                elif "response" in data:
                    return data["response"]
                return str(data)
            
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return f"❌ Model '{model_key}' unavailable (HTTP {resp.status_code}). Try another model."
            
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return "❌ Request timed out. The API may be slow. Try again."
        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return "❌ Connection error. Check your internet connection."
        except Exception:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return "❌ Unexpected error occurred."
    
    return "❌ Failed after multiple attempts."


def stream_chat(messages: List[Dict],
                model_key: str = "openai",
                temperature: float = 0.7,
                on_chunk: Callable[[str], None] = None) -> str:
    """Stream chat response with real-time chunk delivery."""
    client = PollinationsClient()
    result = client.chat(messages, model=model_key, temperature=temperature, 
                        stream=True, on_chunk=on_chunk)
    return result.get("content", "")


# ============ IMAGE FUNCTIONS ============
def generate_image(prompt: str, width: int = 1024, height: int = 1024, 
                   model: str = "flux") -> str:
    """Generate image URL from prompt."""
    client = PollinationsClient()
    return client.generate_image(prompt, width, height, model)


def generate_image_with_download(prompt: str, width: int = 1024, height: int = 1024,
                                  model: str = "flux") -> Dict[str, Any]:
    """Generate image and return both URL and downloadable bytes."""
    client = PollinationsClient()
    url = client.generate_image(prompt, width, height, model)
    
    # Attempt to download the image
    img_data = client.download_image(url)
    
    return {
        "url": url,
        "data": img_data,
        "success": img_data is not None
    }


# ============ AUDIO FUNCTIONS ============
def generate_audio(text: str, voice: str = "nova") -> str:
    """Generate audio URL from text."""
    client = PollinationsClient()
    return client.generate_audio(text, voice)


# ============ FILE ANALYSIS ============
def analyze_file(content: str, filename: str, model_key: str = "openai") -> str:
    """Analyze text/code file content with structured output."""
    ext = Path(filename).suffix
    max_chars = 4000
    truncated = len(content) > max_chars
    display = content[:max_chars]
    
    prompt = f"""Analyze this file: {filename}
File type: {ext}
{f'(Truncated to {max_chars} chars)' if truncated else ''}

Content:
```{ext[1:] if ext else 'text'}
{display}
```

Provide a structured analysis covering:
1. **Purpose** - What this file does
2. **Key Components** - Main functions, classes, or sections
3. **Dependencies** - External libraries or modules used
4. **Code Quality** - Structure, patterns, best practices
5. **Issues/Suggestions** - Potential bugs, improvements, security concerns
6. **Documentation** - Docstring and comment quality"""
    
    messages = [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    return chat_api(messages, model_key)


def analyze_image_file(image_bytes: bytes, filename: str, model_key: str = "gemini") -> str:
    """Analyze image file using vision-capable model."""
    import base64
    
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Describe this image in detail: {filename}"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
                }
            ]
        }
    ]
    
    return chat_api(messages, model_key)


# ============ CODE EXECUTION ============
def execute_python(code: str) -> Dict[str, Any]:
    """Execute Python code safely in sandboxed environment."""
    import io
    import sys
    import traceback
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    
    try:
        exec(code, {"__builtins__": __builtins__})
        stdout = sys.stdout.getvalue()
        stderr = sys.stderr.getvalue()
        return {"success": True, "stdout": stdout, "stderr": stderr, "error": None}
    except Exception as e:
        return {
            "success": False,
            "stdout": sys.stdout.getvalue(),
            "stderr": sys.stderr.getvalue(),
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


# ============ WEB SEARCH ============
def web_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search the web using DuckDuckGo API."""
    try:
        url = f"https://ddg-api.herokuapp.com/search?query={requests.utils.quote(query)}&limit={limit}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data[:limit]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", "")
                })
            return {"success": True, "results": results, "query": query}
        return {"success": False, "error": f"Search API returned {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def deep_research(topic: str, depth: int = 2) -> Dict[str, Any]:
    """Conduct deep multi-source research with follow-up searches."""
    try:
        findings = []
        sources = set()
        
        # First level search
        search_result = web_search(topic)
        if search_result.get("success"):
            for item in search_result["results"][:3]:
                sources.add(item["url"])
                findings.append({
                    "title": item["title"],
                    "source": item["url"],
                    "content": item["snippet"]
                })
        
        # Deeper search if requested
        if depth > 1 and findings:
            for finding in findings[:2]:
                sub_search = web_search(finding["title"], limit=3)
                if sub_search.get("success"):
                    for item in sub_search["results"][:2]:
                        if item["url"] not in sources:
                            sources.add(item["url"])
                            findings.append({
                                "title": item["title"],
                                "source": item["url"],
                                "content": item["snippet"]
                            })
        
        return {
            "success": True,
            "topic": topic,
            "total_sources": len(sources),
            "findings": findings
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ URL FETCHING ============
def fetch_url_content(url: str) -> Dict[str, Any]:
    """Fetch and extract content from a URL."""
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "DenLab/4.0"})
        if response.status_code == 200:
            # Try to extract readable text
            content = response.text[:5000]
            return {"success": True, "content": content, "status_code": 200, "url": url}
        return {"success": False, "error": f"HTTP {response.status_code}", "url": url}
    except Exception as e:
        return {"success": False, "error": str(e), "url": url}


# ============ UTILITY FUNCTIONS ============
def get_model_capabilities(model_key: str) -> List[str]:
    """Get capabilities for a given model."""
    for name, info in MODELS.items():
        if info["name"] == model_key:
            return info.get("capabilities", ["text"])
    return ["text"]


def supports_vision(model_key: str) -> bool:
    """Check if model supports vision."""
    caps = get_model_capabilities(model_key)
    return "vision" in caps


def supports_tools(model_key: str) -> bool:
    """Check if model supports tool use."""
    caps = get_model_capabilities(model_key)
    return "tools" in caps


def parse_image_command(text: str) -> Optional[Dict[str, Any]]:
    """Parse /imagine command with optional --ar ratio."""
    if not text.lower().startswith('/imagine'):
        return None
    
    prompt = text[8:].strip()
    ratio = "1:1"
    
    # Parse aspect ratio
    ar_match = re.search(r'--ar\s+(\d+:\d+)', prompt)
    if ar_match:
        ratio = ar_match.group(1)
        prompt = re.sub(r'--ar\s+\d+:\d+', '', prompt).strip()
    
    # Standard ratios
    ratios = {
        "1:1": (1024, 1024),
        "16:9": (1024, 576),
        "9:16": (576, 1024),
        "4:3": (1024, 768),
        "3:4": (768, 1024),
    }
    width, height = ratios.get(ratio, (1024, 1024))
    
    return {
        "prompt": prompt,
        "ratio": ratio,
        "width": width,
        "height": height
    }
