"""
Central Tool Registry for DenLab Agents.
Provides a singleton registry for all available tools that agents can use.
"""

import inspect
from typing import Dict, List, Callable, Any, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (
    web_search,
    deep_research,
    github_get_files,
    execute_code,
    fetch_url,
    read_file,
    write_file,
    list_files,
    analyze_image,
    get_current_time,
    calculate,
    system_info,
    get_source_code,
    manage_users,
    get_agent_trace,
    get_tools_metadata
)


class ToolRegistry:
    """
    Central registry for all tools that agents can use.
    """
    
    _instance = None
    _tools: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all available tools from backend."""
        self.register(
            name="web_search",
            func=web_search,
            description="Search the web for current information. Returns titles, snippets, and URLs.",
            params={"query": {"type": "string", "description": "Search query", "required": True},
                    "num_results": {"type": "integer", "description": "Number of results (default 5)", "required": False}}
        )
        
        self.register(
            name="deep_research",
            func=deep_research,
            description="Conduct deep multi-source research on a topic. Returns findings with sources.",
            params={"topic": {"type": "string", "description": "Research topic", "required": True},
                    "depth": {"type": "integer", "description": "Research depth (1-3)", "required": False}}
        )
        
        self.register(
            name="github_get_files",
            func=github_get_files,
            description="Get list of files from a GitHub repository.",
            params={"repo_owner": {"type": "string", "description": "Repository owner", "required": True},
                    "repo_name": {"type": "string", "description": "Repository name", "required": True},
                    "path": {"type": "string", "description": "Subdirectory path", "required": False}}
        )
        
        self.register(
            name="execute_code",
            func=execute_code,
            description="Execute Python code in a safe sandbox. Returns stdout/stderr.",
            params={"code": {"type": "string", "description": "Python code to execute", "required": True},
                    "timeout": {"type": "integer", "description": "Execution timeout", "required": False}}
        )
        
        self.register(
            name="fetch_url",
            func=fetch_url,
            description="Fetch and read content from any URL. Returns cleaned text content.",
            params={"url": {"type": "string", "description": "URL to fetch", "required": True}}
        )
        
        self.register(
            name="read_file",
            func=read_file,
            description="Read content from an uploaded file in the current session.",
            params={"file_path": {"type": "string", "description": "File path or key", "required": True}}
        )
        
        self.register(
            name="write_file",
            func=write_file,
            description="Write content to a file.",
            params={"file_path": {"type": "string", "description": "File path", "required": True},
                    "content": {"type": "string", "description": "Content to write", "required": True}}
        )
        
        self.register(
            name="list_files",
            func=list_files,
            description="List all files in the current session.",
            params={"directory": {"type": "string", "description": "Directory", "required": False},
                    "pattern": {"type": "string", "description": "Glob pattern", "required": False}}
        )
        
        self.register(
            name="analyze_image",
            func=analyze_image,
            description="Analyze an uploaded image using vision AI.",
            params={"file_path": {"type": "string", "description": "File path of uploaded image", "required": True},
                    "prompt": {"type": "string", "description": "Analysis prompt", "required": False}}
        )
        
        self.register(
            name="get_current_time",
            func=get_current_time,
            description="Get current date and time.",
            params={}
        )
        
        self.register(
            name="calculate",
            func=calculate,
            description="Safely evaluate a mathematical expression.",
            params={"expression": {"type": "string", "description": "Math expression", "required": True}}
        )
        
        self.register(
            name="system_info",
            func=system_info,
            description="Get system information (developer only).",
            params={}
        )
        
        self.register(
            name="get_source_code",
            func=get_source_code,
            description="Get source code of a file for developer inspection.",
            params={
                "file_name": {"type": "string", "description": "File name", "required": True},
                "max_lines": {"type": "integer", "description": "Max lines", "required": False}
            }
        )
        
        self.register(
            name="manage_users",
            func=manage_users,
            description="Manage users (developer only).",
            params={
                "action": {"type": "string", "description": "list|create|delete", "required": False},
                "username": {"type": "string", "description": "Username", "required": False},
                "password": {"type": "string", "description": "Password", "required": False}
            }
        )
        
        self.register(
            name="get_agent_trace",
            func=get_agent_trace,
            description="Get agent execution traces (developer only).",
            params={
                "agent_name": {"type": "string", "description": "Agent name", "required": False},
                "last_n": {"type": "integer", "description": "Number of traces", "required": False}
            }
        )
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def register(self, name: str, func: Callable, description: str, 
                 params: Dict = None, is_async: bool = None) -> None:
        if params is None:
            params = self._infer_params(func)
        if is_async is None:
            is_async = inspect.iscoroutinefunction(func)
        self._tools[name] = {
            "func": func,
            "description": description,
            "params": params,
            "is_async": is_async
        }
    
    def get_tool(self, name: str) -> Optional[Dict]:
        return self._tools.get(name)
    
    def get_tools(self) -> Dict[str, Dict]:
        return self._tools.copy()
    
    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())
    
    def get_tools_metadata(self) -> Dict:
        """Get metadata for all registered tools (format expected by agents)."""
        metadata = {}
        for name, tool in self._tools.items():
            metadata[name] = {
                "description": tool["description"],
                "params": tool["params"]
            }
        return metadata
    
    def get_tool_schema(self) -> List[Dict]:
        tools = []
        for name, meta in self._tools.items():
            properties = {}
            required = []
            for param_name, param_info in meta["params"].items():
                properties[param_name] = {
                    "type": param_info.get("type", "string"),
                    "description": param_info.get("description", f"Parameter: {param_name}")
                }
                if param_info.get("required", True):
                    required.append(param_name)
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": meta["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            })
        return tools
    
    def get_tools_description(self) -> str:
        lines = ["Available tools:"]
        for name, meta in self._tools.items():
            lines.append(f"  - {name}: {meta['description'][:100]}")
        return "\n".join(lines)
    
    def execute(self, name: str, **kwargs) -> Any:
        tool = self.get_tool(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found in registry")
        func = tool["func"]
        return func(**kwargs)
    
    def has_tool(self, name: str) -> bool:
        return name in self._tools
    
    def get_tools_count(self) -> int:
        return len(self._tools)
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _infer_params(self, func: Callable) -> Dict:
        sig = inspect.signature(func)
        params = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            has_default = param.default is not inspect.Parameter.empty
            params[param_name] = {
                "type": self._infer_type(param),
                "description": f"Parameter: {param_name}",
                "required": not has_default
            }
            if has_default:
                params[param_name]["default"] = str(param.default)
        return params
    
    def _infer_type(self, param: inspect.Parameter) -> str:
        if param.annotation != inspect.Parameter.empty:
            annotation = param.annotation
            if annotation == str:
                return "string"
            elif annotation == int:
                return "integer"
            elif annotation == float:
                return "number"
            elif annotation == bool:
                return "boolean"
            elif annotation == list:
                return "array"
            elif annotation == dict:
                return "object"
        if param.default != inspect.Parameter.empty:
            default = param.default
            if isinstance(default, str):
                return "string"
            elif isinstance(default, int):
                return "integer"
            elif isinstance(default, float):
                return "number"
            elif isinstance(default, bool):
                return "boolean"
            elif isinstance(default, list):
                return "array"
            elif isinstance(default, dict):
                return "object"
        return "string"


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance


def get_tools_schema() -> List[Dict]:
    return get_tool_registry().get_tool_schema()


def get_tools_description() -> str:
    return get_tool_registry().get_tools_description()