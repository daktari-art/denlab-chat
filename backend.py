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

SYSTEM_PROMPT = """You are DenLab, a professional AI research assistant. You can generate images when users type /imagine followed by a description. You help with code analysis, debugging, technical writing, and research. Be concise, accurate, and helpful."""

def chat_api(messages: List[Dict], model: str = "openai", retries: int = 3) -> str:
    """Send chat request with retry logic and better error handling."""
    for attempt in range(retries):
        try:
            resp = requests.post(
                API_URL,
                headers=HEADERS,
                json={"model": model, "messages": messages, "stream": False},
                timeout=60
            )
            
            if resp.status_code != 200:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return f"❌ API Error {resp.status_code}. Please try again."
            
            data = resp.json()
            
            if "choices" not in data or len(data["choices"]) == 0:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return "❌ No response from AI. Please try again."
            
            return data["choices"][0]["message"]["content"]
            
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return "❌ Request timed out. Please try a smaller file."
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return "❌ Connection error. Check your internet."
        except (KeyError, ValueError):
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return "❌ Unexpected response format. Please try again."
    
    return "❌ Failed after multiple attempts."

def generate_image(prompt: str) -> str:
    """Generate image URL from prompt."""
    encoded = requests.utils.quote(prompt)
    return f"{IMAGE_API}/{encoded}?width=1024&height=1024&nologo=true"

def analyze_file(content: str, filename: str, model: str = "openai") -> str:
    """Analyze text/code file content."""
    ext = Path(filename).suffix
    max_chars = 5000
    truncated = len(content) > max_chars
    display = content[:max_chars]
    
    prompt = f"""Analyze this file: {filename}
File type: {ext}
{f'(File truncated to {max_chars} characters)' if truncated else ''}

Content:
\`\`\`
{display}
\`\`\`

Provide a concise analysis:
1. Purpose - What this file does
2. Structure - Key functions/classes/components
3. Dependencies - What it requires/imports
4. Issues - Any obvious problems or improvements"""
    
    messages = [
        {"role": "system", "content": "You are a code analysis expert. Be technical, thorough, and concise."},
        {"role": "user", "content": prompt}
    ]
    return chat_api(messages, model)

def analyze_image_description(description: str, model: str = "openai") -> str:
    """Analyze an image based on user's description."""
    prompt = f"""The user uploaded an image: {description}

Since I cannot see images directly, I will:
1. Acknowledge the upload
2. Ask what specifically they want to know about the image
3. Offer to help if they describe the image contents

Keep response friendly and helpful."""
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be practical and useful."},
        {"role": "user", "content": prompt}
    ]
    return chat_api(messages, model)
