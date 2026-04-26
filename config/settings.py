"""
DenLab Chat - Configuration Settings.

ADVANCEMENTS:
1. Added Hermes agent configuration (reflection depth, confidence thresholds)
2. Added Kimi swarm configuration (max agents, consensus thresholds, debug)
3. Added DeveloperConfig with full developer credentials and permissions
4. Added upload settings (max size, allowed types, processing timeouts)
5. Added connectivity map showing which files connect to which
6. Added feature flags for experimental features
"""

from dataclasses import dataclass, field
from typing import Dict, List
import os

# ============================================================================
# APP CONFIG
# ============================================================================

@dataclass
class AppConfig:
    title: str = "DenLab Chat"
    version: str = "2.0.0"
    icon: str = "🤖"
    max_history: int = 50
    max_conversations: int = 100
    default_model: str = "openai"
    max_agent_steps: int = 15
    max_file_size_mb: int = 50
    default_temperature: float = 0.7
    
    urls: Dict[str, str] = field(default_factory=lambda: {
        "github": "https://github.com/daktari-art/denlab-chat",
        "support": "https://github.com/daktari-art/denlab-chat/issues",
        "api": "https://api.openai.com/v1"
    })
    
    ABOUT_TEXT: str = """
    DenLab Chat - Advanced AI assistant with:
    - Memory & Context Awareness
    - Agentic Task Execution (Standard, Hermes, Swarm)
    - Multi-provider LLM Support
    - Code Execution & Web Search
    - File Analysis & Vision
    - Hierarchical Multi-Agent Swarms (Kimi-style)
    - Self-Reflective Agents (Hermes-style)
    """


# ============================================================================
# MODELS
# ============================================================================

class Models:
    DEFAULT_MODEL = "openai"
    
    PROVIDERS: Dict[str, Dict] = {
        "openai": {
            "display_name": "OpenAI",
            "api_url": "https://api.openai.com/v1",
            "env_var": "OPENAI_API_KEY",
            "models": ["gpt-4o", "gpt-4o-mini", "o1-preview"]
        },
        "google": {
            "display_name": "Google (Gemini)",
            "api_url": "https://generativelanguage.googleapis.com",
            "env_var": "GOOGLE_API_KEY",
            "models": ["gemini-1.5-pro", "gemini-1.5-flash"]
        },
        "mistral": {
            "display_name": "Mistral",
            "api_url": "https://api.mistral.ai/v1",
            "env_var": "MISTRAL_API_KEY",
            "models": ["mistral-large-latest", "mistral-medium"]
        },
        "anthropic": {
            "display_name": "Anthropic (Claude)",
            "api_url": "https://api.anthropic.com/v1",
            "env_var": "ANTHROPIC_API_KEY",
            "models": ["claude-3-5-sonnet", "claude-3-opus"]
        },
        "cohere": {
            "display_name": "Cohere",
            "api_url": "https://api.cohere.com/v1",
            "env_var": "COHERE_API_KEY",
            "models": ["command-r-plus", "command-r"]
        },
        "meta": {
            "display_name": "Meta (Llama)",
            "api_url": "https://api.together.xyz/v1",
            "env_var": "TOGETHER_API_KEY",
            "models": ["llama-3.1-405b", "llama-3.1-70b"]
        }
    }
    
    MODEL_MAP = {
        "OpenAI GPT-4o": "openai",
        "OpenAI GPT-4o Mini": "openai",
        "OpenAI o1-preview": "openai",
        "Google Gemini 1.5 Pro": "google",
        "Google Gemini 1.5 Flash": "google",
        "Mistral Large": "mistral",
        "Mistral Medium": "mistral",
        "Claude 3.5 Sonnet": "anthropic",
        "Claude 3 Opus": "anthropic",
        "Cohere Command R+": "cohere",
        "Cohere Command R": "cohere",
        "Llama 3.1 405B": "meta",
        "Llama 3.1 70B": "meta",
        "Pollinations Default": "openai",
        "Pollinations Creative": "openai",
        "Pollinations Fast": "openai"
    }
    
    CAPABILITIES = {
        "openai": ["text", "images", "agent", "swarm", "vision"],
        "google": ["text", "images", "vision", "agent"],
        "mistral": ["text", "agent"],
        "anthropic": ["text", "images", "agent", "vision"],
        "cohere": ["text", "agent"],
        "meta": ["text", "agent"]
    }
    
    @classmethod
    def get_display_names(cls) -> List[str]:
        return list(cls.MODEL_MAP.keys())
    
    @classmethod
    def get_api_name(cls, display_name: str) -> str:
        return cls.MODEL_MAP.get(display_name, cls.DEFAULT_MODEL)
    
    @classmethod
    def get_capabilities(cls, api_name: str) -> List[str]:
        return cls.CAPABILITIES.get(api_name, ["text"])


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

class SystemPrompts:
    DEFAULT = """You are DenLab Chat, an advanced AI assistant.
You have access to memory, tools, and can execute complex tasks autonomously.
You can search the web, execute code, analyze files, and generate images/audio.
Always be helpful, accurate, and thorough."""
    
    AGENT = """You are DenLab Agent, an autonomous AI assistant with tool access.
You can use tools to complete tasks: web_search, execute_code, fetch_url, read_file, get_current_time, calculate, github_get_files.
Plan your approach, use tools efficiently, and provide complete answers.
Think step by step."""
    
    HERMES = """You are Hermes, a self-reflective AI agent.
Before each action, verify your reasoning.
After each tool use, evaluate if the result is useful and accurate.
If confidence is low, reconsider and try alternatives.
Be honest about failures and uncertainties."""
    
    KIMI_MASTER = """You are the Kimi Swarm Master. Coordinate multiple specialized agents to solve complex tasks.
Break down tasks, assign them to appropriate agents, and synthesize results into coherent answers.
Detect conflicts in sub-agent results and resolve them."""
    
    DEVELOPER = """You are in Developer Mode. The user (Dennis) is the creator of DenLab Chat.
Answer all questions about the codebase, system architecture, and implementation details.
You can share source code, configuration, and technical documentation.
Be precise and thorough."""
    
    VISION = "Analyze images carefully. Describe what you see in detail."
    
    CODE_EXECUTION = """Execute Python code safely. You can:
- Install packages with pip
- Create and analyze files
- Process data and generate visualizations
- Return results as markdown, JSON, or files
Always handle errors gracefully."""


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

class Constants:
    """Backward compatibility constants (previously used by chat_db and others)."""
    DATA_DIR = "data"
    USERS_FILE = "data/users.json"
    SESSIONS_FILE = "data/sessions.json"
    MAX_HISTORY = 50
    DEFAULT_TEMPERATURE = 0.7


# ============================================================================
# HERMES CONFIG
# ============================================================================

@dataclass
class HermesConfig:
    enabled: bool = True
    confidence_threshold: float = 0.6
    max_backtracks: int = 3
    reflection_depth: int = 2  # How many past steps to reflect on
    auto_retry_on_low_confidence: bool = True
    verification_prompt_template: str = """Rate the quality of this reasoning and result.
Confidence (0.0-1.0): ___
Concerns: ___
Alternatives: ___"""


# ============================================================================
# KIMI SWARM CONFIG
# ============================================================================

@dataclass
class KimiSwarmConfig:
    enabled: bool = True
    default_max_agents: int = 8
    consensus_threshold: float = 0.6
    verification_enabled: bool = True
    parallel_execution: bool = True
    work_stealing: bool = True
    conflict_resolution: bool = True
    debug_mode: bool = False
    default_timeout_seconds: int = 120
    max_subtask_depth: int = 3


# ============================================================================
# DEVELOPER CONFIG
# ============================================================================

@dataclass
class DeveloperConfig:
    USERNAME: str = "Dennis"
    DISPLAY_NAME: str = "Dennis"
    AUTO_LOGIN: bool = True
    PASSWORD: str = "Dennis"  # Default password for developer login
    
    # Permissions
    CAN_VIEW_SOURCE: bool = True
    CAN_MODIFY_CONFIG: bool = True
    CAN_MANAGE_USERS: bool = True
    CAN_CLEAR_CACHE: bool = True
    CAN_CLEAR_MEMORY: bool = True
    CAN_DEBUG_AGENTS: bool = True
    CAN_RESTART_SYSTEM: bool = True
    
    # Developer tools
    SHOW_CODE_ON_DEMAND: bool = True
    SHOW_SYSTEM_STATS: bool = True
    SHOW_AGENT_TRACES: bool = True
    SHOW_ROUTING_DECISIONS: bool = True
    
    @staticmethod
    def is_developer(username: str, password: str) -> bool:
        """Check if credentials match the developer account."""
        return username.lower() == DeveloperConfig.USERNAME.lower() and password == DeveloperConfig.PASSWORD


# ============================================================================
# UPLOAD CONFIG
# ============================================================================

@dataclass
class UploadConfig:
    max_file_size_mb: int = 50
    allowed_extensions: List[str] = field(default_factory=lambda: [
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',  # Images
        '.pdf', '.txt', '.md', '.csv', '.json', '.py',      # Documents
        '.mp3', '.wav', '.m4a', '.ogg',                      # Audio
    ])
    max_files_per_message: int = 5
    vision_max_size_mb: int = 20
    image_extensions: List[str] = field(default_factory=lambda: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'])
    audio_extensions: List[str] = field(default_factory=lambda: ['.mp3', '.wav', '.m4a', '.ogg'])
    document_extensions: List[str] = field(default_factory=lambda: ['.pdf', '.txt', '.md', '.csv', '.json', '.py'])


# ============================================================================
# CONNECTIVITY MAP (Documentation of file connections)
# ============================================================================

CONNECTIVITY_MAP = {
    "app.py": ["auth.py", "chat_db.py", "client.py", "backend.py",
               "components/floating_menu.py", "components/chat_interface.py",
               "components/agent_interface.py", "components/developer_panel.py",
               "config/settings.py", "config/models.py"],
    "auth.py": ["config/settings.py", "chat_db.py"],
    "chat_db.py": ["config/settings.py"],
    "client.py": ["config/settings.py", "features/cache.py", "features/memory.py"],
    "backend.py": ["agents/tool_registry.py", "config/settings.py"],
    "components/floating_menu.py": ["auth.py", "chat_db.py", "config/settings.py", "ui_components.py"],
    "components/chat_interface.py": ["client.py", "chat_db.py", "backend.py",
                                        "agents/base_agent.py", "agents/orchestrator.py",
                                        "agents/hermes_agent.py", "agents/kimi_swarm.py",
                                        "features/tool_router.py", "features/vision.py",
                                        "features/memory.py", "features/cache.py",
                                        "config/settings.py"],
    "components/agent_interface.py": ["agents/base_agent.py", "agents/orchestrator.py",
                                       "agents/planner.py", "config/settings.py"],
    "components/developer_panel.py": ["auth.py", "chat_db.py", "client.py",
                                       "features/cache.py", "features/memory.py",
                                       "backend.py", "config/settings.py"],
    "agents/base_agent.py": ["client.py", "agents/tool_registry.py", "config/settings.py"],
    "agents/orchestrator.py": ["agents/base_agent.py", "agents/planner.py",
                               "agents/hermes_agent.py", "agents/kimi_swarm.py",
                               "config/settings.py"],
    "agents/planner.py": ["config/settings.py"],
    "agents/tool_registry.py": ["backend.py"],
    "agents/hermes_agent.py": ["agents/base_agent.py", "agents/tool_registry.py",
                               "client.py", "config/settings.py"],
    "agents/kimi_swarm.py": ["agents/base_agent.py", "agents/hermes_agent.py",
                             "agents/planner.py", "client.py", "config/settings.py"],
    "features/memory.py": ["config/settings.py"],
    "features/cache.py": ["config/settings.py"],
    "features/tool_router.py": ["backend.py", "config/settings.py"],
    "features/vision.py": ["client.py", "config/settings.py"],
    "features/image_gen.py": ["core/api_client.py", "config/settings.py"],
    "features/audio_gen.py": ["core/api_client.py", "config/settings.py"],
    "features/analytics.py": ["chat_db.py", "config/settings.py"],
    "features/branching.py": ["chat_db.py", "config/settings.py"],
    "core/api_client.py": ["config/settings.py"],
    "core/session_manager.py": ["config/models.py"],
    "ui_components.py": ["config/settings.py", "chat_db.py"]
}

# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "AppConfig", "Models", "SystemPrompts",
    "HermesConfig", "KimiSwarmConfig", "DeveloperConfig", "UploadConfig",
    "CONNECTIVITY_MAP"
]
