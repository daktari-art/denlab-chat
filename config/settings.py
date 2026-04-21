"""Central configuration for DenLab v4.0."""
import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class AppConfig:
    TITLE: str = "DenLab"
    ICON: str = "🧪"
    VERSION: str = "4.0.0"
    MAX_HISTORY: int = 100
    MAX_FILE_SIZE_MB: int = 10
    DEFAULT_TEMPERATURE: float = 0.7
    
    API_BASE: str = "https://gen.pollinations.ai"
    API_LEGACY: str = "https://text.pollinations.ai/openai"
    IMAGE_API: str = "https://image.pollinations.ai/prompt"
    
    ENABLE_STREAMING: bool = True
    ENABLE_AUDIO: bool = True
    ENABLE_VISION: bool = True
    ENABLE_AGENT_MODE: bool = True
    ENABLE_PWA: bool = True

CONFIG = AppConfig()

# Model registry with capabilities
MODELS = {
    "GPT-4o": {"name": "openai", "capabilities": ["text", "vision", "tools"]},
    "GPT-4o mini": {"name": "openai-mini", "capabilities": ["text", "vision", "tools"]},
    "Claude 3.5 Sonnet": {"name": "claude", "capabilities": ["text", "vision", "tools"]},
    "Gemini 2.0 Flash": {"name": "gemini", "capabilities": ["text", "vision", "tools"]},
    "Llama 3.3 70B": {"name": "llama", "capabilities": ["text", "tools"]},
    "Mistral Large": {"name": "mistral", "capabilities": ["text", "tools"]},
    "DeepSeek-V3": {"name": "deepseek", "capabilities": ["text", "tools"]},
    "Qwen 2.5 72B": {"name": "qwen", "capabilities": ["text", "vision", "tools"]},
    "Kimi K2.5": {"name": "kimi", "capabilities": ["text", "vision", "tools"]},
}

# Image generation models
IMAGE_MODELS = {
    "flux": "Flux Schnell",
    "flux-pro": "Flux Pro",
    "turbo": "Turbo",
}

# Text-to-speech voices
VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# Aspect ratio presets
ASPECT_RATIOS = {
    "1:1": (1024, 1024),
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "4:3": (1024, 768),
    "3:4": (768, 1024),
    "21:9": (1024, 440),
}

# System prompt
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

# Guarded system prompt (same as main prompt - guardrails are handled at application level)
SAFE_SYSTEM_PROMPT = SYSTEM_PROMPT
