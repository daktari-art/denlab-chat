"""
Base Agent with proper final response generation.
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
    PAUSED = "paused"


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
    step: int
    thought: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class BaseAgent:
    """Base agent with proper final response generation."""
    
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
        self.on_step: Optional[Callable] = None
        self.on_tool_call: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None
    
    def _get_client(self):
        if self._client is None:
            self._client = get_client()
        return self._client
    
    async def _llm_call(self, messages: List[Dict], tools: List[Dict] = None,
                        user_id: Optional[str] = None) -> Dict:
        """Call LLM with timeout."""
        try:
            response = await asyncio.wait_for(
                self._async_generate(messages, tools, user_id),
                timeout=self.timeout_seconds
            )
            return response
        except asyncio.TimeoutError:
            return {"content": "Timed out. Please try a simpler request.", "tool_calls": []}
    
    async def _async_generate(self, messages: List[Dict], tools: List[Dict] = None,
                              user_id: Optional[str] = None) -> Dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._get_client().generate(
                messages=messages, model=self.model, temperature=0.7,
                tools=tools, user_id=user_id
            )
        )
    
    def _build_system_prompt(self) -> str:
        base = self.system_prompt
        if self._tool_registry and self._tool_registry.get_tools_count() > 0:
            base += "\n\nAvailable tools:\n"
            metadata = self._tool_registry.get_tools_metadata()
            for name, info in metadata.items():
                base += f"- {name}: {info.get('description', 'No description')}\n"
        base += f"\nMaximum steps: {self.max_steps}. Provide complete answers."
        return base
    
    async def run(self, task: str, context: Optional[str] = None,
                  user_id: Optional[str] = None) -> str:
        """Execute the agent loop with guaranteed final response."""
        self.state = AgentState.PLANNING
        self.step_count = 0
        self.traces = []
        
        user_prompt = f"Task: {task}\n"
        if context:
            user_prompt += f"\nContext:\n{context}\n"
        user_prompt += "\nWork step by step. Use tools when helpful. Always provide a complete final answer."
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            while self.step_count < self.max_steps:
                self.step_count += 1
                self.state = AgentState.EXECUTING
                
                tools = self._tool_registry.get_tool_schema() if self._tool_registry.get_tools_count() > 0 else None
                response = await self._llm_call(messages, tools=tools, user_id=user_id)
                
                content = response.get("content") or ""
                tool_calls_raw = response.get("tool_calls") or []
                
                # If no tool calls, generate final answer
                if not tool_calls_raw:
                    self.state = AgentState.COMPLETE
                    
                    # If content is empty, make one more call for a proper response
                    if not content or len(content) < 20:
                        messages.append({"role": "user", "content": "Please provide your complete final answer to the original task."})
                        final_resp = await self._llm_call(messages, tools=None, user_id=user_id)
                        content = final_resp.get("content") or "Task completed."
                    
                    self.traces.append(AgentTrace(step=self.step_count, thought=content[:200], tool_calls=[]))
                    return content
                
                # Process tool calls
                trace = AgentTrace(step=self.step_count, thought=content[:500] if content else f"Using {len(tool_calls_raw)} tool(s)...")
                
                tool_calls = []
                for tc_raw in tool_calls_raw:
                    tc = ToolCall.from_openai_format(tc_raw)
                    
                    if self.on_tool_call:
                        self.on_tool_call(tc)
                    
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
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(tc.result)[:4000]
                    })
                
                trace.tool_calls = tool_calls
                self.traces.append(trace)
                
                if self.on_step:
                    self.on_step(trace)
                
                messages.append({
                    "role": "assistant",
                    "content": content or "Using tools...",
                    "tool_calls": [tc.to_openai_format() for tc in tool_calls]
                })
                
                # Get follow-up after tool use
                follow_up = await self._llm_call(messages, user_id=user_id)
                follow_content = follow_up.get("content") or ""
                
                if follow_content and len(follow_content) > 50:
                    messages.append({"role": "assistant", "content": follow_content})
                    
                    # Check if this is a final answer
                    if len(follow_content) > 100 or any(word in follow_content.lower() for word in 
                          ["final", "answer", "result", "conclusion", "summary", "completed"]):
                        self.state = AgentState.COMPLETE
                        self.traces.append(AgentTrace(step=self.step_count + 0.5, thought=follow_content[:200], tool_calls=[]))
                        return follow_content
            
            # Max steps reached - force final answer
            self.state = AgentState.ERROR
            messages.append({"role": "user", "content": "You've reached the maximum steps. Provide your best answer now based on what you've found."})
            final_resp = await self._llm_call(messages, tools=None, user_id=user_id)
            return final_resp.get("content", "Maximum steps reached. Could not complete the task.")
            
        except Exception as e:
            self.state = AgentState.ERROR
            return f"Agent error: {str(e)}. Please try again with a different approach."


def create_simple_agent(model: str = "openai", max_steps: int = None,
                        system_prompt: str = None) -> BaseAgent:
    return BaseAgent(name="SimpleAgent", model=model, max_steps=max_steps, system_prompt=system_prompt)


__all__ = ["BaseAgent", "create_simple_agent", "AgentState", "ToolCall", "AgentTrace"]