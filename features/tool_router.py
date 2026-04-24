"""
Intelligent Tool Router for DenLab Chat.
Detects user intent and routes queries to appropriate tools.
No API calls - pure intent detection.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

# Import from centralized config
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Constants


# ============================================================================
# INTENT DEFINITIONS
# ============================================================================

@dataclass
class Intent:
    """Intent definition with keywords, tools, and confidence boost patterns."""
    name: str
    keywords: List[str]
    tools: List[str]
    requires_confirmation: bool = False
    confidence_boost: float = 0.0


class IntentRegistry:
    """Central registry of all intents and their routing rules."""
    
    # All available intents
    INTENTS: List[Intent] = [
        Intent(
            name="research",
            keywords=["research", "find", "search", "look up", "what is", "who is", 
                      "when did", "where is", "tell me about", "information on"],
            tools=["web_search", "deep_research"],
            confidence_boost=0.1
        ),
        Intent(
            name="github",
            keywords=["github", "repo", "repository", "clone", "list files", "daktari-art"],
            tools=["github_get_files"],
            confidence_boost=0.2
        ),
        Intent(
            name="code",
            keywords=["code", "script", "program", "execute", "run", "calculate", 
                      "compute", "python", "function"],
            tools=["execute_code"],
            confidence_boost=0.1
        ),
        Intent(
            name="file_ops",
            keywords=["read file", "write file", "save", "load", "open file", 
                      "create file", "upload", "download"],
            tools=["read_file", "write_file"],
            confidence_boost=0.05
        ),
        Intent(
            name="web_scrape",
            keywords=["scrape", "fetch url", "get website", "extract from", 
                      "download page", "get content from"],
            tools=["fetch_url"],
            confidence_boost=0.15
        ),
        Intent(
            name="image_gen",
            keywords=["generate image", "create image", "draw", "imagine", 
                      "picture of", "photo of", "/imagine"],
            tools=["generate_image"],
            confidence_boost=0.1
        ),
        Intent(
            name="image_analysis",
            keywords=["analyze image", "describe image", "what's in this image", 
                      "what does this picture show", "uploaded image"],
            tools=["analyze_image"],
            confidence_boost=0.05
        ),
        Intent(
            name="audio",
            keywords=["read aloud", "speak", "audio", "text to speech", "say", "/audio"],
            tools=["generate_audio"],
            confidence_boost=0.1
        ),
        Intent(
            name="analysis",
            keywords=["analyze", "compare", "summarize", "review", "evaluate", 
                      "explain", "break down", "synthesize"],
            tools=[],  # No specific tool - use LLM directly
            confidence_boost=0.0
        ),
        Intent(
            name="agent",
            keywords=["/agent", "autonomous", "let agent handle", "delegate to agent"],
            tools=[],  # Triggers agent mode
            confidence_boost=0.3
        ),
    ]
    
    # Deep/detailed research boost patterns
    DEEP_RESEARCH_PATTERNS: List[Tuple[str, int]] = [
        (r"\b(deep|thorough|comprehensive|detailed)\s+(research|analysis)\b", 2),
        (r"\b(in-depth|extensive|multi-source)\b", 2),
        (r"\b(depth|levels?)\s*(of)?\s*(research|analysis)\b", 1),
    ]
    
    # Code execution boost patterns
    CODE_BOOST_PATTERNS: List[Tuple[str, int]] = [
        (r"\b(run|execute|calculate|compute)\b.*\b(code|script|program)\b", 1),
        (r"\b(solve|implement|write code for)\b", 1),
    ]
    
    # Web search boost patterns (current/latest information)
    WEB_SEARCH_BOOST: List[Tuple[str, int]] = [
        (r"\b(current|latest|recent|today|now)\s+(news|information|data|events)\b", 1),
        (r"\b(as of|updated)\b", 1),
    ]


# ============================================================================
# TOOL ROUTER
# ============================================================================

class ToolRouter:
    """
    Routes user queries to appropriate tools based on intent detection.
    
    Features:
    - Keyword-based intent matching
    - Confidence scoring with boost patterns
    - Depth detection for research tasks
    - Agent mode triggering for complex tasks
    """
    
    def __init__(self):
        self.intents = IntentRegistry.INTENTS
        self.deep_patterns = IntentRegistry.DEEP_RESEARCH_PATTERNS
        self.code_patterns = IntentRegistry.CODE_BOOST_PATTERNS
        self.web_patterns = IntentRegistry.WEB_SEARCH_BOOST
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def route(self, query: str, available_tools: List[str]) -> Dict[str, Any]:
        """
        Route query to appropriate tools.
        
        Args:
            query: User's input text
            available_tools: List of tool names available in the system
            
        Returns:
            Dict with:
            - selected_tools: List of tools to use
            - primary_intent: Name of the primary detected intent
            - confidence: Confidence score (0-1)
            - depth: Research depth (1-3)
            - needs_agent: Whether agent mode should be triggered
            - explanation: Human-readable explanation
        """
        query_lower = query.lower()
        selected_tools = []
        primary_intent = None
        confidence = 0.0
        
        # Step 1: Match against all intents
        for intent in self.intents:
            matched = any(kw in query_lower for kw in intent.keywords)
            
            if matched:
                # Add tools from this intent
                for tool in intent.tools:
                    if tool in available_tools and tool not in selected_tools:
                        selected_tools.append(tool)
                
                # Set primary intent if not already set
                if primary_intent is None:
                    primary_intent = intent.name
                    confidence = 0.6 + intent.confidence_boost
                else:
                    # Boost confidence if multiple intents match the same tools
                    if set(intent.tools).intersection(selected_tools):
                        confidence = min(confidence + 0.1, 0.95)
        
        # Step 2: Apply confidence boost patterns
        confidence = self._apply_boost_patterns(query_lower, confidence, selected_tools)
        
        # Step 3: Detect research depth
        depth = self._detect_depth(query_lower)
        
        # Step 4: Determine if agent mode is needed
        needs_agent = self._needs_agent(query_lower, selected_tools, confidence)
        
        # Step 5: If no tools selected, use default chat
        if not selected_tools:
            selected_tools = ["chat"]  # Special flag for direct LLM
        
        # Step 6: Generate explanation
        explanation = self._generate_explanation(primary_intent, selected_tools, confidence)
        
        return {
            "selected_tools": selected_tools,
            "primary_intent": primary_intent or "general",
            "confidence": round(confidence, 2),
            "depth": depth,
            "needs_agent": needs_agent,
            "explanation": explanation
        }
    
    def explain_routing(self, query: str, result: Dict[str, Any]) -> str:
        """
        Generate a human-readable explanation of the routing decision.
        
        Useful for showing users why agent mode was triggered or which tools were selected.
        """
        if not result.get("selected_tools") or result["selected_tools"] == ["chat"]:
            return "This appears to be a general conversation. I'll respond directly."
        
        tools_str = ", ".join(result["selected_tools"][:3])
        intent = result.get("primary_intent", "general")
        confidence = result.get("confidence", 0)
        
        explanation = f"Detected intent: {intent} (confidence: {confidence:.0%})"
        
        if tools_str and tools_str != "chat":
            explanation += f"\nUsing tools: {tools_str}"
        
        if result.get("needs_agent"):
            explanation += "\nThis task is complex - switching to Agent mode for better results."
        
        return explanation
    
    def get_intent_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all registered intents (for debugging/admin)."""
        return [
            {
                "name": intent.name,
                "keywords": intent.keywords[:5],  # Show first 5 only
                "tools": intent.tools,
                "has_boost": intent.confidence_boost > 0
            }
            for intent in self.intents
        ]
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _apply_boost_patterns(self, query: str, current_confidence: float, selected_tools: List[str]) -> float:
        """Apply confidence boost patterns for specific tool types."""
        confidence = current_confidence
        
        # Deep research boost
        if "deep_research" in selected_tools or "web_search" in selected_tools:
            for pattern, boost in self.deep_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    confidence += boost * 0.1
        
        # Code execution boost
        if "execute_code" in selected_tools:
            for pattern, boost in self.code_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    confidence += boost * 0.1
        
        # Web search boost (current/latest information)
        if "web_search" in selected_tools or "deep_research" in selected_tools:
            for pattern, boost in self.web_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    confidence += boost * 0.1
        
        return min(confidence, 0.95)
    
    def _detect_depth(self, query: str) -> int:
        """
        Detect research depth from query.
        
        Returns:
            1: Quick search
            2: Detailed research
            3: Comprehensive multi-source research
        """
        depth = 1  # Default to quick search
        
        # Check for depth indicators
        if re.search(r"\b(thorough|comprehensive|deep|extensive|multi-source)\b", query, re.IGNORECASE):
            depth = 3
        elif re.search(r"\b(detailed|in-depth|full|complete)\b", query, re.IGNORECASE):
            depth = 2
        
        # Check for explicit depth specification
        depth_match = re.search(r"depth\s*[:=]\s*(\d+)", query, re.IGNORECASE)
        if depth_match:
            requested = int(depth_match.group(1))
            depth = min(max(requested, 1), 3)
        
        return depth
    
    def _needs_agent(self, query: str, selected_tools: List[str], confidence: float) -> bool:
        """
        Determine if task requires agent mode.
        
        Agent mode is triggered for:
        - Multi-tool tasks (more than 2 tools selected)
        - GitHub repository operations
        - Complex multi-step research
        - Explicit /agent command
        - High confidence on complex intents
        """
        # Explicit agent command
        if query.startswith("/agent") or "/agent" in query:
            return True
        
        # Multi-tool tasks
        if len(selected_tools) >= 2 and "chat" not in selected_tools:
            return True
        
        # GitHub operations (often complex)
        if "github_get_files" in selected_tools:
            return True
        
        # High confidence on research with depth > 1
        if "deep_research" in selected_tools and self._detect_depth(query) > 1:
            return True
        
        # Complex code tasks
        if "execute_code" in selected_tools and "write_file" in selected_tools:
            return True
        
        return False
    
    def _generate_explanation(self, intent: Optional[str], tools: List[str], confidence: float) -> str:
        """Generate internal explanation of routing decision."""
        if not intent:
            return "No specific intent detected. Using default chat."
        
        if tools == ["chat"]:
            return f"Intent '{intent}' detected but no specific tools needed. Using direct chat."
        
        return f"Intent '{intent}' detected with {len(tools)} tool(s). Confidence: {confidence:.0%}"


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_router_instance: Optional[ToolRouter] = None


def get_router() -> ToolRouter:
    """Get singleton ToolRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ToolRouter()
    return _router_instance


def route_query(query: str, available_tools: List[str]) -> Dict[str, Any]:
    """Convenience function to route a query."""
    router = get_router()
    return router.route(query, available_tools)