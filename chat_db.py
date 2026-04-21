"""Chat database for persistent conversation history.
Uses JSON file storage per user.
"""
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def generate_id() -> str:
    """Generate a unique ID for conversations and messages."""
    return uuid.uuid4().hex[:12]

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
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "username": self.username,
            "conversations": [],
            "version": "1.0"
        }
    
    def _save(self):
        """Save chat data to JSON file."""
        with open(self.file_path, 'w') as f:
            json.dump(self._data, f, indent=2)
    
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
    
    def add_message(self, conv_id: str, role: str, content: str, metadata: Optional[Dict] = None):
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
            conv["title"] = content[:40] + "..." if len(content) > 40 else content
        
        self._save()
        return True
    
    def update_conversation_title(self, conv_id: str, title: str):
        """Update conversation title."""
        conv = self.get_conversation(conv_id)
        if conv:
            conv["title"] = title
            conv["updated_at"] = datetime.now().isoformat()
            self._save()
    
    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation."""
        convs = self._data.get("conversations", [])
        for i, conv in enumerate(convs):
            if conv["id"] == conv_id:
                convs.pop(i)
                self._save()
                return True
        return False
    
    def get_messages(self, conv_id: str) -> List[Dict]:
        """Get all messages in a conversation."""
        conv = self.get_conversation(conv_id)
        if conv:
            return conv.get("messages", [])
        return []
    
    def clear_messages(self, conv_id: str):
        """Clear all messages in a conversation."""
        conv = self.get_conversation(conv_id)
        if conv:
            conv["messages"] = []
            conv["updated_at"] = datetime.now().isoformat()
            self._save()
    
    def update_model(self, conv_id: str, model: str):
        """Update the model for a conversation."""
        conv = self.get_conversation(conv_id)
        if conv:
            conv["model"] = model
            self._save()
    
    def export_conversation(self, conv_id: str) -> str:
        """Export conversation as markdown string."""
        conv = self.get_conversation(conv_id)
        if not conv:
            return ""
        
        lines = [f"# {conv.get('title', 'Chat')}\n"]
        lines.append(f"Model: {conv.get('model', 'unknown')}\n")
        lines.append(f"Date: {conv.get('created_at', 'unknown')}\n\n")
        lines.append("---\n\n")
        
        for msg in conv.get("messages", []):
            role = msg["role"].upper()
            content = msg.get("content", "")
            lines.append(f"**{role}**: {content}\n\n")
        
        return "\n".join(lines)
    
    def get_or_create_default(self, model: str = "openai") -> str:
        """Get the most recent conversation or create a new one."""
        convs = self.get_conversations()
        if convs:
            return convs[0]["id"]
        return self.create_conversation(model=model)


# Cache instances
_db_instances: Dict[str, ChatDatabase] = {}

def get_chat_db(username: str) -> ChatDatabase:
    """Get or create a ChatDatabase for a user."""
    key = username.lower().strip()
    if key not in _db_instances:
        _db_instances[key] = ChatDatabase(key)
    return _db_instances[key]
