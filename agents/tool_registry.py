"""
Central Tool Registry for DenLab Agents.
Provides a singleton registry for all available tools that agents can use.
"""

import inspect
from typing import Dict, List, Callable, Any, Optional

# Import from backend for tool functions
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


# ============================================================================
# TOOL REGISTRY
# ============================================================================

class ToolRegistry:
    """
    Central registry for all tools that agents can use.
    
    Features:
    - Singleton pattern for global access
    - Automatic parameter inference from function signatures
    - Tool metadata storage
    - Async/sync function detection
    """
    
    _instance = None
    _tools: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the registry with all backend tools."""
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all available tools from backend."""
        
        # Core tools
        self.register(
            name="web_search",
            func=web_search,
            description="Search the web for current information. Returns titles, snippets, and URLs.",
            params={"query": {"type": "string", "description": "Search query", "required": True},
                    "limit": {"type": "integer", "description": "Number of results (default 5)", "required": False}}
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
            description="Get list of files from a GitHub repository. Pass 'owner/repo' format.",
            params={"repo": {"type": "string", "description": "GitHub repository (owner/repo)", "required": True},
                    "branch": {"type": "string", "description": "Branch name (optional)", "required": False}}
        )
        
        self.register(
            name="execute_code",
            func=execute_code,
            description="Execute Python code in a safe sandbox. Returns stdout/stderr.",
            params={"code": {"type": "string", "description": "Python code to execute", "required": True},
                    "timeout_seconds": {"type": "integer", "description": "Execution timeout", "required": False}}
        )
        
        self.register(
            name="fetch_url",
            func=fetch_url,
            description="Fetch and read content from any URL. Returns cleaned text content.",
            params={"url": {"type": "string", "description": "URL to fetch", "required": True},
                    "max_length": {"type": "integer", "description": "Max content length", "required": False}}
        )
        
        self.register(
            name="read_file",
            func=read_file,
            description="Read content from an uploaded file in the current session.",
            params={"path": {"type": "string", "description": "File path or key", "required": True}}
        )
        
        self.register(
            name="write_file",
            func=write_file,
            description="Write content to a file (stored in session memory).",
            params={"path": {"type": "string", "description": "File path", "required": True},
                    "content": {"type": "string", "description": "Content to write", "required": True}}
        )
        
        self.register(
            name="list_files",
            func=list_files,
            description="List all files in the current session.",
            params={}
        )
        
        self.register(
            name="analyze_image",
            func=analyze_image,
            description="Analyze an uploaded image using vision AI.",
            params={"file_key": {"type": "string", "description": "File key of uploaded image", "required": True},
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
        
        # Developer tools
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
        """
        Register a tool in the registry.
        
        Args:
            name: Tool name (used by agent to call)
            func: Function to execute
            description: Human-readable description
            params: Parameter schema (auto-inferred if not provided)
            is_async: Whether function is async (auto-detected if not provided)
        """
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
        """
        Get a tool by name.
        
        Args:
            name: Tool name
        
        Returns:
            Tool dict or None if not found
        """
        return self._tools.get(name)
    
    def get_tools(self) -> Dict[str, Dict]:
        """
        Get all registered tools.
        
        Returns:
            Dictionary of tool name -> tool metadata
        """
        return self._tools.copy()
    
    def get_tool_names(self) -> List[str]:
        """
        Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_tool_schema(self) -> List[Dict]:
        """
        Get OpenAI-compatible tool schema for function calling.
        
        Returns:
            List of tool definitions in OpenAI format
        """
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
        """
        Get a human-readable description of all tools.
        
        Returns:
            Formatted string with tool names and descriptions
        """
        lines = ["Available tools:"]
        for name, meta in self._tools.items():
            lines.append(f"  - {name}: {meta['description'][:100]}")
        return "\n".join(lines)
    
    def execute(self, name: str, **kwargs) -> Any:
        """
        Execute a tool by name.
        
        Args:
            name: Tool name
            **kwargs: Arguments to pass to the tool function
        
        Returns:
            Tool execution result
        
        Raises:
            KeyError: If tool not found
        """
        tool = self.get_tool(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found in registry")
        
        func = tool["func"]
        return func(**kwargs)
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool exists in the registry."""
        return name in self._tools
    
    def get_tools_count(self) -> int:
        """Get the number of registered tools."""
        return len(self._tools)
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _infer_params(self, func: Callable) -> Dict:
        """
        Infer parameter schema from function signature.
        
        Args:
            func: Function to inspect
        
        Returns:
            Parameter schema dictionary
        """
        sig = inspect.signature(func)
        params = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Determine if parameter has default value
            has_default = param.default is not inspect.Parameter.empty
            
            params[param_name] = {
                "type": self._infer_type(param),
                "description": f"Parameter: {param_name}",
                "required": not has_default
            }
            
            # Add default value info if present
            if has_default:
                params[param_name]["default"] = str(param.default)
        
        return params
    
    def _infer_type(self, param: inspect.Parameter) -> str:
        """Infer parameter type from annotation or default value."""
        # Check annotation
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
        
        # Check default value
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
        
        # Default to string
        return "string"
    
    def _get_param_type_name(self, param) -> str:
        """Helper to get type name from parameter."""
        if hasattr(param, 'annotation') and param.annotation != inspect.Parameter.empty:
            return param.annotation.__name__.lower()
        return "string"


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the singleton ToolRegistry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance


def get_tools_schema() -> List[Dict]:
    """Convenience function to get OpenAI-compatible tool schema."""
    return get_tool_registry().get_tool_schema()


def get_tools_description() -> str:
    """Convenience function to get human-readable tool descriptions."""
    return get_tool_registry().get_tools_description()