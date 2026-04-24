"""
Configuration settings for DenLab Chat.
Single source of truth - all other files import from here.
"""

import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# ============================================================================
# APP CONFIGURATION
# ============================================================================

@dataclass
class AppConfig:
    """Main application configuration."""
    title: str = "DenLab Chat"
    icon: str = "🧪"
    version: str = "7.0.0"
    description: str = "Advanced AI Assistant with Memory, Cache, Swarm Agents & GitHub Integration"
    
    # Layout
    layout: str = "wide"
    sidebar_state: str = "expanded"
    
    # Limits
    max_history: int = 100
    max_file_size_mb: int = 10
    max_agent_steps: int = 25
    max_parallel_agents: int = 4
    
    # Features
    enable_streaming: bool = True
    enable_vision: bool = True
    enable_agent_mode: bool = True
    enable_swarm_mode: bool = True
    enable_pwa: bool = True
    enable_analytics: bool = True


# ============================================================================
# API ENDPOINTS
# ============================================================================

class APIEndpoints:
    """Centralized API endpoint configuration."""
    
    # Primary API (Pollinations.ai)
    TEXT_API: str = "https://text.pollinations.ai/openai"
    IMAGE_API: str = "https://image.pollinations.ai/prompt"
    AUDIO_API: str = "https://gen.pollinations.ai/audio"
    
    # Fallback APIs
    FALLBACK_TEXT_API: str = "https://text.pollinations.ai/openai"  # Same provider with different model
    FALLBACK_IMAGE_API: str = "https://image.pollinations.ai/prompt"
    
    # External services
    DUCKDUCKGO_API: str = "https://api.duckduckgo.com/"
    DUCKDUCKGO_FALLBACK: str = "https://ddg-api.herokuapp.com/search"
    GITHUB_API: str = "https://api.github.com"
    
    # Timeouts (seconds)
    TIMEOUT_SHORT: int = 10
    TIMEOUT_MEDIUM: int = 15
    TIMEOUT_LONG: int = 30
    TIMEOUT_EXTRA_LONG: int = 60
    
    # Headers
    @staticmethod
    def get_headers() -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "User-Agent": "DenLab/7.0"
        }
    
    @staticmethod
    def get_github_headers() -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DenLab/7.0"
        }


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

class Models:
    """Model registry - single source of truth for all AI models."""
    
    # Model mapping: Display Name -> API Model Name
    MODEL_MAP: Dict[str, str] = {
        "GPT-4o": "openai",
        "GPT-4o mini": "openai-mini",
        "Claude 3.5 Sonnet": "claude",
        "Gemini 2.0 Flash": "gemini",
        "Llama 3.3 70B": "llama",
        "Mistral Large": "mistral",
        "DeepSeek V3": "deepseek",
        "Qwen 2.5 72B": "qwen",
    }
    
    # Model capabilities mapping
    MODEL_CAPABILITIES: Dict[str, List[str]] = {
        "openai": ["text", "vision", "tools"],
        "openai-mini": ["text", "vision", "tools"],
        "claude": ["text", "vision", "tools"],
        "gemini": ["text", "vision", "tools"],
        "llama": ["text", "tools"],
        "mistral": ["text", "tools"],
        "deepseek": ["text", "tools"],
        "qwen": ["text", "vision", "tools"],
    }
    
    # Image generation models
    IMAGE_MODELS: Dict[str, str] = {
        "flux": "Flux Schnell",
        "flux-pro": "Flux Pro",
        "turbo": "Turbo",
    }
    
    # Default model
    DEFAULT_MODEL: str = "openai"
    DEFAULT_IMAGE_MODEL: str = "flux"
    
    @classmethod
    def get_display_names(cls) -> List[str]:
        """Get list of display names for UI."""
        return list(cls.MODEL_MAP.keys())
    
    @classmethod
    def get_api_name(cls, display_name: str) -> str:
        """Convert display name to API model name."""
        return cls.MODEL_MAP.get(display_name, cls.DEFAULT_MODEL)
    
    @classmethod
    def get_capabilities(cls, model_name: str) -> List[str]:
        """Get capabilities for a model."""
        return cls.MODEL_CAPABILITIES.get(model_name, ["text"])
    
    @classmethod
    def supports_vision(cls, model_name: str) -> bool:
        """Check if model supports vision."""
        return "vision" in cls.get_capabilities(model_name)
    
    @classmethod
    def supports_tools(cls, model_name: str) -> bool:
        """Check if model supports tools."""
        return "tools" in cls.get_capabilities(model_name)


# ============================================================================
# ASPECT RATIOS FOR IMAGE GENERATION
# ============================================================================

class AspectRatios:
    """Aspect ratio presets for image generation."""
    
    RATIOS: Dict[str, Tuple[int, int]] = {
        "1:1": (1024, 1024),
        "16:9": (1024, 576),
        "9:16": (576, 1024),
        "4:3": (1024, 768),
        "3:4": (768, 1024),
        "21:9": (1024, 440),
    }
    
    DEFAULT: str = "1:1"
    
    @classmethod
    def get_dimensions(cls, ratio: str) -> Tuple[int, int]:
        """Get width, height for a ratio."""
        return cls.RATIOS.get(ratio, cls.RATIOS[cls.DEFAULT])
    
    @classmethod
    def get_all_ratios(cls) -> List[str]:
        """Get all available ratios."""
        return list(cls.RATIOS.keys())


# ============================================================================
# TEXT-TO-SPEECH VOICES
# ============================================================================

class TTSVoices:
    """Available TTS voices."""
    
    VOICES: List[str] = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    DEFAULT: str = "nova"
    
    @classmethod
    def get_voices(cls) -> List[str]:
        return cls.VOICES


# ============================================================================
# SYSTEM PROMPTS (Clean - No Ads, No Brand Mentions)
# ============================================================================

class SystemPrompts:
    """Centralized system prompts - clean, no external branding."""
    
    # Main assistant prompt
    MAIN_PROMPT: str = """You are DenLab, an advanced AI research assistant with tool-use capabilities and persistent memory.

Guidelines:
1. Be helpful, accurate, and thorough in your responses
2. Use available tools when they would improve the answer
3. Remember previous conversations and reference them when relevant
4. Provide clear explanations with examples when helpful
5. Break down complex tasks into steps
6. Write clean, well-documented code when requested
7. Research topics thoroughly using search when current information is needed
8. Respect user autonomy and provide factual information

Available tools:
- web_search: Search the live web for current information
- github_get_files: List all files in a GitHub repository
- deep_research: Multi-hop research across sources
- execute_code: Run Python code in sandboxed environment
- fetch_url: Scrape specific web pages
- read_file: Read uploaded file contents
- write_file: Save generated content to files
- analyze_image: Analyze and describe uploaded images

You have memory of past conversations. Use this to provide personalized, context-aware responses."""
    
    # Master agent prompt for swarm mode
    MASTER_AGENT_PROMPT: str = """You are the DenLab Master Agent. Your role is to:
1. Analyze the user's task and break it into sub-tasks
2. Delegate each sub-task to specialized agents
3. Collect results from all agents
4. Synthesize them into a coherent final response

Available sub-agents:
- Researcher: Best for web search, fact-finding, and information gathering
- Coder: Best for writing, executing, and debugging code
- Analyst: Best for data analysis, comparisons, and evaluations
- Writer: Best for composing final responses, summaries, and reports

When given a task, respond with a JSON plan like:
{"subtasks": [{"role": "researcher", "task": "..."}, {"role": "writer", "task": "..."}]}

Then after receiving results, synthesize the final answer."""
    
    # Sub-agent prompts
    SUB_AGENT_PROMPTS: Dict[str, str] = {
        "researcher": "You are a Research Agent. Find accurate, current information. Be thorough and cite sources.",
        "coder": "You are a Code Agent. Write clean, working code. Explain your approach and show output.",
        "analyst": "You are an Analyst Agent. Compare, evaluate, and draw insights from data. Be objective.",
        "writer": "You are a Writer Agent. Synthesize information into clear, well-structured responses."
    }
    
    # Code generation prompt
    CODE_PROMPT: str = "You are an expert Python programmer. Write clean, well-documented, production-ready code. Return ONLY the code inside a markdown code block."
    
    # Code analysis prompt
    ANALYSIS_PROMPT: str = """You are a senior code reviewer and software architect. Provide thorough technical analysis covering:
1. Purpose - What this file does
2. Key Components - Main functions, classes, or sections
3. Dependencies - External libraries or modules used
4. Code Quality - Structure, patterns, best practices
5. Issues/Suggestions - Potential bugs, improvements, security concerns
6. Documentation - Docstring and comment quality"""
    
    # Synthesis prompt for swarm
    SYNTHESIS_PROMPT: str = """You are a synthesis expert. Combine multiple agent results into a clear, coherent response that directly addresses the original task."""
    
    @classmethod
    def get_sub_agent_prompt(cls, agent_type: str) -> str:
        """Get prompt for a specific sub-agent type."""
        return cls.SUB_AGENT_PROMPTS.get(agent_type, cls.SUB_AGENT_PROMPTS["writer"])


# ============================================================================
# DEVELOPER CONFIGURATION
# ============================================================================

class DeveloperConfig:
    """Developer account configuration - hardcoded for creator access."""
    
    USERNAME: str = "dennis"
    PASSWORD: str = "yessyess"
    DISPLAY_NAME: str = "Dennis"
    
    @classmethod
    def is_developer(cls, username: str, password: str = None) -> bool:
        """Check if credentials match developer account."""
        if password is not None:
            return username.lower() == cls.USERNAME and password == cls.PASSWORD
        return username.lower() == cls.USERNAME


# ============================================================================
# CACHE & MEMORY CONFIGURATION
# ============================================================================

class CacheConfig:
    """Response cache configuration."""
    
    ENABLED: bool = True
    MAX_SIZE: int = 100
    TTL_HOURS: int = 24
    CACHE_DIR: str = "data/cache"


class MemoryConfig:
    """Memory system configuration."""
    
    ENABLED: bool = True
    MAX_WORKING_MESSAGES: int = 15
    MAX_EPISODIC_ENTRIES: int = 50
    MEMORY_DIR: str = "data/memories"


# ============================================================================
# FILE UPLOAD CONFIGURATION
# ============================================================================

class FileUploadConfig:
    """File upload configuration."""
    
    ALLOWED_EXTENSIONS: List[str] = [
        "txt", "py", "js", "ts", "html", "css", "json", "md", "csv", "xml", "yaml", "yml",
        "sh", "bash", "c", "cpp", "h", "hpp", "java", "kt", "swift", "rs", "go", "rb", "php", "sql",
        "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "pdf"
    ]
    
    MAX_SIZE_MB: int = 10
    
    @classmethod
    def is_allowed(cls, filename: str) -> bool:
        """Check if file extension is allowed."""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        return ext in cls.ALLOWED_EXTENSIONS


# ============================================================================
# CONSTANTS
# ============================================================================

class Constants:
    """General constants."""
    
    # Tool names
    TOOLS: Dict[str, str] = {
        "WEB_SEARCH": "web_search",
        "GITHUB_GET_FILES": "github_get_files",
        "DEEP_RESEARCH": "deep_research",
        "EXECUTE_CODE": "execute_code",
        "FETCH_URL": "fetch_url",
        "READ_FILE": "read_file",
        "WRITE_FILE": "write_file",
        "ANALYZE_IMAGE": "analyze_image",
        "GENERATE_IMAGE": "generate_image",
        "GENERATE_AUDIO": "generate_audio",
    }
    
    # Command prefixes
    COMMANDS: Dict[str, str] = {
        "IMAGINE": "/imagine",
        "RESEARCH": "/research",
        "CODE": "/code",
        "ANALYZE": "/analyze",
        "AUDIO": "/audio",
        "AGENT": "/agent",
    }
    
    # Agent types for swarm
    AGENT_TYPES: List[str] = ["researcher", "coder", "analyst", "writer"]
    
    # Agent icons
    AGENT_ICONS: Dict[str, str] = {
        "researcher": "🔍",
        "coder": "💻",
        "analyst": "📊",
        "writer": "✍️",
        "master": "👑",
    }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_config = None

def get_config() -> AppConfig:
    """Get singleton AppConfig instance."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


# Convenience exports for cleaner imports elsewhere
MODELS = Models.MODEL_MAP
MODEL_NAMES = Models.get_display_names()
SYSTEM_PROMPT = SystemPrompts.MAIN_PROMPT
API_URL = APIEndpoints.TEXT_API
IMAGE_API_URL = APIEndpoints.IMAGE_API
AUDIO_API_URL = APIEndpoints.AUDIO_API