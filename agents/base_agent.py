"""
Base Agent with proper final response and Pollinations retry support.
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


class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Any = None
    status: str = "pending"
    duration_ms: float = 0.0
    
    @classmethod
    def from_openai_format(cls, data: Dict) -> "ToolCall":
        func_data = data.get("function", {})
        args_str = func_data.get("arguments", "{}")
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError:
            args = {}
        return cls(
            id=data.get("id", ""),
            name=func_data.get("name", ""),
            arguments=args,
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
    step: int
    thought: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class BaseAgent:
    """Base agent with guaranteed response output."""
    
    def __init__(self, name: str = "BaseAgent", model: str = "openai", max_steps: int = None,
                 system_prompt: str = None, timeout_seconds: int = 90):
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
        self.on_step: Optional[Callable] = None
        self.on_tool_call: Optional[Callable] = None
    
    def _get_client(self):
        if self._client is None:
            self._client = get_client()
        return self._client
    
    def _generate_with_retry(self, messages: List[Dict], tools: List[Dict] = None, 
                             user_id: str = None, max_retries: int = 3) -> Dict:
        """Generate with retry for Pollinations 502 errors."""
        for attempt in range(max_retries):
            try:
                response = self._get_client().generate(
                    messages=messages, model=self.model, temperature=0.7,
                    tools=tools, user_id=user_id
                )
                if response.get("content") or response.get("tool_calls"):
                    return response
                if attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                return {"content": f"Error after {max_retries} attempts: {str(e)}", "tool_calls": None}
        
        return {"content": "Unable to generate response. Please try again.", "tool_calls": None}
    
    def _build_system_prompt(self) -> str:
        base = self.system_prompt
        tools_meta = self._tool_registry.get_tools_metadata()
        if tools_meta:
            base += "\n\nYou have access to these tools:\n"
            for name, info in tools_meta.items():
                base += f"- **{name}**: {info.get('description', 'No description')}\n"
            base += "\nUse tools when they would help. Always provide complete, detailed answers."
        return base
    
    async def run(self, task: str, context: Optional[str] = None,
                  user_id: Optional[str] = None) -> str:
        """Execute agent loop with guaranteed final output."""
        self.state = AgentState.PLANNING
        self.step_count = 0
        self.traces = []
        
        user_prompt = f"## Task\n{task}\n"
        if context:
            user_prompt += f"\n## Context\n{context}\n"
        user_prompt += "\nWork through this step by step. Use tools if helpful. Always finish with a complete answer."
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]
        
        last_content = ""
        
        try:
            while self.step_count < self.max_steps:
                self.step_count += 1
                self.state = AgentState.EXECUTING
                
                tools = self._tool_registry.get_tool_schema() if self._tool_registry.get_tools_count() > 0 else None
                response = self._generate_with_retry(messages, tools=tools, user_id=user_id)
                
                content = response.get("content") or ""
                tool_calls_raw = response.get("tool_calls") or []
                
                if content:
                    last_content = content
                
                # No tool calls = final answer
                if not tool_calls_raw:
                    self.state = AgentState.COMPLETE
                    final = content if content and len(content) > 20 else last_content
                    if not final or len(final) < 10:
                        # Force final answer
                        messages.append({"role": "user", "content": "Please provide your complete final answer to the task."})
                        forced = self._generate_with_retry(messages, tools=None, user_id=user_id)
                        final = forced.get("content", "Task completed.")
                    self.traces.append(AgentTrace(step=self.step_count, thought=final[:200]))
                    return final
                
                # Process tool calls
                trace = AgentTrace(step=self.step_count, 
                                 thought=content[:300] if content else f"Using {len(tool_calls_raw)} tool(s)")
                
                for tc_raw in tool_calls_raw:
                    tc = ToolCall.from_openai_format(tc_raw)
                    
                    if self.on_tool_call:
                        self.on_tool_call(tc)
                    
                    try:
                        result = self._tool_registry.execute(tc.name, **tc.arguments)
                        tc.result = str(result)[:4000]
                        tc.status = "success"
                    except Exception as e:
                        tc.result = f"Error: {str(e)}"
                        tc.status = "error"
                    
                    trace.tool_calls.append(tc)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": tc.result})
                
                self.traces.append(trace)
                if self.on_step:
                    self.on_step(trace)
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": content or "Using tools...",
                    "tool_calls": [tc.to_openai_format() for tc in trace.tool_calls]
                })
                
                # Get follow-up after tools
                follow = self._generate_with_retry(messages, user_id=user_id)
                follow_content = follow.get("content") or ""
                
                if follow_content:
                    messages.append({"role": "assistant", "content": follow_content})
                    last_content = follow_content
                    
                    # Check if final
                    if len(follow_content) > 100:
                        self.state = AgentState.COMPLETE
                        self.traces.append(AgentTrace(step=self.step_count + 0.5, thought=follow_content[:200]))
                        return follow_content
            
            # Max steps - synthesize final
            messages.append({"role": "user", "content": "You've reached the maximum steps. Provide your best answer based on everything above."})
            final = self._generate_with_retry(messages, tools=None, user_id=user_id)
            return final.get("content", last_content or "Task completed after maximum steps.")
            
        except Exception as e:
            return f"Agent error: {str(e)}"


def create_simple_agent(model: str = "openai", max_steps: int = None,
                        system_prompt: str = None) -> BaseAgent:
    return BaseAgent(name="SimpleAgent", model=model, max_steps=max_steps, system_prompt=system_prompt)


__all__ = ["BaseAgent", "create_simple_agent", "AgentState", "ToolCall", "AgentTrace"]