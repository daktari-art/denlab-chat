"""Central tool registry for all agents."""
from typing import Dict, Callable
import inspect

class ToolRegistry:
    """Global tool registry - singleton pattern."""
    _instance = None
    _tools: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, name: str, description: str, params: Dict = None):
        """Decorator to register a function as a tool."""
        def decorator(func: Callable):
            self._tools[name] = {
                "func": func,
                "description": description,
                "params": params or self._infer_params(func),
                "is_async": inspect.iscoroutinefunction(func)
            }
            return func
        return decorator
    
    def get_tools(self) -> Dict[str, Dict]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_tool(self, name: str) -> Dict:
        """Get specific tool."""
        return self._tools.get(name)
    
    def _infer_params(self, func: Callable) -> Dict:
        """Infer parameters from function signature."""
        sig = inspect.signature(func)
        params = {}
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            params[name] = {
                "type": "string",
                "description": f"Parameter: {name}",
                "required": param.default is inspect.Parameter.empty
            }
        return params

# Global instance
registry = ToolRegistry()
