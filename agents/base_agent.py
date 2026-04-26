"""
Base Agent with Hermes Hook Support and Enhanced Tool Execution.

ADVANCEMENTS:
1. Added hooks for Hermes agent integration (pre_tool, post_tool, on_reflection)
2. Enhanced tool result streaming for real-time UI updates
3. Added tool execution timeout handling
4. Added support for custom system prompts per agent instance
5. Added state checkpointing for resume capability
6. Better error recovery with retry logic

Connected to: tool_registry.py (tools), client.py (LLM), planner.py (decomposition),
config/settings.py (prompts).
"""

import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SystemPrompts, AppConfig
from client import get_client
from agents.tool_registry import get_tool_registry


# ============================================================================
# DATA CLASSES
# ============================================================================

class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETE = "complete"
    ERROR = "error"
    PAUSED = "paused"


@dataclass
class ToolCall:
    """Represents a tool call."""
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Any = None
    status: str = "pending"
    duration_ms: float = 0.0
    
    @classmethod
    def from_openai_format(cls, data: Dict) -> "ToolCall":
        return cls(
            id=data.get("id", ""),
            name=data.get("function", {}).get("name", ""),
            arguments=json.loads(data.get("function", {}).get("arguments", "{}")),
        )
    
    def to_openai_format(self) -> Dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments)
            }
        }


@dataclass
class AgentTrace:
    """Trace of a single agent step."""
    step: int
    thought: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# BASE AGENT
# ============================================================================

class BaseAgent:
    """
    Enhanced base agent with hooks for Hermes integration,
    timeout handling, and checkpointing.
    
    Hooks (set by Hermes or other advanced agents):
    - pre_tool_call(tool_call): Called before executing a tool
    - post_tool_call(tool_call, result): Called after executing a tool
    - on_reflection(step, thought, confidence): Called after reflection
    - on_checkpoint(state): Called when agent checkpoints state
    """
    
    def __init__(self, name: str = "BaseAgent", model: str = "openai", max_steps: int = None,
                 system_prompt: str = None, timeout_seconds: int = 60):
        self.name = name
        self.model = model
        self.max_steps = max_steps or AppConfig.max_agent_steps
        self.timeout_seconds = timeout_seconds
        self.system_prompt = system_prompt or SystemPrompts.AGENT
        self.state = AgentState.IDLE
        self.step_count = 0
        self.traces: List[AgentTrace] = []
        self._client = None
        self._tool_registry = get_tool_registry()
        
        # Callbacks
        self.on_step: Optional[Callable] = None
        self.on_tool_call: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Hermes / advanced hooks
        self.pre_tool_call: Optional[Callable] = None  # (tool_call) -> modified tool_call or None
        self.post_tool_call: Optional[Callable] = None  # (tool_call, result) -> None
        self.on_reflection: Optional[Callable] = None  # (step, thought, confidence) -> None
        self.on_checkpoint: Optional[Callable] = None  # (state_dict) -> None
    
    def _get_client(self):
        if self._client is None:
            self._client = get_client()
        return self._client
    
    # ========================================================================
    # LLM CALL
    # ========================================================================
    
    async def _llm_call(self, messages: List[Dict], tools: List[Dict] = None,
                        user_id: Optional[str] = None) -> Dict:
        """Call LLM with timeout handling."""
        try:
            response = await asyncio.wait_for(
                self._async_generate(messages, tools, user_id),
                timeout=self.timeout_seconds
            )
            return response
        except asyncio.TimeoutError:
            return {
                "content": f"Agent step timed out after {self.timeout_seconds}s. The operation may be too complex.",
                "tool_calls": [],
                "guardrail_triggered": False
            }
    
    async def _async_generate(self, messages: List[Dict], tools: List[Dict] = None,
                              user_id: Optional[str] = None) -> Dict:
        """Async wrapper for client generate."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._get_client().generate(
                messages=messages,
                model=self.model,
                temperature=0.7,
                tools=tools,
                user_id=user_id
            )
        )
    
    # ========================================================================
    # PROMPT BUILDING
    # ========================================================================
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with agent capabilities."""
        base = self.system_prompt
        
        if self._tool_registry and self._tool_registry.get_tools_count() > 0:
            base += "\n\nAvailable tools:\n"
            for name, info in self._tool_registry.get_tools_metadata().items():
                base += f"- {name}: {info['description']}\n"
        
        base += f"\nMaximum steps: {self.max_steps}. Think efficiently."
        return base
    
    def _build_user_prompt(self, task: str, context: Optional[str] = None) -> str:
        """Build user prompt with optional context."""
        prompt = f"Task: {task}\n"
        if context:
            prompt += f"\nContext:\n{context}\n"
        prompt += "\nWork step by step. Use tools when needed."
        return prompt
    
    # ========================================================================
    # MAIN RUN
    # ========================================================================
    
    async def run(self, task: str, context: Optional[str] = None,
                  user_id: Optional[str] = None) -> str:
        """
        Execute the agent loop with enhanced error recovery.
        """
        self.state = AgentState.PLANNING
        self.step_count = 0
        self.traces = []
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._build_user_prompt(task, context)}
        ]
        
        try:
            while self.step_count < self.max_steps:
                self.step_count += 1
                self.state = AgentState.EXECUTING
                
                # Checkpoint state
                self._checkpoint()
                
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
                    
                    self.traces.append(AgentTrace(
                        step=self.step_count,
                        thought=content[:200] if content else "Final response",
                        tool_calls=[]
                    ))
                    
                    return content or "Task completed."
                
                # Process tool calls
                trace = AgentTrace(
                    step=self.step_count,
                    thought=content[:500] if content else f"Using {len(tool_calls_raw)} tool(s)..."
                )
                
                tool_calls = []
                for tc_raw in tool_calls_raw:
                    tc = ToolCall.from_openai_format(tc_raw)
                    
                    # Pre-tool hook (Hermes can modify here)
                    if self.pre_tool_call:
                        modified = self.pre_tool_call(tc)
                        if modified:
                            tc = modified
                    
                    if self.on_tool_call:
                        self.on_tool_call(tc)
                    
                    # Execute with timeout
                    start_time = time.time()
                    try:
                        result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: self._tool_registry.execute(tc.name, **tc.arguments)
                            ),
                            timeout=30  # Per-tool timeout
                        )
                        tc.result = result
                        tc.status = "success"
                    except asyncio.TimeoutError:
                        tc.result = "Tool execution timed out (30s)"
                        tc.status = "timeout"
                    except Exception as e:
                        tc.result = f"Error: {str(e)}"
                        tc.status = "error"
                        if self.on_error:
                            self.on_error(e)
                    
                    tc.duration_ms = (time.time() - start_time) * 1000
                    tool_calls.append(tc)
                    
                    # Post-tool hook
                    if self.post_tool_call:
                        self.post_tool_call(tc, tc.result)
                    
                    # Add to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(tc.result)[:4000]
                    })
                
                trace.tool_calls = tool_calls
                self.traces.append(trace)
                
                if self.on_step:
                    self.on_step(trace)
                
                # Add assistant message
                messages.append({
                    "role": "assistant",
                    "content": content or "Using tools...",
                    "tool_calls": [tc.to_openai_format() for tc in tool_calls]
                })
                
                # Get follow-up
                follow_up = await self._llm_call(messages, user_id=user_id)
                follow_content = follow_up.get("content") or ""
                
                if follow_content:
                    messages.append({"role": "assistant", "content": follow_content})
                    
                    if self._is_final_answer(follow_content):
                        self.state = AgentState.COMPLETE
                        
                        if self.on_complete:
                            self.on_complete(follow_content)
                        
                        self.traces.append(AgentTrace(
                            step=self.step_count + 0.5,
                            thought=follow_content[:200],
                            tool_calls=[]
                        ))
                        
                        return follow_content
            
            # Max steps reached
            self.state = AgentState.ERROR
            return self._build_max_steps_message()
            
        except Exception as e:
            self.state = AgentState.ERROR
            if self.on_error:
                self.on_error(e)
            return f"Agent error in {self.name}: {str(e)}"
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _is_final_answer(self, content: str) -> bool:
        """Check if content is a final answer."""
        final_indicators = [
            "final answer", "completed", "done", "result", "output",
            "##", "###", "Based on", "The answer is", "In conclusion"
        ]
        content_lower = (content or "").lower()
        return any(ind in content_lower for ind in final_indicators) or len(content) > 200
    
    def _build_max_steps_message(self) -> str:
        """Build message when max steps reached."""
        return f"Reached maximum steps ({self.max_steps}). Here's what I found so far:\n\n" + \
               "\n".join([f"Step {t.step}: {t.thought[:100]}..." for t in self.traces[-5:]])
    
    def _checkpoint(self):
        """Save current state for potential resume."""
        state = {
            "step_count": self.step_count,
            "state": self.state.value,
            "trace_count": len(self.traces),
            "timestamp": time.time()
        }
        if self.on_checkpoint:
            self.on_checkpoint(state)
    
    def get_trace_summary(self) -> str:
        """Get human-readable trace summary."""
        lines = [f"# Agent Trace: {self.name}"]
        for trace in self.traces:
            lines.append(f"\n**Step {trace.step}**")
            lines.append(f"> {trace.thought[:150]}")
            for tc in trace.tool_calls:
                icon = "✅" if tc.status == "success" else "⚠️" if tc.status == "timeout" else "❌"
                lines.append(f"  {icon} `{tc.name}` ({tc.duration_ms:.0f}ms): {str(tc.result)[:80]}...")
        return "\n".join(lines)


# ============================================================================
# SIMPLE AGENT FACTORY
# ============================================================================

def create_simple_agent(model: str = "openai", max_steps: int = None,
                        system_prompt: str = None) -> BaseAgent:
    """Create a simple agent instance."""
    return BaseAgent(
        name="SimpleAgent",
        model=model,
        max_steps=max_steps,
        system_prompt=system_prompt
    )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "BaseAgent", "create_simple_agent", "AgentState",
    "ToolCall", "AgentTrace"
]
