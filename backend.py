import requests
import time
from pathlib import Path
from typing import List, Dict

API_URL = "https://text.pollinations.ai/openai"
IMAGE_API = "https://image.pollinations.ai/prompt"
HEADERS = {"Content-Type": "application/json"}

MODELS = {
    "GPT-4o mini": {"name": "openai", "provider": "pollinations"},
    "GPT-4o": {"name": "openai-large", "provider": "pollinations"},
    "Llama 3.3 70B": {"name": "llama", "provider": "pollinations"},
    "DeepSeek-V3": {"name": "deepseek", "provider": "pollinations"},
    "Gemini 2.0 Flash": {"name": "gemini", "provider": "pollinations"},
    "Qwen Coder 32B": {"name": "qwen-coder", "provider": "pollinations"},
}

SYSTEM_PROMPT = """You are DenLab, a professional AI research assistant. You can generate images when users type /imagine followed by a description. You help with code analysis, debugging, technical writing, and research. Be concise, accurate, and helpful. When providing code, use proper markdown code blocks with language specification."""

def chat_api(messages: List[Dict], model_key: str = "openai", retries: int = 2) -> str:
    """Send chat request with model-specific handling."""
    
    # Get actual model name
    model_name = model_key
    
    for attempt in range(retries + 1):
        try:
            # Different payloads for different models
            payload = {
                "model": model_name,
                "messages": messages,
                "stream": False,
                "temperature": 0.7
            }
            
            # Some models need different parameters
            if "deepseek" in model_name:
                payload["max_tokens"] = 2000
            elif "llama" in model_name:
                payload["temperature"] = 0.6
            
            resp = requests.post(
                API_URL,
                headers=HEADERS,
                json=payload,
                timeout=60
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                elif "response" in data:
                    return data["response"]
                else:
                    # Fallback: try to extract any text
                    return str(data)
            
            # If we get here, something went wrong
            if attempt < retries:
                time.sleep(1.5)
                continue
            return f"❌ Model '{model_name}' unavailable. Try GPT-4o mini."
            
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return "❌ Request timed out."
        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return "❌ Connection error."
        except Exception:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return "❌ Unexpected error."
    
    return "❌ Failed after multiple attempts."

def generate_image(prompt: str) -> str:
    """Generate image URL from prompt."""
    encoded = requests.utils.quote(prompt)
    return f"{IMAGE_API}/{encoded}?width=1024&height=1024&nologo=true"

def analyze_file(content: str, filename: str, model_key: str = "openai") -> str:
    """Analyze text/code file content."""
    ext = Path(filename).suffix
    max_chars = 4000
    truncated = len(content) > max_chars
    display = content[:max_chars]
    
    prompt = f"""Analyze this file: {filename}
File type: {ext}
{f'(Truncated to {max_chars} chars)' if truncated else ''}

Content:
\`\`\`{ext[1:] if ext else 'text'}
{display}
\`\`\`

Provide:
1. Purpose
2. Key components
3. Dependencies
4. Issues/suggestions"""
    
    messages = [
        {"role": "system", "content": "You are a code analysis expert. Be technical and concise."},
        {"role": "user", "content": prompt}
    ]
    return chat_api(messages, model_key)

def analyze_image_description(description: str, model_key: str = "openai") -> str:
    """Analyze an image based on user's description."""
    prompt = f"""User uploaded: {description}

Acknowledge the upload and offer to help analyze if they describe the image contents. Be friendly and helpful."""
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    return chat_api(messages, model_key)
