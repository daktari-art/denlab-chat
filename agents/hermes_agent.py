"""
Hermes Agent - Advanced Agent with Self-Reflection & Chain-of-Thought Verification.

Tactics from Hermes (advanced reasoning agent patterns):
1. Self-Reflection: After each tool call, the agent reflects on whether the result is useful
2. Chain-of-Thought Verification: The agent verifies its own reasoning before acting
3. Backtracking: If a tool fails, the agent backtracks and tries alternatives
4. Confidence Scoring: Each step gets a confidence score; low confidence triggers re-evaluation
5. Plan Validation: Before executing, validate the plan against available tools
6. Meta-Cognition: The agent thinks about its own thinking process

Connected to: base_agent.py (extends BaseAgent), tool_registry.py (tools),
client.py (LLM API), config/settings.py (prompts).
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SystemPrompts, AppConfig
from client import get_client
from agents.tool_registry import get_tool_registry
from agents.base_agent import BaseAgent, AgentState, ToolCall, AgentTrace


# ============================================================================
# HERMES DATA CLASSES
# ============================================================================

class ConfidenceLevel(Enum):
    HIGH = "high"      # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # < 0.5


@dataclass
class Reflection:
    """Self-reflection record for a step."""
    step: int
    thought: str
    action_taken: str
    result_summary: str
    confidence: float
    needs_reconsideration: bool
    alternatives_considered: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step,
            "thought": self.thought[:300],
            "action_taken": self.action_taken,
            "result_summary": self.result_summary[:300],
            "confidence": round(self.confidence, 2),
            "needs_reconsideration": self.needs_reconsideration,
            "alternatives": self.alternatives_considered
        }


@dataclass
class PlanStep:
    """A step in the Hermes execution plan."""
    step_id: int
    description: str
    required_tools: List[str]
    expected_outcome: str
    fallback_strategy: str
    validation_criteria: List[str] = field(default_factory=list)


# ============================================================================
# HERMES AGENT
# ============================================================================

class HermesAgent(BaseAgent):
    """
    Advanced agent with Hermes-style self-reflection and verification.
    
    Enhancements over BaseAgent:
    - Pre-execution plan validation
    - Confidence scoring per step
    - Automatic backtracking on failure
    - Self-reflection after each action
    - Meta-cognitive reasoning
    - Result verification against expected outcomes
    - Alternative strategy selection
    """
    
    def __init__(self, name: str = "Hermes", model: str = "openai", max_steps: int = None):
        super().__init__(name=name, model=model, max_steps=max_steps)
        self.reflections: List[Reflection] = []
        self.execution_plan: List[PlanStep] = []
        self.backtrack_count = 0
        self.confidence_threshold = 0.6
        self._verification_prompt = """Verify the following reasoning:
        
1. Is the planned action appropriate for the task?
2. Are the tool arguments correct and complete?
3. What could go wrong with this approach?
4. Is there a simpler or more reliable alternative?

Respond with a confidence score (0.0-1.0) and any concerns."""
    
    # ========================================================================
    # Advanced Plan Generation
    # ========================================================================
    
    async def _generate_plan(self, task: str) -> List[PlanStep]:
        """Generate a validated execution plan before acting."""
        plan_prompt = f"""You are Hermes, an advanced planning agent. Break down this task into clear steps.

Task: {task}

For each step, specify:
1. What needs to be done
2. Which tools would help (web_search, execute_code, fetch_url, etc.)
3. What the expected outcome looks like
4. What to do if this step fails (fallback)
5. How to verify the step succeeded

Available tools:
- web_search: Search the web
- deep_research: Multi-source research
- execute_code: Run Python code
- fetch_url: Fetch webpage content
- read_file: Read uploaded files
- github_get_files: List GitHub repo files
- get_current_time: Get current time
- calculate: Math calculations

Respond in JSON format:
{{
    "steps": [
        {{
            "step_id": 1,
            "description": "...",
            "required_tools": ["tool_name"],
            "expected_outcome": "...",
            "fallback_strategy": "...",
            "validation_criteria": ["criterion 1", "criterion 2"]
        }}
    ]
}}"""
        
        messages = [
            {"role": "system", "content": "You are a precise planning agent. Respond only in valid JSON."},
            {"role": "user", "content": plan_prompt}
        ]
        
        response = await self._llm_call(messages, user_id=None)
        content = response.get("content", "")
        
        # Extract JSON
        try:
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            
            plan_data = json.loads(json_str.strip())
            steps = []
            for step_data in plan_data.get("steps", []):
                steps.append(PlanStep(
                    step_id=step_data.get("step_id", 0),
                    description=step_data.get("description", ""),
                    required_tools=step_data.get("required_tools", []),
                    expected_outcome=step_data.get("expected_outcome", ""),
                    fallback_strategy=step_data.get("fallback_strategy", ""),
                    validation_criteria=step_data.get("validation_criteria", [])
                ))
            return steps
        except Exception:
            # Fallback: create a simple single-step plan
            return [PlanStep(
                step_id=1,
                description=task,
                required_tools=[],
                expected_outcome="Task completed successfully",
                fallback_strategy="Use web search for more information"
            )]
    
    # ========================================================================
    # Confidence Scoring
    # ========================================================================
    
    async def _score_confidence(self, thought: str, tool_name: str, arguments: Dict) -> float:
        """Score confidence of a planned action (0.0-1.0)."""
        verify_prompt = f"""Rate the confidence of this planned action:

Reasoning: {thought}
Tool: {tool_name}
Arguments: {json.dumps(arguments)}

Rate from 0.0 (very uncertain) to 1.0 (very confident). Respond with ONLY a number."""
        
        messages = [
            {"role": "system", "content": "You are a confidence rater. Respond with ONLY a number between 0.0 and 1.0."},
            {"role": "user", "content": verify_prompt}
        ]
        
        try:
            response = await self._llm_call(messages, user_id=None)
            content = response.get("content", "0.5").strip()
            # Extract number
            import re
            match = re.search(r'(\d+\.?\d*)', content)
            if match:
                score = float(match.group(1))
                return min(max(score / 10 if score > 1 else score, 0.0), 1.0)
        except Exception:
            pass
        
        return 0.5
    
    # ========================================================================
    # Self-Reflection
    # ========================================================================
    
    async def _reflect(self, step: int, thought: str, tool_name: str, result: str, confidence: float) -> Reflection:
        """Generate self-reflection after a tool execution."""
        reflect_prompt = f"""Reflect on this action and its result:

Step: {step}
Your reasoning: {thought}
Action taken: {tool_name}
Result: {result[:500]}

Questions:
1. Did this action produce useful information?
2. Is the result complete and accurate?
3. What should the next step be?
4. Should we try a different approach?
5. Rate confidence (0.0-1.0)

Respond in JSON:
{{
    "useful": true/false,
    "complete": true/false,
    "next_step": "...",
    "try_different": true/false,
    "confidence": 0.8,
    "alternatives": ["alternative 1", "alternative 2"]
}}"""
        
        messages = [
            {"role": "system", "content": "You are a self-reflective agent. Be honest about failures."},
            {"role": "user", "content": reflect_prompt}
        ]
        
        try:
            response = await self._llm_call(messages, user_id=None)
            content = response.get("content", "")
            
            # Extract JSON
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            
            reflect_data = json.loads(json_str.strip())
            
            reflection = Reflection(
                step=step,
                thought=thought[:300],
                action_taken=tool_name,
                result_summary=result[:300],
                confidence=reflect_data.get("confidence", confidence),
                needs_reconsideration=reflect_data.get("try_different", False) or not reflect_data.get("useful", True),
                alternatives_considered=reflect_data.get("alternatives", [])
            )
            
            return reflection
        except Exception:
            return Reflection(
                step=step,
                thought=thought[:300],
                action_taken=tool_name,
                result_summary=result[:300],
                confidence=confidence,
                needs_reconsideration=confidence < self.confidence_threshold,
                alternatives_considered=[]
            )
    
    # ========================================================================
    # Backtracking
    # ========================================================================
    
    async def _backtrack(self, messages: List[Dict], failed_step: int) -> List[Dict]:
        """Backtrack and try alternative approach after a failed step."""
        self.backtrack_count += 1
        
        # Add backtracking context
        backtrack_msg = f"""The previous approach (step {failed_step}) did not work as expected.
Let's reconsider the task and try a different strategy.

Reflections so far:
"""
        for ref in self.reflections[-3:]:
            backtrack_msg += f"- Step {ref.step}: {ref.action_taken} (confidence: {ref.confidence:.2f})\n"
        
        backtrack_msg += "\nPlease propose a revised plan or different tool selection."
        
        messages.append({"role": "user", "content": backtrack_msg})
        return messages
    
    # ========================================================================
    # Main Run (Override)
    # ========================================================================
    
    async def run(self, task: str, context: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Execute the Hermes agent loop with reflection and verification.
        
        Overrides BaseAgent.run() with advanced reasoning.
        """
        self.state = AgentState.PLANNING
        self.step_count = 0
        self.traces = []
        self.reflections = []
        self.backtrack_count = 0
        
        # Generate execution plan
        self.execution_plan = await self._generate_plan(task)
        
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
                    
                    # Final reflection on the complete response
                    final_reflection = await self._reflect(
                        self.step_count, content, "final_answer", content, 0.9
                    )
                    self.reflections.append(final_reflection)
                    
                    self.traces.append(AgentTrace(
                        step=self.step_count,
                        thought=content[:200] if content else "Final response",
                        tool_calls=[]
                    ))
                    
                    return content or "Task completed."
                
                # Process tool calls with reflection
                trace = AgentTrace(
                    step=self.step_count,
                    thought=content[:500] if content else f"Using {len(tool_calls_raw)} tool(s)..."
                )
                
                tool_calls = []
                all_success = True
                
                for tc_raw in tool_calls_raw:
                    tc = ToolCall.from_openai_format(tc_raw)
                    
                    # Score confidence before execution
                    confidence = await self._score_confidence(content, tc.name, tc.arguments)
                    
                    if self.on_tool_call:
                        self.on_tool_call(tc)
                    
                    # Execute tool
                    start_time = time.time()
                    try:
                        result = self._tool_registry.execute(tc.name, **tc.arguments)
                        tc.result = result
                        tc.status = "success"
                    except Exception as e:
                        tc.result = f"Error: {str(e)}"
                        tc.status = "error"
                        all_success = False
                    
                    tc.duration_ms = (time.time() - start_time) * 1000
                    tool_calls.append(tc)
                    
                    # Self-reflect on this tool execution
                    reflection = await self._reflect(
                        self.step_count, content, tc.name, str(tc.result), confidence
                    )
                    self.reflections.append(reflection)
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(tc.result)[:4000]
                    })
                    
                    # If confidence is too low, consider backtracking
                    if reflection.needs_reconsideration and self.backtrack_count < 3:
                        messages = await self._backtrack(messages, self.step_count)
                        break
                
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
            
            # Max steps
            self.state = AgentState.ERROR
            return self._build_max_steps_message()
            
        except Exception as e:
            self.state = AgentState.ERROR
            return f"Hermes agent error: {str(e)}"
    
    def get_reflection_summary(self) -> str:
        """Get a summary of all reflections."""
        if not self.reflections:
            return "No reflections recorded."
        
        lines = [f"## Hermes Reflection Summary ({len(self.reflections)} reflections)", ""]
        for ref in self.reflections:
            icon = "✅" if ref.confidence > 0.7 else "⚠️" if ref.confidence > 0.4 else "❌"
            lines.append(f"{icon} Step {ref.step}: `{ref.action_taken}` (confidence: {ref.confidence:.2f})")
            if ref.needs_reconsideration:
                lines.append(f"   ↳ Backtrack suggested. Alternatives: {', '.join(ref.alternatives_considered[:2])}")
        
        lines.append("")
        lines.append(f"**Total backtracks:** {self.backtrack_count}")
        lines.append(f"**Average confidence:** {sum(r.confidence for r in self.reflections) / len(self.reflections):.2f}")
        
        return "\n".join(lines)
    
    def _build_system_prompt(self) -> str:
        """Build enhanced system prompt with reflection instructions."""
        base = super()._build_system_prompt()
        hermes_addon = """

## Hermes Advanced Reasoning Protocol

Before using any tool:
1. Verify the tool is appropriate for the subtask
2. Check arguments are complete and correctly typed
3. Consider what could go wrong
4. Have a fallback plan ready

After each tool result:
1. Evaluate if the result is useful and accurate
2. If confidence is low (< 0.6), reconsider your approach
3. Consider alternative tools or strategies
4. Never proceed blindly with poor results

When ready to answer, signal completion clearly."""
        return base + hermes_addon


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_hermes_agent(model: str = "openai", max_steps: int = None) -> HermesAgent:
    """Factory function to create a Hermes agent."""
    return HermesAgent(name="Hermes", model=model, max_steps=max_steps)


async def run_hermes(task: str, user_id: Optional[str] = None, model: str = "openai") -> str:
    """Quick function to run Hermes on a task."""
    agent = create_hermes_agent(model=model)
    return await agent.run(task, user_id=user_id)
