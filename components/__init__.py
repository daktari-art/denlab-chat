"""
UI Components for DenLab Chat.
Import components lazily to avoid circular imports.
"""

__all__ = ["Sidebar", "ChatInterface", "AgentInterface", "AdvancedSettings"]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "Sidebar":
        from components.sidebar import Sidebar
        return Sidebar
    elif name == "ChatInterface":
        from components.chat_interface import ChatInterface
        return ChatInterface
    elif name == "AgentInterface":
        from components.agent_interface import AgentInterface
        return AgentInterface
    elif name == "AdvancedSettings":
        from components.sidebar import AdvancedSettings
        return AdvancedSettings
    raise AttributeError(f"module {__name__} has no attribute {name}")