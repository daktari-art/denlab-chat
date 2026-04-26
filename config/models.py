"""
Config Models - Pydantic models for configuration.

ADVANCEMENTS:
1. Added DeveloperSession model for developer-specific session data
2. Added AgentTraceRecord for persistent agent trace logging
3. Added UploadFile model for file upload metadata
4. Added SystemHealthRecord for health check history
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Enum
from datetime import datetime


class UserSession(BaseModel):
    """User session data."""
    username: str
    token: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_developer: bool = False


class DeveloperSession(BaseModel):
    """Developer session with elevated permissions."""
    username: str = "Dennis"
    display_name: str = "Dennis"
    token: str = "dev_token"
    permissions: List[str] = Field(default_factory=lambda: [
        "view_source", "modify_config", "manage_users", "clear_cache",
        "clear_memory", "debug_agents", "restart_system"
    ])
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_command: Optional[str] = None
    commands_executed: int = 0


class ConversationConfig(BaseModel):
    """Per-conversation configuration."""
    conversation_id: str
    model: str = "openai"
    temperature: float = 0.7
    agent_mode: bool = False
    swarm_mode: bool = False
    hermes_mode: bool = False
    memory_enabled: bool = True
    cache_enabled: bool = True
    max_steps: int = 15
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AgentTraceRecord(BaseModel):
    """Persistent record of agent execution trace."""
    trace_id: str
    conversation_id: str
    agent_name: str
    task: str
    steps: int
    reflections: int = 0
    backtracks: int = 0
    avg_confidence: float = 0.0
    duration_ms: float = 0.0
    status: str = "success"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class UploadFile(BaseModel):
    """Uploaded file metadata."""
    filename: str
    size_bytes: int
    content_type: str
    extension: str
    processing_status: str = "pending"  # pending, processed, failed
    extracted_text: Optional[str] = None
    uploaded_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SystemHealthRecord(BaseModel):
    """Health check result record."""
    check_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_modules: int = 0
    healthy_modules: int = 0
    failed_modules: List[Dict[str, str]] = Field(default_factory=list)
    score: float = 0.0  # percentage


class CacheStats(BaseModel):
    """Cache statistics snapshot."""
    size: int
    hits: int
    misses: int
    hit_rate: float
    avg_entry_size: float
    oldest_entry_age_seconds: float
    memory_usage_mb: float


class MemoryStats(BaseModel):
    """Memory system statistics."""
    user_count: int
    total_interactions: int
    avg_interactions_per_user: float
    total_semantic_facts: int
    total_episodic_summaries: int




# ============================================================================
# SESSION MODELS (for session_manager.py compatibility)
# ============================================================================

class Session(BaseModel):
    """Chat session data."""
    id: str
    name: str = "New Session"
    messages: List[Dict] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MessageRole(str, Enum):
    """Message role enumeration."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """Individual chat message."""
    role: MessageRole
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[Dict[str, Any]] = None

# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "UserSession", "DeveloperSession", "ConversationConfig",
    "AgentTraceRecord", "UploadFile", "SystemHealthRecord",
    "CacheStats", "MemoryStats"
]
