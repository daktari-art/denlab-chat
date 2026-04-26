"""
Chat database for persistent conversation history.
Uses JSON file storage per user.
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

# Import from centralized config
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Constants


# ============================================================================
# CONSTANTS
# ============================================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ============================================================================
# ID GENERATION
# ============================================================================

def generate_id() -> str:
    """Generate a unique ID for conversations and messages."""
    return uuid.uuid4().hex[:12]


# ============================================================================
# CHAT DATABASE
# ============================================================================

class ChatDatabase:
    """Manage conversations and messages for a user."""
    
    def __init__(self, username: str):
        self.username = username.lower().strip()
        self.file_path = os.path.join(DATA_DIR, f"chats_{self.username}.json")
        os.makedirs(DATA_DIR, exist_ok=True)
        self._data = self._load()
    
    def _load(self) -> Dict:
        """Load chat data from JSON file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "username": self.username,
            "conversations": [],
            "version": "2.0"
        }
    
    def _save(self):
        """Save chat data to JSON file."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving chat data for {self.username}: {e}")
    
    # ========================================================================
    # Conversation Management
    # ========================================================================
    
    def create_conversation(self, title: str = "New Chat", model: str = "openai") -> str:
        """Create a new conversation and return its ID."""
        conv_id = generate_id()
        conversation = {
            "id": conv_id,
            "title": title,
            "model": model,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        self._data["conversations"].append(conversation)
        self._save()
        return conv_id
    
    def get_conversations(self) -> List[Dict]:
        """Get all conversations, sorted by most recent first."""
        convs = self._data.get("conversations", [])
        convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return convs
    
    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Get a specific conversation by ID."""
        for conv in self._data.get("conversations", []):
            if conv["id"] == conv_id:
                return conv
        return None
    
    def update_conversation(self, conv_id: str, updates: Dict) -> bool:
        """Update a conversation with new data."""
        conv = self.get_conversation(conv_id)
        if not conv:
            return False
        
        for key, value in updates.items():
            if key in conv:
                conv[key] = value
        
        conv["updated_at"] = datetime.now().isoformat()
        self._save()
        return True
    
    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation."""
        convs = self._data.get("conversations", [])
        for i, conv in enumerate(convs):
            if conv["id"] == conv_id:
                convs.pop(i)
                self._save()
                return True
        return False
    
    def clear_all_conversations(self) -> int:
        """Delete all conversations for this user."""
        count = len(self._data.get("conversations", []))
        self._data["conversations"] = []
        self._save()
        return count
    
    # ========================================================================
    # Message Management
    # ========================================================================
    
    def add_message(self, conv_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """Add a message to a conversation."""
        conv = self.get_conversation(conv_id)
        if not conv:
            return False
        
        message = {
            "id": generate_id(),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        conv["messages"].append(message)
        conv["updated_at"] = datetime.now().isoformat()
        
        # Auto-update title from first user message
        if conv["title"] == "New Chat" and role == "user":
            new_title = content[:40] + "..." if len(content) > 40 else content
            conv["title"] = new_title
        
        self._save()
        return True
    
    def get_messages(self, conv_id: str) -> List[Dict]:
        """Get all messages in a conversation."""
        conv = self.get_conversation(conv_id)
        if conv:
            return conv.get("messages", [])
        return []
    
    def get_last_message(self, conv_id: str) -> Optional[Dict]:
        """Get the last message in a conversation."""
        messages = self.get_messages(conv_id)
        return messages[-1] if messages else None
    
    def clear_messages(self, conv_id: str) -> bool:
        """Clear all messages in a conversation."""
        conv = self.get_conversation(conv_id)
        if conv:
            conv["messages"] = []
            conv["updated_at"] = datetime.now().isoformat()
            self._save()
            return True
        return False
    
    def delete_message(self, conv_id: str, message_id: str) -> bool:
        """Delete a specific message by ID."""
        conv = self.get_conversation(conv_id)
        if not conv:
            return False
        
        messages = conv.get("messages", [])
        for i, msg in enumerate(messages):
            if msg.get("id") == message_id:
                messages.pop(i)
                conv["updated_at"] = datetime.now().isoformat()
                self._save()
                return True
        return False
    
    # ========================================================================
    # Model Management
    # ========================================================================
    
    def update_model(self, conv_id: str, model: str) -> bool:
        """Update the model for a conversation."""
        return self.update_conversation(conv_id, {"model": model})
    
    def get_conversation_model(self, conv_id: str) -> Optional[str]:
        """Get the model used for a conversation."""
        conv = self.get_conversation(conv_id)
        return conv.get("model") if conv else None
    
    # ========================================================================
    # Export & Utilities
    # ========================================================================
    
    def export_conversation(self, conv_id: str, format: str = "markdown") -> str:
        """
        Export conversation as markdown or JSON.
        
        Args:
            conv_id: Conversation ID
            format: "markdown" or "json"
        
        Returns:
            Exported string
        """
        conv = self.get_conversation(conv_id)
        if not conv:
            return ""
        
        if format == "json":
            return json.dumps(conv, indent=2, ensure_ascii=False)
        
        # Markdown format (default)
        lines = [f"# {conv.get('title', 'Chat')}\n"]
        lines.append(f"**Model:** {conv.get('model', 'unknown')}\n")
        lines.append(f"**Date:** {conv.get('created_at', 'unknown')}\n")
        lines.append(f"**Exported:** {datetime.now().isoformat()}\n")
        lines.append("\n---\n\n")
        
        for msg in conv.get("messages", []):
            role = msg["role"].upper()
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")[:16]  # YYYY-MM-DD HH:MM
            
            lines.append(f"### {role} [{timestamp}]\n")
            lines.append(f"{content}\n\n")
        
        return "\n".join(lines)
    
    def get_or_create_default(self, model: str = "openai") -> str:
        """
        Get the most recent conversation or create a new one.
        
        Returns:
            Conversation ID
        """
        convs = self.get_conversations()
        if convs:
            return convs[0]["id"]
        return self.create_conversation(model=model)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics for this user."""
        convs = self.get_conversations()
        total_messages = sum(len(conv.get("messages", [])) for conv in convs)
        
        return {
            "username": self.username,
            "conversation_count": len(convs),
            "total_messages": total_messages,
            "oldest_conversation": convs[-1].get("created_at") if convs else None,
            "newest_conversation": convs[0].get("created_at") if convs else None
        }


# ============================================================================
# DATABASE MANAGER (Singleton per user)
# ============================================================================

_db_instances: Dict[str, ChatDatabase] = {}


def get_chat_db(username: str) -> ChatDatabase:
    """Get or create a ChatDatabase for a user."""
    key = username.lower().strip()
    if key not in _db_instances:
        _db_instances[key] = ChatDatabase(key)
    return _db_instances[key]


def clear_chat_db_cache():
    """Clear all cached database instances (useful for testing)."""
    global _db_instances
    _db_instances = {}


def delete_user_chat_data(username: str) -> bool:
    """Permanently delete all chat data for a user."""
    username = username.lower().strip()
    db = ChatDatabase(username)  # This loads the data
    
    # Clear from cache if present
    if username in _db_instances:
        del _db_instances[username]
    
    # Delete the file
    file_path = os.path.join(DATA_DIR, f"chats_{username}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    
    return False


# ============================================================================
# BACKWARD COMPATIBILITY ALIAS
# ============================================================================

ConversationDB = ChatDatabase
