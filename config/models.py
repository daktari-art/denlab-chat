"""Data models."""
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    CODE = "code"
    FILE = "file"

class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = datetime.now()
    metadata: Dict = {}

class Session(BaseModel):
    id: str
    name: str
    messages: List[ChatMessage] = []
    model: str = "openai"
    temperature: float = 0.7
    created_at: datetime = datetime.now()
