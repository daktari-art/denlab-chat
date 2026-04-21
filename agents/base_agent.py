"""Base agent with autonomous tool-use loop."""
import json
import uuid
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable

class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_TOOL = "waiting_tool"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    status: str = "pending"
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    
    def to_dict(self):
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
    observation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

class BaseAgent(ABC):
    """Autonomous agent with tool-use capabilities."""
    
    def __init__(self, name: str, model: str = "openai", max_steps: int = 25):
        self.name = name
        self.model = model
        self.max_steps = max_steps
        self.state = AgentState.IDLE
        self.traces: List[AgentTrace] = []
        self.memory: Dict[str, Any] = {}
        self.tool_registry: Dict[str, Dict] = {}
        self.step_count = 0
        self.on_step: Optional[Callable[[AgentTrace], None]] = None
        
    def register_tool(self, name: str, func: Callable, description: str, params: Dict):
        """Register an available tool."""
        self.tool_registry[name] = {
            "func": func,
            "description": description,
            "params": params
        }
    
    def get_tool_schema(self) -> List[Dict]:
        """Get OpenAI-compatible tool schema."""
        tools = []
        for name, meta in self.tool_registry.items():
            properties = {}
            required = []
            for param_name, param_info in meta["params"].items():
                properties[param_name] = {
                    "type": param_info.get("type", "string"),
                    "description": param_info.get("description", "")
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
    
    async def run(self, task: str, context: Optional[str] = None) -> str:
        """Execute autonomous loop."""
        self.state = AgentState.PLANNING
        self.step_count = 0
        self.traces = []
        
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": f"Task: {task}\n\nContext: {context or 'No additional context'}"}
        ]
        
        try:
            while self.step_count < self.max_steps:
                self.step_count += 1
                
                # Get LLM response
                response = await self._llm_call(messages, tools=self.get_tool_schema())
                
                if response.get("tool_calls"):
                    self.state = AgentState.EXECUTING
                    trace = AgentTrace(step=self.step_count, thought=response.get("content", ""))
                    
                    # Execute all tool calls
                    tool_results = []
                    for tc_data in response["tool_calls"]:
                        tc = await self._execute_tool(tc_data)
                        trace.tool_calls.append(tc)
                        tool_results.append({
                            "tool_call_id": tc.id,
                            "role": "tool",
                            "content": str(tc.result)[:4000]  # Limit result size
                        })
                    
                    self.traces.append(trace)
                    if self.on_step:
                        self.on_step(trace)
                    
                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": response.get("content", ""),
                        "tool_calls": [tc.to_dict() for tc in trace.tool_calls]
                    })
                    
                    # Add tool results
                    for result in tool_results:
                        messages.append(result)
                else:
                    # Final answer
                    self.state = AgentState.COMPLETE
                    return response.get("content", "Task completed.")
            
            self.state = AgentState.ERROR
            return "Maximum steps reached. Task may be incomplete."
            
        except Exception as e:
            self.state = AgentState.ERROR
            return f"Agent error: {str(e)}"
    
    async def _execute_tool(self, tool_call_data: Dict) -> ToolCall:
        """Execute a single tool."""
        tc = ToolCall(
            id=tool_call_data.get("id", str(uuid.uuid4())),
            name=tool_call_data["function"]["name"],
            arguments=json.loads(tool_call_data["function"]["arguments"])
        )
        
        if tc.name not in self.tool_registry:
            tc.result = f"Error: Tool '{tc.name}' not found"
            tc.status = "error"
            return tc
        
        try:
            tc.status = "running"
            start = datetime.now()
            
            func = self.tool_registry[tc.name]["func"]
            if asyncio.iscoroutinefunction(func):
                result = await func(**tc.arguments)
            else:
                result = func(**tc.arguments)
            
            tc.duration_ms = (datetime.now() - start).total_seconds() * 1000
            tc.result = result
            tc.status = "success"
        except Exception as e:
            tc.result = f"Error: {str(e)}"
            tc.status = "error"
        
        return tc
    
    @abstractmethod
    async def _llm_call(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Call LLM API - implement in subclass."""
        pass
    
    def _get_system_prompt(self) -> str:
        return f"""You are {self.name}, an autonomous AI agent with tool-use capabilities.

Rules:
1. Think step-by-step about the task
2. Use tools when you need external data or actions
3. Always verify facts with search before stating them
4. If a tool fails, try an alternative approach
5. Provide concise, actionable final answers
6. You have {self.max_steps} maximum steps - use them wisely

Available tools: {', '.join(self.tool_registry.keys())}"""
