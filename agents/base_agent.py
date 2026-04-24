"""
Base Agent for DenLab Chat.
Autonomous agent with tool-use capabilities - single agent execution.
No swarm logic here - that belongs in orchestrator.py.
"""

import json
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Union

# Import from completed files
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SystemPrompts, Constants, AppConfig
from client import get_client, MultiProviderClient
from agents.tool_registry import get_tool_registry, ToolRegistry


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class AgentState(Enum):
    """Possible states of an agent."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_TOOL = "waiting_tool"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ToolCall:
    """Record of a single tool call execution."""
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    status: str = "pending"  # pending, running, success, error
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "result": str(self.result)[:500] if self.result else None,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms
        }
    
    def to_openai_format(self) -> Dict:
        """Convert to OpenAI tool call format."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments)
            }
        }
    
    @classmethod
    def from_openai_format(cls, data: Dict) -> "ToolCall":
        """Create from OpenAI tool call format."""
        function = data.get("function", {})
        return cls(
            id=data.get("id", ""),
            name=function.get("name", ""),
            arguments=json.loads(function.get("arguments", "{}"))
        )


@dataclass
class AgentTrace:
    """Record of a single agent step."""
    step: int
    thought: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    observation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "step": self.step,
            "thought": self.thought[:500],
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "observation": self.observation[:500] if self.observation else None,
            "timestamp": self.timestamp.isoformat()
        }


# ============================================================================
# BASE AGENT
# ============================================================================

class BaseAgent(ABC):
    """
    Autonomous agent with tool-use capabilities.
    
    Features:
    - Step-by-step reasoning loop
    - Tool calling and execution
    - Progress tracking with traces
    - Configurable max steps
    - Memory integration via client
    """
    
    def __init__(
        self,
        name: str,
        model: str = "openai",
        max_steps: int = None,
        system_prompt: str = None
    ):
        """
        Initialize the agent.
        
        Args:
            name: Agent name (for logging/display)
            model: Model to use (e.g., "openai", "claude")
            max_steps: Maximum steps before stopping (default from config)
            system_prompt: Custom system prompt (uses default if not provided)
        """
        self.name = name
        self.model = model
        self.max_steps = max_steps or AppConfig.max_agent_steps
        self.system_prompt = system_prompt or SystemPrompts.MAIN_PROMPT
        
        self.state = AgentState.IDLE
        self.traces: List[AgentTrace] = []
        self.memory: Dict[str, Any] = {}
        self.step_count = 0
        
        # Callbacks
        self.on_step: Optional[Callable[[AgentTrace], None]] = None
        self.on_tool_call: Optional[Callable[[ToolCall], None]] = None
        self.on_complete: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Client and tool registry
        self._client = None  # Lazy loaded
        self._tool_registry = get_tool_registry()
    
    # ========================================================================
    # Properties
    # ========================================================================
    
    @property
    def client(self) -> MultiProviderClient:
        """Lazy-load the client."""
        if self._client is None:
            self._client = get_client()
        return self._client
    
    @property
    def is_complete(self) -> bool:
        """Check if agent has completed."""
        return self.state in [AgentState.COMPLETE, AgentState.ERROR]
    
    @property
    def last_trace(self) -> Optional[AgentTrace]:
        """Get the most recent trace."""
        return self.traces[-1] if self.traces else None
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    async def run(self, task: str, context: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Execute the agent loop for a given task.
        
        Args:
            task: User task/prompt
            context: Additional context (optional)
            user_id: User ID for memory (optional)
        
        Returns:
            Final response string
        """
        self.state = AgentState.PLANNING
        self.step_count = 0
        self.traces = []
        
        # Build initial messages
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._build_user_prompt(task, context)}
        ]
        
        try:
            while self.step_count < self.max_steps:
                self.step_count += 1
                self.state = AgentState.EXECUTING
                
                # Get tool schema
                tools = self._tool_registry.get_tool_schema() if self._tool_registry.get_tools_count() > 0 else None
                
                # Call LLM
                response = await self._llm_call(messages, tools=tools, user_id=user_id)
                
                if response.get("guardrail_triggered"):
                    self.state = AgentState.COMPLETE
                    return response["content"]
                
                content = response.get("content") or ""
                tool_calls_raw = response.get("tool_calls") or []
                
                # If no tool calls, we're done
                if not tool_calls_raw:
                    self.state = AgentState.COMPLETE
                    
                    if self.on_complete:
                        self.on_complete(content)
                    
                    # Record final trace
                    self.traces.append(AgentTrace(
                        step=self.step_count,
                        thought=content[:200] if content else "Final response",
                        tool_calls=[]
                    ))
                    
                    return content or "Task completed."
                
                # Create trace for this step
                trace = AgentTrace(
                    step=self.step_count,
                    thought=content[:500] if content else f"Using {len(tool_calls_raw)} tool(s)..."
                )
                
                # Parse and execute tool calls
                tool_calls = []
                for tc_raw in tool_calls_raw:
                    tc = ToolCall.from_openai_format(tc_raw)
                    
                    if self.on_tool_call:
                        self.on_tool_call(tc)
                    
                    # Execute the tool
                    start_time = time.time()
                    try:
                        result = self._tool_registry.execute(tc.name, **tc.arguments)
                        tc.result = result
                        tc.status = "success"
                    except Exception as e:
                        tc.result = f"Error: {str(e)}"
                        tc.status = "error"
                    
                    tc.duration_ms = (time.time() - start_time) * 1000
                    tool_calls.append(tc)
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(tc.result)[:4000]
                    })
                
                trace.tool_calls = tool_calls
                self.traces.append(trace)
                
                if self.on_step:
                    self.on_step(trace)
                
                # Add assistant message with tool calls
                assistant_msg = {
                    "role": "assistant",
                    "content": content or "Using tools...",
                    "tool_calls": [tc.to_openai_format() for tc in tool_calls]
                }
                messages.append(assistant_msg)
                
                # Get follow-up response after tool execution
                follow_up = await self._llm_call(messages, user_id=user_id)
                follow_content = follow_up.get("content") or ""
                
                if follow_content:
                    messages.append({"role": "assistant", "content": follow_content})
                    
                    # Check if this appears to be final answer
                    if self._is_final_answer(follow_content):
                        self.state = AgentState.COMPLETE
                        
                        if self.on_complete:
                            self.on_complete(follow_content)
                        
                        # Record final trace
                        self.traces.append(AgentTrace(
                            step=self.step_count + 0.5,
                            thought=follow_content[:200],
                            tool_calls=[]
                        ))
                        
                        return follow_content
                    
                    # Continue loop if more tool calls expected
                    continue
            
            # Max steps reached
            self.state = AgentState.ERROR
            error_msg = self._build_max_steps_message()
            
            if self.on_error:
                self.on_error(error_msg)
            
            return error_msg
            
        except Exception as e:
            self.state = AgentState.ERROR
            error_msg = f"Agent error: {str(e)}"
            
            if self.on_error:
                self.on_error(error_msg)
            
            return error_msg
    
    def reset(self):
        """Reset agent state for a new task."""
        self.state = AgentState.IDLE
        self.traces = []
        self.memory = {}
        self.step_count = 0
    
    def get_trace_summary(self) -> str:
        """Get a summary of the agent's execution trace."""
        if not self.traces:
            return "No execution traces available."
        
        lines = [f"Agent: {self.name}", f"Steps: {len(self.traces)}", ""]
        
        for trace in self.traces:
            lines.append(f"Step {trace.step}:")
            if trace.thought:
                lines.append(f"  Thought: {trace.thought[:100]}...")
            if trace.tool_calls:
                for tc in trace.tool_calls:
                    icon = "✅" if tc.status == "success" else "❌"
                    lines.append(f"  {icon} {tc.name} ({tc.duration_ms:.0f}ms)")
        
        return "\n".join(lines)
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with available tools."""
        tools_desc = self._tool_registry.get_tools_description()
        return f"""{self.system_prompt}

{self._tool_registry.get_tools_description()}

You are {self.name}. You have {self.max_steps} steps maximum.

When using tools:
1. Call the tool with appropriate arguments
2. Wait for the result
3. Continue based on the result
4. When you have the final answer, respond directly (no tool calls)

Think step by step. Explain your reasoning before using tools."""
    
    def _build_user_prompt(self, task: str, context: Optional[str]) -> str:
        """Build the user prompt with context."""
        if context:
            return f"Task: {task}\n\nContext: {context}"
        return f"Task: {task}"
    
    def _is_final_answer(self, content: str) -> bool:
        """Determine if the response appears to be a final answer."""
        if not content:
            return False
        
        # If no code blocks and length is reasonable, likely final answer
        if "```" not in content and len(content) > 100:
            return True
        
        # If contains final answer indicators
        indicators = ["final answer", "in summary", "to conclude", "here is your", "task completed"]
        if any(indicator in content.lower() for indicator in indicators):
            return True
        
        return False
    
    def _build_max_steps_message(self) -> str:
        """Build message when max steps are reached."""
        lines = [f"⚠️ Maximum steps ({self.max_steps}) reached. Task may be incomplete.\n"]
        lines.append("## Progress so far:\n")
        
        for trace in self.traces:
            if trace.thought:
                lines.append(f"**Step {trace.step}**: {trace.thought[:150]}...")
            for tc in trace.tool_calls:
                lines.append(f"  - `{tc.name}` - {tc.status}")
        
        lines.append("\nTry increasing max steps in settings or breaking down the task.")
        
        return "\n".join(lines)
    
    # ========================================================================
    # LLM Call (Override in subclass if needed)
    # ========================================================================
    
    async def _llm_call(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call the LLM API.
        
        Can be overridden in subclasses for custom behavior.
        
        Args:
            messages: List of message dicts
            tools: Optional tool schema for function calling
            user_id: User ID for memory
        
        Returns:
            Dict with 'content' and optional 'tool_calls'
        """
        # Run in thread pool to avoid blocking (since client.sync is sync)
        loop = asyncio.get_event_loop()
        
        def sync_call():
            return self.client.chat(
                messages=messages,
                model=self.model,
                temperature=0.7,
                tools=tools,
                user_id=user_id
            )
        
        result = await loop.run_in_executor(None, sync_call)
        return result


# ============================================================================
# SIMPLE AGENT (for testing)
# ============================================================================

class SimpleAgent(BaseAgent):
    """
    Simple agent implementation with minimal configuration.
    Useful for testing and simple tool use scenarios.
    """
    
    def __init__(self, name: str = "SimpleAgent", model: str = "openai"):
        super().__init__(name=name, model=model)
    
    async def run(self, task: str, user_id: Optional[str] = None) -> str:
        """Run the agent with a task."""
        return await super().run(task, user_id=user_id)


# ============================================================================
# AGENT FACTORY
# ============================================================================

def create_agent(
    name: str,
    model: str = "openai",
    max_steps: int = None,
    system_prompt: str = None
) -> BaseAgent:
    """
    Factory function to create an agent.
    
    Args:
        name: Agent name
        model: Model to use
        max_steps: Maximum steps
        system_prompt: Custom system prompt
    
    Returns:
        Configured BaseAgent instance
    """
    return BaseAgent(
        name=name,
        model=model,
        max_steps=max_steps,
        system_prompt=system_prompt
    )


def create_simple_agent(model: str = "openai") -> SimpleAgent:
    """Create a simple agent for quick tasks."""
    return SimpleAgent(name="DenLab Agent", model=model)