
"""Enhanced API client supporting tool calls."""
import requests
import json
import time
from typing import List, Dict, Optional, Callable

class PollinationsClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://text.pollinations.ai/openai"
        self.image_url = "https://image.pollinations.ai/prompt"
    
    def chat(self, messages: List[Dict], model: str = "openai", 
             temperature: float = 0.7, stream: bool = False,
             tools: Optional[List[Dict]] = None,
             on_chunk: Optional[Callable] = None) -> Dict:
        """Send chat request with optional tool support."""
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        if stream and on_chunk:
            return {"content": self._stream(payload, on_chunk), "tool_calls": None}
        else:
            return self._sync(payload)
    
    def _sync(self, payload: Dict) -> Dict:
        """Non-streaming request."""
        resp = self.session.post(self.base_url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        message = data["choices"][0]["message"]
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls")
        }
    
    def _stream(self, payload: Dict, on_chunk: Callable) -> str:
        """Streaming request."""
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
                    except:
                        continue
        return ''.join(full)
    
    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024) -> str:
        encoded = requests.utils.quote(prompt)
        return f"{self.image_url}/{encoded}?width={width}&height={height}&nologo=true"
    
    def generate_audio(self, text: str, voice: str = "nova") -> str:
        encoded = requests.utils.quote(text)
        return f"https://gen.pollinations.ai/audio/{encoded}?voice={voice}"
