"""
Backend Tools for DenLab Chat.
All tool functions that agents can use - web search, GitHub, code execution, file ops, etc.
No UI code, no agent logic - just pure function implementations.
"""

import json
import re
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import from centralized config
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import APIEndpoints, Constants, FileUploadConfig


# ============================================================================
# WEB SEARCH TOOLS
# ============================================================================

def web_search(query: str, limit: int = 5) -> str:
    """
    Search the web using DuckDuckGo API.
    
    Args:
        query: Search query string
        limit: Maximum number of results (default 5)
    
    Returns:
        JSON string with search results
    """
    try:
        # Primary API: DuckDuckGo Instant Answer
        url = f"{APIEndpoints.DUCKDUCKGO_API}?q={requests.utils.quote(query)}&format=json&no_html=1&skip_disambig=1"
        resp = requests.get(url, timeout=APIEndpoints.TIMEOUT_SHORT, headers=APIEndpoints.get_headers())
        
        results = []
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Extract from RelatedTopics
            if data.get("RelatedTopics"):
                for item in data["RelatedTopics"][:limit]:
                    if isinstance(item, dict):
                        text = item.get("Text", "")
                        if text:
                            results.append({
                                "title": text[:100],
                                "snippet": text[:300],
                                "url": item.get("FirstURL", "")
                            })
        
        # Fallback: Alternative DuckDuckGo API
        if not results:
            fallback_url = f"{APIEndpoints.DUCKDUCKGO_FALLBACK}?query={requests.utils.quote(query)}&limit={limit}"
            fb_resp = requests.get(fallback_url, timeout=APIEndpoints.TIMEOUT_SHORT)
            
            if fb_resp.status_code == 200:
                for item in fb_resp.json()[:limit]:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "url": item.get("link", "")
                    })
        
        return json.dumps({
            "success": True,
            "results": results,
            "query": query,
            "count": len(results)
        }, indent=2)
        
    except requests.exceptions.Timeout:
        return json.dumps({"success": False, "error": "Search timed out. Please try again."})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def deep_research(topic: str, depth: int = 2) -> str:
    """
    Conduct deep multi-source research on a topic.
    
    Args:
        topic: Research topic
        depth: Research depth (1=quick, 2=detailed, 3=comprehensive)
    
    Returns:
        JSON string with findings and sources
    """
    try:
        findings = []
        sources = set()
        
        # Level 1: Initial search
        initial = json.loads(web_search(topic, limit=3))
        if initial.get("success"):
            for item in initial["results"]:
                sources.add(item.get("url", ""))
                findings.append({
                    "title": item.get("title", ""),
                    "source": item.get("url", ""),
                    "content": item.get("snippet", ""),
                    "level": 1
                })
        
        # Level 2: Follow-up on top findings
        if depth >= 2 and findings:
            for finding in findings[:2]:
                follow_up = json.loads(web_search(finding["title"], limit=2))
                if follow_up.get("success"):
                    for item in follow_up["results"]:
                        if item.get("url") not in sources:
                            sources.add(item.get("url", ""))
                            findings.append({
                                "title": item.get("title", ""),
                                "source": item.get("url", ""),
                                "content": item.get("snippet", ""),
                                "level": 2
                            })
        
        # Level 3: Cross-reference and third-level search
        if depth >= 3 and findings:
            for finding in findings[2:4]:
                cross = json.loads(web_search(finding["title"], limit=1))
                if cross.get("success"):
                    for item in cross["results"]:
                        if item.get("url") not in sources:
                            sources.add(item.get("url", ""))
                            findings.append({
                                "title": item.get("title", ""),
                                "source": item.get("url", ""),
                                "content": item.get("snippet", ""),
                                "level": 3
                            })
        
        # Generate summary statistics
        level_counts = {1: 0, 2: 0, 3: 0}
        for f in findings:
            level_counts[f.get("level", 1)] += 1
        
        return json.dumps({
            "success": True,
            "topic": topic,
            "depth": depth,
            "total_sources": len(sources),
            "total_findings": len(findings),
            "findings_by_level": level_counts,
            "findings": findings[:10]  # Limit to 10 findings
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ============================================================================
# GITHUB TOOLS
# ============================================================================

def github_get_files(repo: str, branch: str = None) -> str:
    """
    Get list of files from a GitHub repository.
    
    Args:
        repo: Repository in format "owner/repo" or GitHub URL
        branch: Branch name (auto-detects main/master if not specified)
    
    Returns:
        JSON string with file list
    """
    try:
        # Parse owner/repo format
        repo_clean = repo.replace("github.com/", "").replace("https://", "").replace("http://", "")
        parts = repo_clean.split("/")
        
        if len(parts) >= 2:
            owner = parts[-2]
            repo_name = parts[-1].replace(".git", "")
        else:
            return json.dumps({"success": False, "error": "Invalid repo format. Use 'owner/repo' or GitHub URL"})
        
        # Try branches in order: specified > main > master
        branches_to_try = [branch] if branch else []
        if "main" not in branches_to_try:
            branches_to_try.append("main")
        if "master" not in branches_to_try:
            branches_to_try.append("master")
        
        for try_branch in branches_to_try:
            if not try_branch:
                continue
                
            url = f"{APIEndpoints.GITHUB_API}/repos/{owner}/{repo_name}/git/trees/{try_branch}?recursive=1"
            resp = requests.get(url, timeout=APIEndpoints.TIMEOUT_MEDIUM, headers=APIEndpoints.get_github_headers())
            
            if resp.status_code == 200:
                data = resp.json()
                files = []
                dirs = []
                
                for item in data.get("tree", []):
                    if item.get("type") == "blob":
                        files.append({
                            "path": item["path"],
                            "size": item.get("size", 0),
                            "url": item.get("url", "")
                        })
                    elif item.get("type") == "tree":
                        dirs.append(item["path"])
                
                return json.dumps({
                    "success": True,
                    "repo": f"{owner}/{repo_name}",
                    "branch": try_branch,
                    "file_count": len(files),
                    "dir_count": len(dirs),
                    "files": files[:100],  # Limit to 100 files
                    "directories": dirs[:20]
                }, indent=2)
        
        return json.dumps({"success": False, "error": f"Could not access repo {owner}/{repo_name}"})
        
    except requests.exceptions.Timeout:
        return json.dumps({"success": False, "error": "GitHub API timed out"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ============================================================================
# CODE EXECUTION TOOLS
# ============================================================================

def execute_code(code: str, timeout_seconds: int = 10) -> str:
    """
    Execute Python code safely in a sandboxed environment.
    
    Args:
        code: Python code to execute
        timeout_seconds: Maximum execution time
    
    Returns:
        JSON string with stdout, stderr, and any errors
    """
    import io
    import sys
    import traceback
    import threading
    
    # Safe builtins - only allow safe operations
    SAFE_BUILTINS = {
        'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
        'enumerate': enumerate, 'float': float, 'int': int, 'len': len,
        'list': list, 'max': max, 'min': min, 'print': print, 'range': range,
        'round': round, 'set': set, 'sorted': sorted, 'str': str, 'sum': sum,
        'tuple': tuple, 'zip': zip, 'map': map, 'filter': filter,
        'pow': pow, 'divmod': divmod, 'isinstance': isinstance,
        'type': type, 'reversed': reversed
    }
    
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    
    def execute():
        nonlocal output_buffer, error_buffer
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = output_buffer
        sys.stderr = error_buffer
        
        try:
            exec(code, {"__builtins__": SAFE_BUILTINS}, {})
        except Exception as e:
            error_buffer.write(traceback.format_exc())
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Run with timeout
    thread = threading.Thread(target=execute)
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        return json.dumps({
            "success": False,
            "error": f"Code execution timed out after {timeout_seconds} seconds",
            "stdout": output_buffer.getvalue(),
            "stderr": error_buffer.getvalue()
        }, indent=2)
    
    stdout = output_buffer.getvalue()
    stderr = error_buffer.getvalue()
    
    return json.dumps({
        "success": True,
        "stdout": stdout if stdout else "(no output)",
        "stderr": stderr if stderr else "",
        "code_length": len(code)
    }, indent=2)


# ============================================================================
# URL FETCHING TOOLS
# ============================================================================

def fetch_url(url: str, max_length: int = 5000) -> str:
    """
    Fetch and clean content from a URL.
    
    Args:
        url: URL to fetch
        max_length: Maximum content length to return
    
    Returns:
        JSON string with cleaned content
    """
    try:
        resp = requests.get(
            url,
            timeout=APIEndpoints.TIMEOUT_MEDIUM,
            headers={
                "User-Agent": "DenLab/7.0 (https://denlab.chat)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        
        if resp.status_code != 200:
            return json.dumps({
                "success": False,
                "error": f"HTTP {resp.status_code}",
                "url": url
            })
        
        # Clean HTML content
        content = resp.text[:max_length * 2]  # Fetch extra for cleaning
        
        # Remove script and style tags
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # Clean whitespace
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Truncate if needed
        if len(content) > max_length:
            content = content[:max_length] + "...\n[Content truncated]"
        
        return json.dumps({
            "success": True,
            "url": url,
            "content": content,
            "content_length": len(content),
            "status_code": resp.status_code
        }, indent=2)
        
    except requests.exceptions.Timeout:
        return json.dumps({"success": False, "error": "Request timed out", "url": url})
    except requests.exceptions.ConnectionError:
        return json.dumps({"success": False, "error": "Connection failed", "url": url})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "url": url})


# ============================================================================
# FILE OPERATION TOOLS (In-memory storage)
# ============================================================================

# Global file store (will be managed by app.py session state)
_file_store: Dict[str, Dict] = {}

def set_file_store(store: Dict[str, Dict]):
    """Set the file store reference (called from app.py)."""
    global _file_store
    _file_store = store


def read_file(path: str) -> str:
    """
    Read content from an uploaded file.
    
    Args:
        path: File path/key in the file store
    
    Returns:
        JSON string with file content
    """
    if path in _file_store:
        f = _file_store[path]
        content = f.get("content", f.get("bytes", ""))
        
        # Handle bytes content
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8', errors='ignore')
            except:
                content = str(content)
        
        return json.dumps({
            "success": True,
            "content": content[:10000],
            "name": f.get("name", path),
            "size": len(content),
            "type": f.get("type", "text")
        }, indent=2)
    
    return json.dumps({"success": False, "error": f"File not found: {path}"})


def write_file(path: str, content: str) -> str:
    """
    Write content to a file (stored in memory).
    
    Args:
        path: File path/key
        content: Content to write
    
    Returns:
        JSON string with result
    """
    _file_store[path] = {
        "type": "text",
        "name": path,
        "content": content,
        "size": len(content),
        "timestamp": datetime.now().isoformat()
    }
    
    return json.dumps({
        "success": True,
        "path": path,
        "size": len(content),
        "message": f"File saved: {path}"
    }, indent=2)


def list_files() -> str:
    """
    List all files in the current session.
    
    Returns:
        JSON string with file list
    """
    files = []
    for path, data in _file_store.items():
        files.append({
            "path": path,
            "name": data.get("name", path),
            "size": data.get("size", 0),
            "type": data.get("type", "unknown"),
            "timestamp": data.get("timestamp", "")
        })
    
    return json.dumps({
        "success": True,
        "count": len(files),
        "files": files
    }, indent=2)


# ============================================================================
# IMAGE ANALYSIS TOOLS
# ============================================================================

def analyze_image(file_key: str, prompt: str = "Describe this image in detail.") -> str:
    """
    Analyze an uploaded image using vision model.
    
    Args:
        file_key: Key of the uploaded image in file store
        prompt: Analysis prompt
    
    Returns:
        JSON string with analysis result
    """
    try:
        # Import vision module - lazy import to avoid circular dependencies
        from features.vision import VisionAnalyzer
        
        if file_key not in _file_store:
            return json.dumps({"success": False, "error": "Image not found"})
        
        img_data = _file_store[file_key]
        if img_data.get("type") != "image":
            return json.dumps({"success": False, "error": "File is not an image"})
        
        analyzer = VisionAnalyzer()
        result = analyzer.analyze(img_data["bytes"], prompt=prompt, model="gemini")
        
        return json.dumps({
            "success": True,
            "analysis": result,
            "image": img_data.get("name", file_key)
        }, indent=2)
        
    except ImportError:
        return json.dumps({"success": False, "error": "Vision module not available"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ============================================================================
# UTILITY TOOLS
# ============================================================================

def get_current_time() -> str:
    """
    Get current date and time.
    
    Returns:
        JSON string with current time information
    """
    now = datetime.now()
    return json.dumps({
        "success": True,
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "timestamp": now.timestamp()
    }, indent=2)


def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression (e.g., "2 + 2 * 3")
    
    Returns:
        JSON string with result
    """
    # Allowed characters and operations
    allowed_chars = set("0123456789+-*/.()% ")
    
    if not all(c in allowed_chars for c in expression):
        return json.dumps({"success": False, "error": "Invalid characters in expression"})
    
    try:
        # Safe eval using only math operations
        result = eval(expression, {"__builtins__": {}}, {})
        return json.dumps({
            "success": True,
            "expression": expression,
            "result": result
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ============================================================================
# TOOL REGISTRY METADATA
# ============================================================================

def get_tools_metadata() -> Dict[str, Dict]:
    """
    Get metadata for all available tools.
    
    Returns:
        Dictionary with tool names and their descriptions/parameters
    """
    return {
        "web_search": {
            "description": "Search the web for current information",
            "params": {"query": "string", "limit": "integer (optional)"},
            "example": 'web_search("latest AI news")'
        },
        "deep_research": {
            "description": "Conduct deep multi-source research on a topic",
            "params": {"topic": "string", "depth": "integer (1-3, optional)"},
            "example": 'deep_research("quantum computing", depth=2)'
        },
        "github_get_files": {
            "description": "List files in a GitHub repository",
            "params": {"repo": "string (owner/repo)", "branch": "string (optional)"},
            "example": 'github_get_files("daktari-art/denlab-chat")'
        },
        "execute_code": {
            "description": "Execute Python code safely",
            "params": {"code": "string"},
            "example": 'execute_code("print(2+2)")'
        },
        "fetch_url": {
            "description": "Fetch and clean content from a URL",
            "params": {"url": "string"},
            "example": 'fetch_url("https://example.com")'
        },
        "read_file": {
            "description": "Read content from an uploaded file",
            "params": {"path": "string"},
            "example": 'read_file("myfile.txt")'
        },
        "write_file": {
            "description": "Write content to a file",
            "params": {"path": "string", "content": "string"},
            "example": 'write_file("output.txt", "Hello World")'
        },
        "list_files": {
            "description": "List all files in the current session",
            "params": {},
            "example": 'list_files()'
        },
        "analyze_image": {
            "description": "Analyze an uploaded image using vision AI",
            "params": {"file_key": "string", "prompt": "string (optional)"},
            "example": 'analyze_image("myimage.png")'
        },
        "get_current_time": {
            "description": "Get current date and time",
            "params": {},
            "example": 'get_current_time()'
        },
        "calculate": {
            "description": "Safely evaluate a mathematical expression",
            "params": {"expression": "string"},
            "example": 'calculate("15 * 23")'
        }
    }


# ============================================================================
# COMPATIBILITY ALIAS
# ============================================================================

# For backward compatibility with existing imports
PollinationsClient = None  # Will be set by client.py if needed