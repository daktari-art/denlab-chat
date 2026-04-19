import requests
import time
from pathlib import Path
from typing import List, Dict

API_URL = "https://text.pollinations.ai/openai"
IMAGE_API = "https://image.pollinations.ai/prompt"
HEADERS = {"Content-Type": "application/json"}

MODELS = {
    "GPT-4o mini": "openai",
    "GPT-4o": "openai-large",
    "Llama 3.3 70B": "llama",
    "DeepSeek-V3": "deepseek",
    "Gemini 2.0 Flash": "gemini",
    "Qwen Coder 32B": "qwen-coder",
}

SYSTEM_PROMPT = """You are DenLab, a professional AI research assistant. You help with code analysis, debugging, technical writing, and research. Be concise, accurate, and helpful."""

def chat_api(messages: List[Dict], model: str = "openai", retries: int = 2) -> str:
    """Send chat request with retry logic."""
    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                API_URL,
                headers=HEADERS,
                json={"model": model, "messages": messages, "stream": False},
                timeout=45
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(1)
                continue
            return "⚠️ Request timed out. Please try again."
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return f"⚠️ Connection error: {str(e)}"
        except (KeyError, IndexError):
            return "⚠️ Unexpected API response. Please try again."
    return "⚠️ Failed after multiple attempts."

def generate_image(prompt: str) -> str:
    """Generate image URL from prompt."""
    encoded = requests.utils.quote(prompt)
    return f"{IMAGE_API}/{encoded}?width=1024&height=1024&nologo=true"

def analyze_file(content: str, filename: str, model: str = "openai") -> str:
    """Analyze text/code file content."""
    ext = Path(filename).suffix
    max_chars = 6000
    truncated = len(content) > max_chars
    display = content[:max_chars]
    
    prompt = f"""Analyze this file: {filename}
File type: {ext}
{f'⚠️ Truncated to {max_chars} chars' if truncated else ''}

Content:
\`\`\`
{display}
\`\`\`

Provide:
1. Purpose & structure
2. Key components
3. Potential issues
4. Summary"""
    
    messages = [
        {"role": "system", "content": "You are a code analysis expert. Be technical and precise."},
        {"role": "user", "content": prompt}
    ]
    return chat_api(messages, model)
