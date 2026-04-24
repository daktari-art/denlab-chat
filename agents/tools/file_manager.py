"""File operations."""
import json
from pathlib import Path
from typing import Union

class FileManager:
    """Manage file operations."""
    
    def read(self, path: str) -> str:
        """Read file contents."""
        try:
            p = Path(path)
            if not p.exists():
                return f"Error: File {path} not found"
            
            text = p.read_text(encoding='utf-8', errors='ignore')
            return text[:10000]  # Limit size
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def write(self, path: str, content: str) -> str:
        """Write content to file."""
        try:
            p = Path(path)
            p.write_text(content, encoding='utf-8')
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def list_dir(self, path: str = ".") -> str:
        """List directory contents."""
        try:
            p = Path(path)
            items = []
            for item in p.iterdir():
                item_type = "📁" if item.is_dir() else "📄"
                items.append(f"{item_type} {item.name}")
            return "\n".join(items)
        except Exception as e:
            return f"Error: {str(e)}"

_fm = FileManager()

def read_file(path: str) -> str:
    """Read a file's contents."""
    return _fm.read(path)

def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    return _fm.write(path, content)
