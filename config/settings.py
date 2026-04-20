"""Central configuration for DenLab."""
import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class AppConfig:
    TITLE: str = "DenLab"
    ICON: str = "🧪"
    VERSION: str = "3.0.0"
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

CONFIG = AppConfig()

MODELS = {
    "GPT-4o mini": "openai",
    "GPT-4o": "openai-large",
    "Llama 3.3 70B": "llama",
    "DeepSeek-V3": "deepseek",
    "Gemini 2.0 Flash": "gemini",
    "Qwen Coder 32B": "qwen-coder",
    "Kimi K2.5": "kimi",
}

IMAGE_MODELS = {
    "flux": "Flux Schnell",
    "gptimage": "GPT Image 1 Mini",
    "gptimage-large": "GPT Image 1.5",
}

VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

SYSTEM_PROMPT = """You are DenLab, a professional AI research assistant. 
You can generate images with /imagine, analyze files, and run in Agent mode for autonomous tasks.
Be concise, accurate, and helpful."""
