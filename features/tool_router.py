# features/tool_router.py
"""Intelligent tool selection based on query intent."""
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Intent:
    name: str
    keywords: List[str]
    tools: List[str]
    requires_confirmation: bool = False

class ToolRouter:
    """Route queries to optimal tools based on intent."""
    
    def __init__(self):
        self.intents = [
            Intent("research", 
                   ["research", "find", "search", "look up", "what is", "who is", "when did", "where is"],
                   ["web_search", "deep_research"]),
            
            Intent("code",
                   ["code", "script", "program", "execute", "run", "calculate", "compute"],
                   ["execute_code"]),
            
            Intent("file_ops",
                   ["read file", "write file", "save", "load", "open file", "create file"],
                   ["read_file", "write_file"]),
            
            Intent("web_scrape",
                   ["scrape", "fetch url", "get website", "extract from", "download page"],
                   ["fetch_url"]),
            
            Intent("image_gen",
                   ["generate image", "create image", "draw", "imagine", "picture of", "photo of"],
                   ["generate_image"]),
            
            Intent("image_analysis",
                   ["analyze image", "describe image", "what's in this image", "what does this picture show"],
                   ["analyze_image"]),
            
            Intent("analysis",
                   ["analyze", "compare", "summarize", "review", "evaluate", "explain"],
                   []),  # No specific tool, use LLM
            
            Intent("audio",
                   ["read aloud", "speak", "audio", "text to speech", "say"],
                   ["generate_audio"]),
        ]
        
        # Confidence boosting patterns
        self.boost_patterns = {
            "deep_research": r"\b(deep|thorough|comprehensive|detailed)\s+(research|analysis)\b",
            "execute_code": r"\b(run|execute|calculate|compute)\b.*\b(code|script|program)\b",
            "web_search": r"\b(current|latest|recent)\s+(news|information|data)\b",
        }
    
    def route(self, query: str, available_tools: List[str]) -> Dict[str, any]:
        """Route query to appropriate tools."""
        query_lower = query.lower()
        selected_tools = []
        primary_intent = None
        confidence = 0.0
        
        # Check each intent
        for intent in self.intents:
            matched = any(kw in query_lower for kw in intent.keywords)
            if matched:
                for tool in intent.tools:
                    if tool in available_tools and tool not in selected_tools:
                        selected_tools.append(tool)
                
                if primary_intent is None:
                    primary_intent = intent.name
                    confidence = 0.6
        
        # Boost confidence based on patterns
        for tool, pattern in self.boost_patterns.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                if tool not in selected_tools and tool in available_tools:
                    selected_tools.append(tool)
                confidence = min(confidence + 0.2, 1.0)
        
        # Handle research with depth specification
        depth = 1
        if "thorough" in query_lower or "comprehensive" in query_lower or "deep" in query_lower:
            depth = 3
        elif "detailed" in query_lower:
            depth = 2
        
        # If no tools selected, use default chat
        needs_agent = len(selected_tools) > 0
        
        return {
            "selected_tools": selected_tools,
            "primary_intent": primary_intent or "general",
            "confidence": confidence,
            "depth": depth,
            "needs_agent": needs_agent
        }
    
    def explain_routing(self, query: str, result: Dict) -> str:
        """Generate explanation of routing decision."""
        if not result["selected_tools"]:
            return "This appears to be a general conversation. I'll respond directly."
        
        tools_str = ", ".join(result["selected_tools"])
        return f"Detected intent: {result['primary_intent']} (confidence: {result['confidence']:.0%}). Using tools: {tools_str}"


# Singleton
_router = None

def get_router() -> ToolRouter:
    global _router
    if _router is None:
        _router = ToolRouter()
    return _router
