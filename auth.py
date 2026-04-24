"""Authentication and user management for DenLab Chat.
Uses JSON file storage for user accounts with password hashing.
"""
import json
import hashlib
import secrets
import os
from datetime import datetime
from typing import Dict, Optional, Any

# Storage paths
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

class AuthManager:
    """Handle user registration, login, and account management."""
    
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._users = self._load_users()
        self._sessions: Dict[str, str] = {}  # token -> username
    
    def _load_users(self) -> Dict:
        """Load user database from JSON file."""
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_users(self):
        """Save user database to JSON file."""
        with open(USERS_FILE, 'w') as f:
            json.dump(self._users, f, indent=2)
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """Hash password with salt using PBKDF2."""
        if salt is None:
            salt = secrets.token_hex(16)
        hash_value = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return hash_value, salt
    
    def _verify_password(self, password: str, hash_value: str, salt: str) -> bool:
        """Verify password against stored hash."""
        check, _ = self._hash_password(password, salt)
        return secrets.compare_digest(check, hash_value)
    
    def _generate_token(self) -> str:
        """Generate secure session token."""
        return secrets.token_urlsafe(32)
    
    def register(self, username: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user account.
        
        Returns: {"success": bool, "token": str, "user": dict} or {"success": False, "error": str}
        """
        username = username.strip().lower()
        
        if not username or not password:
            return {"success": False, "error": "Username and password are required"}
        
        if len(username) < 3:
            return {"success": False, "error": "Username must be at least 3 characters"}
        
        if len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters"}
        
        if not username.replace("_", "").replace("-", "").isalnum():
            return {"success": False, "error": "Username can only contain letters, numbers, underscores, and hyphens"}
        
        if username in self._users:
            return {"success": False, "error": "Username already exists"}
        
        hash_value, salt = self._hash_password(password)
        
        self._users[username] = {
            "username": username,
            "display_name": display_name or username.title(),
            "password_hash": hash_value,
            "password_salt": salt,
            "created_at": datetime.now().isoformat(),
            "settings": {
                "default_model": "openai",
                "stream_responses": True,
                "theme": "dark"
            }
        }
        
        self._save_users()
        
        token = self._generate_token()
        self._sessions[token] = username
        
        return {
            "success": True,
            "token": token,
            "user": {
                "username": username,
                "display_name": self._users[username]["display_name"]
            }
        }
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user and create session.
        
        Returns: {"success": bool, "token": str, "user": dict} or {"success": False, "error": str}
        """
        username = username.strip().lower()
        
        if not username or not password:
            return {"success": False, "error": "Username and password are required"}
        
        if username not in self._users:
            return {"success": False, "error": "Invalid username or password"}
        
        user = self._users[username]
        if not self._verify_password(password, user["password_hash"], user["password_salt"]):
            return {"success": False, "error": "Invalid username or password"}
        
        token = self._generate_token()
        self._sessions[token] = username
        
        return {
            "success": True,
            "token": token,
            "user": {
                "username": username,
                "display_name": user["display_name"]
            }
        }
    
    def logout(self, token: str):
        """Invalidate session token."""
        if token in self._sessions:
            del self._sessions[token]
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """Validate session token and return user info."""
        if token not in self._sessions:
            return None
        
        username = self._sessions[token]
        if username not in self._users:
            return None
        
        user = self._users[username]
        return {
            "username": username,
            "display_name": user["display_name"],
            "settings": user.get("settings", {})
        }
    
    def change_password(self, token: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """Change user password."""
        user = self.validate_token(token)
        if not user:
            return {"success": False, "error": "Not authenticated"}
        
        username = user["username"]
        stored = self._users[username]
        
        if not self._verify_password(old_password, stored["password_hash"], stored["password_salt"]):
            return {"success": False, "error": "Current password is incorrect"}
        
        if len(new_password) < 6:
            return {"success": False, "error": "New password must be at least 6 characters"}
        
        hash_value, salt = self._hash_password(new_password)
        stored["password_hash"] = hash_value
        stored["password_salt"] = salt
        self._save_users()
        
        return {"success": True}
    
    def delete_account(self, token: str, password: str) -> Dict[str, Any]:
        """Permanently delete user account and all data."""
        user = self.validate_token(token)
        if not user:
            return {"success": False, "error": "Not authenticated"}
        
        username = user["username"]
        stored = self._users[username]
        
        if not self._verify_password(password, stored["password_hash"], stored["password_salt"]):
            return {"success": False, "error": "Password is incorrect"}
        
        # Remove user
        del self._users[username]
        self._save_users()
        
        # Remove session
        if token in self._sessions:
            del self._sessions[token]
        
        # Clean up chat data
        chat_file = os.path.join(DATA_DIR, f"chats_{username}.json")
        if os.path.exists(chat_file):
            os.remove(chat_file)
        
        return {"success": True}
    
    def update_settings(self, token: str, settings: Dict) -> Dict[str, Any]:
        """Update user settings."""
        user = self.validate_token(token)
        if not user:
            return {"success": False, "error": "Not authenticated"}
        
        username = user["username"]
        if "settings" not in self._users[username]:
            self._users[username]["settings"] = {}
        
        self._users[username]["settings"].update(settings)
        self._save_users()
        
        return {"success": True}
    
    def get_settings(self, token: str) -> Dict[str, Any]:
        """Get user settings."""
        user = self.validate_token(token)
        if not user:
            return {"success": False, "error": "Not authenticated"}
        
        username = user["username"]
        return {
            "success": True,
            "settings": self._users[username].get("settings", {})
        }


# Singleton
_auth_manager: Optional[AuthManager] = None

def get_auth_manager() -> AuthManager:
    """Get or create the AuthManager singleton."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
