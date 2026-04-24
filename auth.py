"""
Authentication and User Management for DenLab Chat.
Uses JSON file storage for user accounts with password hashing.
Includes hardcoded developer account for creator access.
"""

import json
import hashlib
import secrets
import os
from datetime import datetime
from typing import Dict, Optional, Any, Tuple

# Import from centralized config
import sys
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from config.settings import DeveloperConfig


# ============================================================================
# CONSTANTS
# ============================================================================

DATA_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data")
USERS_FILE = _os.path.join(DATA_DIR, "users.json")
SESSIONS_FILE = _os.path.join(DATA_DIR, "sessions.json")


# ============================================================================
# PASSWORD HASHING
# ============================================================================

class PasswordHasher:
    """Secure password hashing using PBKDF2."""
    
    @staticmethod
    def hash(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash a password with PBKDF2.
        
        Args:
            password: Plain text password
            salt: Optional salt (generated if not provided)
        
        Returns:
            Tuple of (hash_value, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        hash_value = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000  # Number of iterations
        ).hex()
        
        return hash_value, salt
    
    @staticmethod
    def verify(password: str, hash_value: str, salt: str) -> bool:
        """
        Verify a password against stored hash.
        
        Args:
            password: Plain text password to verify
            hash_value: Stored hash
            salt: Stored salt
        
        Returns:
            True if password matches, False otherwise
        """
        check_hash, _ = PasswordHasher.hash(password, salt)
        return secrets.compare_digest(check_hash, hash_value)


# ============================================================================
# TOKEN MANAGER
# ============================================================================

class TokenManager:
    """Secure session token management."""
    
    @staticmethod
    def generate() -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_format(token: str) -> bool:
        """Validate token format (basic sanity check)."""
        return isinstance(token, str) and len(token) >= 32


# ============================================================================
# AUTH MANAGER
# ============================================================================

class AuthManager:
    """
    Handle user registration, login, and account management.
    
    Features:
    - JSON file storage for users
    - PBKDF2 password hashing
    - Session token management
    - Hardcoded developer account (dennis/yessyess)
    - Account deletion with chat data cleanup
    """
    
    def __init__(self):
        _os.makedirs(DATA_DIR, exist_ok=True)
        self._users = self._load_users()
        self._sessions = self._load_sessions()
        self._hasher = PasswordHasher()
        self._token_manager = TokenManager()
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def register(self, username: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new user account.
        
        Args:
            username: Desired username (lowercase, alphanumeric + _ -)
            password: Password (min 6 characters)
            display_name: Optional display name (defaults to username.title())
        
        Returns:
            Dict with success status, token, and user info or error message
        """
        username = username.strip().lower()
        
        # Validation
        if not username or not password:
            return {"success": False, "error": "Username and password are required"}
        
        if len(username) < 3:
            return {"success": False, "error": "Username must be at least 3 characters"}
        
        if len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters"}
        
        # Username character validation
        allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not all(c in allowed_chars for c in username):
            return {"success": False, "error": "Username can only contain letters, numbers, underscores, and hyphens"}
        
        # Reserve developer username
        if username == DeveloperConfig.USERNAME:
            return {"success": False, "error": "This username is reserved. Please choose another."}
        
        # Check for existing user
        if username in self._users:
            return {"success": False, "error": "Username already exists"}
        
        # Create user
        hash_value, salt = self._hasher.hash(password)
        
        self._users[username] = {
            "username": username,
            "display_name": display_name or username.title(),
            "password_hash": hash_value,
            "password_salt": salt,
            "created_at": datetime.now().isoformat(),
            "settings": {
                "default_model": "openai",
                "stream_responses": True,
                "theme": "light"
            }
        }
        
        self._save_users()
        
        # Create session
        token = self._token_manager.generate()
        self._sessions[token] = {
            "username": username,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        self._save_sessions()
        
        return {
            "success": True,
            "token": token,
            "user": {
                "username": username,
                "display_name": self._users[username]["display_name"]
            }
        }
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and create session.
        
        Handles hardcoded developer account (dennis/yessyess) separately.
        
        Args:
            username: Username
            password: Password
        
        Returns:
            Dict with success status, token, and user info or error message
        """
        username = username.strip().lower()
        
        if not username or not password:
            return {"success": False, "error": "Username and password are required"}
        
        # Hardcoded developer login
        if DeveloperConfig.is_developer(username, password):
            token = self._token_manager.generate()
            self._sessions[token] = {
                "username": DeveloperConfig.USERNAME,
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "is_developer": True
            }
            self._save_sessions()
            
            return {
                "success": True,
                "token": token,
                "user": {
                    "username": DeveloperConfig.USERNAME,
                    "display_name": DeveloperConfig.DISPLAY_NAME,
                    "is_developer": True
                }
            }
        
        # Regular user login
        if username not in self._users:
            return {"success": False, "error": "Invalid username or password"}
        
        user = self._users[username]
        
        if not self._hasher.verify(password, user["password_hash"], user["password_salt"]):
            return {"success": False, "error": "Invalid username or password"}
        
        # Create session
        token = self._token_manager.generate()
        self._sessions[token] = {
            "username": username,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "is_developer": False
        }
        self._save_sessions()
        
        return {
            "success": True,
            "token": token,
            "user": {
                "username": username,
                "display_name": user["display_name"],
                "is_developer": False
            }
        }
    
    def logout(self, token: str) -> bool:
        """
        Invalidate a session token.
        
        Args:
            token: Session token to invalidate
        
        Returns:
            True if token was valid and removed, False otherwise
        """
        if token in self._sessions:
            del self._sessions[token]
            self._save_sessions()
            return True
        return False
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate a session token and return user info.
        
        Args:
            token: Session token to validate
        
        Returns:
            User info dict if valid, None otherwise
        """
        if not token or not self._token_manager.validate_format(token):
            return None
        
        if token not in self._sessions:
            return None
        
        session = self._sessions[token]
        username = session.get("username")
        
        # Update last activity
        session["last_activity"] = datetime.now().isoformat()
        self._save_sessions()
        
        # Developer account
        if session.get("is_developer") or username == DeveloperConfig.USERNAME:
            return {
                "username": DeveloperConfig.USERNAME,
                "display_name": DeveloperConfig.DISPLAY_NAME,
                "is_developer": True,
                "settings": {}
            }
        
        # Regular user
        if username not in self._users:
            return None
        
        user = self._users[username]
        return {
            "username": username,
            "display_name": user["display_name"],
            "is_developer": False,
            "settings": user.get("settings", {})
        }
    
    def change_password(self, token: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change user password.
        
        Args:
            token: Session token
            old_password: Current password
            new_password: New password (min 6 characters)
        
        Returns:
            Dict with success status and message
        """
        user_info = self.validate_token(token)
        if not user_info:
            return {"success": False, "error": "Not authenticated"}
        
        # Developer account cannot change password via this method
        if user_info.get("is_developer"):
            return {"success": False, "error": "Developer password is fixed. Modify code to change it."}
        
        username = user_info["username"]
        
        if username not in self._users:
            return {"success": False, "error": "User not found"}
        
        stored = self._users[username]
        
        if not self._hasher.verify(old_password, stored["password_hash"], stored["password_salt"]):
            return {"success": False, "error": "Current password is incorrect"}
        
        if len(new_password) < 6:
            return {"success": False, "error": "New password must be at least 6 characters"}
        
        # Update password
        hash_value, salt = self._hasher.hash(new_password)
        stored["password_hash"] = hash_value
        stored["password_salt"] = salt
        self._save_users()
        
        return {"success": True, "message": "Password updated successfully"}
    
    def delete_account(self, token: str, password: str) -> Dict[str, Any]:
        """
        Permanently delete user account and all associated data.
        
        Args:
            token: Session token
            password: Password confirmation
        
        Returns:
            Dict with success status and message
        """
        user_info = self.validate_token(token)
        if not user_info:
            return {"success": False, "error": "Not authenticated"}
        
        # Developer account cannot be deleted
        if user_info.get("is_developer"):
            return {"success": False, "error": "Developer account cannot be deleted"}
        
        username = user_info["username"]
        
        if username not in self._users:
            return {"success": False, "error": "User not found"}
        
        stored = self._users[username]
        
        if not self._hasher.verify(password, stored["password_hash"], stored["password_salt"]):
            return {"success": False, "error": "Password is incorrect"}
        
        # Remove user
        del self._users[username]
        self._save_users()
        
        # Remove all sessions for this user
        tokens_to_remove = [
            t for t, s in self._sessions.items()
            if s.get("username") == username
        ]
        for t in tokens_to_remove:
            del self._sessions[t]
        self._save_sessions()
        
        # Clean up chat data
        chat_file = _os.path.join(DATA_DIR, f"chats_{username}.json")
        if _os.path.exists(chat_file):
            _os.remove(chat_file)
        
        # Clean up memory data
        memory_dir = _os.path.join(DATA_DIR, "memories", username)
        if _os.path.exists(memory_dir):
            import shutil
            shutil.rmtree(memory_dir)
        
        return {"success": True, "message": "Account deleted successfully"}
    
    def update_settings(self, token: str, settings: Dict) -> Dict[str, Any]:
        """
        Update user settings.
        
        Args:
            token: Session token
            settings: Dictionary of settings to update
        
        Returns:
            Dict with success status
        """
        user_info = self.validate_token(token)
        if not user_info:
            return {"success": False, "error": "Not authenticated"}
        
        # Developer account uses in-memory settings only
        if user_info.get("is_developer"):
            return {"success": True, "message": "Developer settings updated (session only)"}
        
        username = user_info["username"]
        
        if username not in self._users:
            return {"success": False, "error": "User not found"}
        
        if "settings" not in self._users[username]:
            self._users[username]["settings"] = {}
        
        self._users[username]["settings"].update(settings)
        self._save_users()
        
        return {"success": True}
    
    def get_settings(self, token: str) -> Dict[str, Any]:
        """
        Get user settings.
        
        Args:
            token: Session token
        
        Returns:
            Dict with settings or error
        """
        user_info = self.validate_token(token)
        if not user_info:
            return {"success": False, "error": "Not authenticated"}
        
        if user_info.get("is_developer"):
            return {
                "success": True,
                "settings": {
                    "default_model": "openai",
                    "stream_responses": True,
                    "theme": "light"
                }
            }
        
        username = user_info["username"]
        
        if username not in self._users:
            return {"success": False, "error": "User not found"}
        
        return {
            "success": True,
            "settings": self._users[username].get("settings", {})
        }
    
    def get_user_count(self) -> int:
        """Get total number of registered users (excluding developer)."""
        return len(self._users)
    
    def get_active_sessions_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _load_users(self) -> Dict:
        """Load user database from JSON file."""
        if _os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_users(self):
        """Save user database to JSON file."""
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving users: {e}")
    
    def _load_sessions(self) -> Dict:
        """Load sessions from JSON file."""
        if _os.path.exists(SESSIONS_FILE):
            try:
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert ISO strings back to strings (keep as is)
                    return data
            except Exception:
                return {}
        return {}
    
    def _save_sessions(self):
        """Save sessions to JSON file."""
        try:
            # Clean up expired sessions (older than 7 days)
            expired = []
            for token, session in self._sessions.items():
                created = session.get("created_at")
                if created:
                    try:
                        created_date = datetime.fromisoformat(created)
                        if (datetime.now() - created_date).days > 7:
                            expired.append(token)
                    except:
                        pass
            
            for token in expired:
                del self._sessions[token]
            
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._sessions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving sessions: {e}")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get or create the AuthManager singleton."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def is_developer_session(token: str) -> bool:
    """Check if a session token belongs to the developer."""
    auth = get_auth_manager()
    user = auth.validate_token(token)
    return user.get("is_developer", False) if user else False