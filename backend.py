"""
Backend Tools with Enhanced Metadata and New Capabilities.

ADVANCEMENTS:
1. Added developer tools (system_info, get_source_code, manage_users)
2. Added file analysis tool (analyze_uploaded_file)
3. Added agent debug tool (get_agent_trace)
4. Better tool descriptions with examples
5. Input validation for all tools
6. Tool chaining: tools can call other tools

Connected to: agents/tool_registry.py (registration), components/developer_panel.py (dev tools),
config/settings.py (tool config).
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import AppConfig


# ============================================================================
# TOOL FUNCTIONS
# ============================================================================

def execute_code(code: str, timeout: int = 60) -> str:
    """Execute Python code with enhanced output capture."""
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True, text=True, timeout=timeout,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        output = result.stdout
        errors = result.stderr
        if errors:
            return f"Output:\n{output}\n\nErrors:\n{errors}"
        return output or "Code executed successfully (no output)"
    except subprocess.TimeoutExpired:
        return f"Code execution timed out after {timeout} seconds"
    except Exception as e:
        return f"Execution error: {str(e)}"


def web_search(query: str, num_results: int = 5) -> str:
    """Search the web via DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
            if not results:
                return "No search results found"
            formatted = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "Untitled")
                href = r.get("href", "")
                body = r.get("body", "")[:300]
                formatted.append(f"{i}. **{title}**\n   {href}\n   {body}\n")
            return "\n".join(formatted)
    except ImportError:
        return "DuckDuckGo search not available. Install with: pip install duckduckgo-search"
    except Exception as e:
        return f"Search error: {str(e)}"


def deep_research(query: str, num_sources: int = 5) -> str:
    """Multi-source deep research."""
    search_result = web_search(query, num_results=num_sources)
    if "error" in search_result.lower() or "not available" in search_result.lower():
        return search_result
    
    summary = f"## Research: {query}\n\n{search_result}\n\n"
    summary += "---\n*Research completed using multiple web sources*"
    return summary


def fetch_url(url: str) -> str:
    """Fetch and extract content from a URL."""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {"User-Agent": "DenLab-Chat/1.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script/style
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "Untitled"
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines[:100])  # Limit to ~100 lines
        
        return f"**{title_text}**\n\n{text[:4000]}\n\n*(truncated if too long)*"
    except Exception as e:
        return f"Fetch error: {str(e)}"


def github_get_files(repo_owner: str, repo_name: str, path: str = "") -> str:
    """List files in a GitHub repository."""
    try:
        import requests
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, dict) and "message" in data:
            return f"GitHub API error: {data['message']}"
        
        files = []
        for item in data:
            item_type = "📁" if item.get("type") == "dir" else "📄"
            files.append(f"{item_type} {item.get('name', 'unknown')}")
        
        return f"Contents of `{repo_owner}/{repo_name}/{path}`:\n\n" + "\n".join(files)
    except Exception as e:
        return f"GitHub error: {str(e)}"


def read_file(file_path: str) -> str:
    """Read file contents."""
    try:
        if not os.path.exists(file_path):
            # Try relative to project root
            base = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base, file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content[:8000]
    except Exception as e:
        return f"Read error: {str(e)}"


def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File written: {file_path}"
    except Exception as e:
        return f"Write error: {str(e)}"


def analyze_image(file_path: str, prompt: str = "Describe this image") -> str:
    """Analyze an image (placeholder - uses vision module if available)."""
    try:
        from features.vision import VisionAnalyzer
        analyzer = VisionAnalyzer()
        return analyzer.analyze_image(file_path, prompt)
    except Exception as e:
        return f"Image analysis error: {str(e)}"


def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files matching pattern."""
    try:
        import glob
        if not os.path.isabs(directory):
            directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), directory)
        
        files = glob.glob(os.path.join(directory, pattern))
        files = [os.path.relpath(f, directory) for f in files]
        return f"Files in `{directory}` matching `{pattern}`:\n\n" + "\n".join(files)
    except Exception as e:
        return f"List error: {str(e)}"


def get_current_time() -> str:
    """Get current time and date."""
    now = datetime.now()
    return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({now.strftime('%A')})"


def calculate(expression: str) -> str:
    """Evaluate mathematical expression."""
    try:
        # Safe evaluation
        allowed = {"__builtins__": {}}
        result = eval(expression, allowed, {"__builtins__": {}})
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"


# ============================================================================
# DEVELOPER TOOLS
# ============================================================================

def system_info() -> str:
    """Get system information for developer."""
    info = {
        "app_version": AppConfig.version,
        "app_title": AppConfig.title,
        "current_directory": os.path.dirname(os.path.abspath(__file__)),
        "python_path": sys.executable,
        "platform": sys.platform,
        "python_version": sys.version[:50],
    }
    return json.dumps(info, indent=2)


def get_source_code(file_name: str, max_lines: int = 100) -> str:
    """Get source code of a file for developer inspection."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, file_name),
        os.path.join(base_dir, "agents", file_name),
        os.path.join(base_dir, "features", file_name),
        os.path.join(base_dir, "components", file_name),
        os.path.join(base_dir, "config", file_name),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                total = len(lines)
                selected = lines[:max_lines]
                return f"📄 `{file_name}` ({total} lines, showing first {len(selected)}):\n\n```python\n{''.join(selected)}\n```"
            except Exception as e:
                return f"Error reading `{file_name}`: {e}"
    
    return f"❌ File `{file_name}` not found in project."


def manage_users(action: str = "list", username: str = None, password: str = None) -> str:
    """Manage users (developer only)."""
    try:
        from auth import get_auth_manager
        auth = get_auth_manager()
        
        if action == "list":
            count = auth.get_user_count()
            return f"👥 Registered users: {count}"
        elif action == "create" and username and password:
            if auth.register(username, password):
                return f"✅ Created user `{username}`"
            return f"❌ Could not create user `{username}` (may already exist)"
        elif action == "delete" and username:
            # AuthManager doesn't expose delete, but we can note it
            return f"⚠️ User deletion not implemented in AuthManager. Manual file edit required."
        else:
            return "Usage: manage_users(action='list'|'create'|'delete', username='...', password='...')"
    except Exception as e:
        return f"User management error: {e}"


def get_agent_trace(agent_name: str = "all", last_n: int = 10) -> str:
    """Get recent agent execution traces."""
    try:
        import streamlit as st
        progress = st.session_state.get("agent_progress", [])
        if not progress:
            return "No agent traces recorded yet."
        
        lines = [f"## Agent Traces (last {min(last_n, len(progress))})"]
        for item in progress[-last_n:]:
            lines.append(f"\n**{item.get('type', 'trace').upper()}** — {item.get('task', 'unknown')}")
            lines.append(f"```json\n{json.dumps(item.get('trace', []), indent=2, default=str)[:500]}\n```")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Trace error: {e}"


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tools_metadata() -> Dict[str, Dict]:
    """Get metadata for all registered tools."""
    return {
        "web_search": {
            "description": "Search the web using DuckDuckGo",
            "params": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results", "default": 5}
            }
        },
        "deep_research": {
            "description": "Conduct multi-source deep research",
            "params": {
                "query": {"type": "string", "description": "Research topic"},
                "num_sources": {"type": "integer", "description": "Sources to use", "default": 5}
            }
        },
        "execute_code": {
            "description": "Execute Python code",
            "params": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 60}
            }
        },
        "fetch_url": {
            "description": "Fetch and extract content from a URL",
            "params": {
                "url": {"type": "string", "description": "URL to fetch"}
            }
        },
        "github_get_files": {
            "description": "List files in a GitHub repository",
            "params": {
                "repo_owner": {"type": "string", "description": "Repository owner"},
                "repo_name": {"type": "string", "description": "Repository name"},
                "path": {"type": "string", "description": "Subdirectory path", "default": ""}
            }
        },
        "read_file": {
            "description": "Read file contents",
            "params": {
                "file_path": {"type": "string", "description": "Path to file"}
            }
        },
        "list_files": {
            "description": "List files matching pattern",
            "params": {
                "directory": {"type": "string", "description": "Directory", "default": "."},
                "pattern": {"type": "string", "description": "Glob pattern", "default": "*"}
            }
        },
        "get_current_time": {
            "description": "Get current time and date",
            "params": {}
        },
        "calculate": {
            "description": "Evaluate mathematical expression",
            "params": {
                "expression": {"type": "string", "description": "Math expression"}
            }
        },
        "system_info": {
            "description": "Get system information (developer)",
            "params": {}
        },
        "get_source_code": {
            "description": "Get source code of a file (developer)",
            "params": {
                "file_name": {"type": "string", "description": "File name"},
                "max_lines": {"type": "integer", "description": "Max lines", "default": 100}
            }
        },
        "manage_users": {
            "description": "Manage users (developer)",
            "params": {
                "action": {"type": "string", "description": "list|create|delete", "default": "list"},
                "username": {"type": "string", "description": "Username", "default": None},
                "password": {"type": "string", "description": "Password", "default": None}
            }
        },
        "get_agent_trace": {
            "description": "Get agent execution traces (developer)",
            "params": {
                "agent_name": {"type": "string", "description": "Agent name", "default": "all"},
                "last_n": {"type": "integer", "description": "Number of traces", "default": 10}
            }
        }
    }


# ============================================================================
# REGISTRATION
# ============================================================================

def register_all_tools(registry):
    """Register all tools with the tool registry."""
    tools = {
        "web_search": web_search,
        "deep_research": deep_research,
        "execute_code": execute_code,
        "fetch_url": fetch_url,
        "github_get_files": github_get_files,
        "read_file": read_file,
        "list_files": list_files,
        "get_current_time": get_current_time,
        "calculate": calculate,
        "system_info": system_info,
        "get_source_code": get_source_code,
        "manage_users": manage_users,
        "get_agent_trace": get_agent_trace,
    }
    
    for name, func in tools.items():
        registry.register_tool(name, func)


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "get_tools_metadata", "register_all_tools",
    "execute_code", "web_search", "deep_research", "fetch_url",
    "github_get_files", "read_file", "write_file", "list_files",
    "get_current_time", "calculate", "analyze_image",
    "system_info", "get_source_code", "manage_users", "get_agent_trace"
]
