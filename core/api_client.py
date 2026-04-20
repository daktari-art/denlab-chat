"""Enhanced API client for DenLab v4.0.
Supports streaming, tool calls, image generation, and audio generation.
"""
import requests
import json
import time
from typing import List, Dict, Optional, Callable, Any

class PollinationsClient:
    """Enhanced API client supporting tool calls, streaming, and multimodal features."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.base_url = "https://text.pollinations.ai/openai"
        self.image_url = "https://image.pollinations.ai/prompt"
        self.audio_url = "https://gen.pollinations.ai/audio"
    
    def chat(self, 
             messages: List[Dict], 
             model: str = "openai", 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None,
             stream: bool = False,
             tools: Optional[List[Dict]] = None,
             on_chunk: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Send chat request with optional tool support and streaming.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier string
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            tools: Optional list of tool definitions for function calling
            on_chunk: Callback for streaming chunks
            
        Returns:
            Dict with 'content' and optionally 'tool_calls'
        """
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
        resp = self.session.post(self.base_url, json=payload, timeout=60)
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
        resp = self.session.post(self.base_url, json={**payload, "stream": True}, 
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
    
    def generate_image(self, 
                       prompt: str, 
                       width: int = 1024, 
                       height: int = 1024,
                       model: str = "flux",
                       seed: Optional[int] = None,
                       nologo: bool = True) -> str:
        """Generate image URL from prompt.
        
        Args:
            prompt: Image description
            width: Image width in pixels
            height: Image height in pixels
            model: Image model to use
            seed: Optional seed for reproducibility
            nologo: Whether to hide watermark
            
        Returns:
            URL string for the generated image
        """
        encoded = requests.utils.quote(prompt)
        url = f"{self.image_url}/{encoded}?width={width}&height={height}&model={model}"
        if nologo:
            url += "&nologo=true"
        if seed:
            url += f"&seed={seed}"
        return url
    
    def generate_audio(self, text: str, voice: str = "nova") -> str:
        """Generate audio URL from text (TTS).
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            URL string for the generated audio
        """
        encoded = requests.utils.quote(text[:500])
        return f"{self.audio_url}/{encoded}?voice={voice}"
    
    def download_image(self, img_url: str) -> Optional[bytes]:
        """Download image bytes from a URL.
        
        Args:
            img_url: URL of the image to download
            
        Returns:
            Image bytes or None if download failed
        """
        try:
            resp = self.session.get(img_url, timeout=15)
            resp.raise_for_status()
            return resp.content
        except Exception:
            return None
    
    def chat_with_retry(self,
                       messages: List[Dict],
                       model: str = "openai",
                       temperature: float = 0.7,
                       retries: int = 2) -> Dict[str, Any]:
        """Chat with automatic retry on failure.
        
        Args:
            messages: List of message dicts
            model: Model identifier
            temperature: Sampling temperature
            retries: Number of retry attempts
            
        Returns:
            Dict with 'content' and 'tool_calls'
        """
        for attempt in range(retries + 1):
            try:
                return self.chat(messages, model=model, temperature=temperature)
            except requests.exceptions.Timeout:
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return {"content": "❌ Request timed out. Please try again.", "tool_calls": None}
            except requests.exceptions.RequestException:
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return {"content": "❌ Connection error. Check your internet connection.", "tool_calls": None}
            except Exception as e:
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return {"content": f"❌ Error: {str(e)}", "tool_calls": None}
        
        return {"content": "❌ Failed after multiple attempts.", "tool_calls": None}


# Singleton instance
def get_client() -> PollinationsClient:
    """Get or create singleton API client instance."""
    return PollinationsClient()
