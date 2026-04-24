"""
Swarm Orchestrator for DenLab Chat.
Master agent delegates to specialized sub-agents, executes tasks in parallel,
then synthesizes results into a coherent final response.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
from dataclasses import dataclass, field

# Import from completed files
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SystemPrompts, Constants, AppConfig
from client import get_client, MultiProviderClient
from agents.base_agent import BaseAgent, SimpleAgent, AgentTrace
from agents.planner import TaskPlanner, ExecutionPlan, PlanStep, AgentType, get_planner
from agents.tool_registry import get_tool_registry


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SubTaskResult:
    """Result of a sub-task execution."""
    step_id: str
    description: str
    agent_type: str
    result: str
    status: str  # pending, running, complete, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "step_id": self.step_id,
            "description": self.description[:200],
            "agent_type": self.agent_type,
            "result": self.result[:1000] if self.result else None,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error": self.error[:200] if self.error else None
        }


@dataclass
class SwarmExecutionResult:
    """Complete result of a swarm execution."""
    task: str
    status: str  # pending, running, complete, failed
    subtasks: Dict[str, SubTaskResult]
    synthesis: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_ms: float = 0.0
    plan: Optional[ExecutionPlan] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "task": self.task[:200],
            "status": self.status,
            "subtasks": {k: v.to_dict() for k, v in self.subtasks.items()},
            "synthesis": self.synthesis[:2000] if self.synthesis else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the execution."""
        lines = [
            f"## Swarm Execution Summary",
            f"**Task:** {self.task[:100]}",
            f"**Status:** {self.status}",
            f"**Duration:** {self.total_duration_ms:.0f}ms",
            f"**Sub-tasks:** {len(self.subtasks)}",
            ""
        ]
        
        for step_id, result in self.subtasks.items():
            icon = "✅" if result.status == "complete" else "❌" if result.status == "failed" else "🔄"
            lines.append(f"{icon} **{result.agent_type}**: {result.description[:60]} ({result.duration_ms:.0f}ms)")
        
        return "\n".join(lines)


# ============================================================================
# SUB-AGENT PROXY
# ============================================================================

class SubAgentProxy:
    """
    Proxy for executing a sub-agent task.
    Wraps a BaseAgent for use in swarm execution.
    """
    
    def __init__(self, agent_type: str, model: str = "openai"):
        self.agent_type = agent_type
        self.model = model
        self._agent = None
    
    def _get_agent(self) -> BaseAgent:
        """Lazy-load the agent with appropriate system prompt."""
        if self._agent is None:
            system_prompt = SystemPrompts.get_sub_agent_prompt(self.agent_type)
            self._agent = BaseAgent(
                name=f"{self.agent_type.title()}Agent",
                model=self.model,
                system_prompt=system_prompt
            )
        return self._agent
    
    async def execute(self, task: str, user_id: Optional[str] = None) -> str:
        """
        Execute a task using the sub-agent.
        
        Args:
            task: Task description for the sub-agent
            user_id: User ID for memory
        
        Returns:
            Agent response string
        """
        agent = self._get_agent()
        return await agent.run(task, user_id=user_id)


# ============================================================================
# SWARM ORCHESTRATOR
# ============================================================================

class SwarmOrchestrator:
    """
    Swarm orchestrator for parallel agent execution.
    
    Features:
    - Master agent decomposes tasks into sub-tasks
    - Parallel execution of independent sub-tasks
    - Sequential execution for dependent tasks
    - Progress tracking and callbacks
    - Result synthesis into final response
    """
    
    def __init__(
        self,
        model: str = "openai",
        max_parallel: int = None,
        enable_progress: bool = True
    ):
        """
        Initialize the swarm orchestrator.
        
        Args:
            model: Default model for all agents
            max_parallel: Maximum number of parallel executions
            enable_progress: Whether to emit progress updates
        """
        self.model = model
        self.max_parallel = max_parallel or AppConfig.max_parallel_agents
        self.enable_progress = enable_progress
        
        self._client = None
        self._planner = get_planner()
        self._sub_agents: Dict[str, SubAgentProxy] = {}
        self._progress_callbacks: List[Callable] = []
    
    # ========================================================================
    # Properties
    # ========================================================================
    
    @property
    def client(self) -> MultiProviderClient:
        """Lazy-load the client for master agent."""
        if self._client is None:
            self._client = get_client()
        return self._client
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def add_progress_callback(self, callback: Callable):
        """Add a callback for progress updates."""
        self._progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable):
        """Remove a progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        user_id: Optional[str] = None,
        custom_plan: Optional[ExecutionPlan] = None
    ) -> SwarmExecutionResult:
        """
        Execute a task using the swarm.
        
        Args:
            task: User task description
            context: Additional context
            user_id: User ID for memory
            custom_plan: Optional pre-defined plan (auto-generated if not provided)
        
        Returns:
            SwarmExecutionResult with all results and synthesis
        """
        start_time = datetime.now()
        
        # Step 1: Create or use plan
        if custom_plan:
            plan = custom_plan
        else:
            plan = self._planner.create_plan(task, context)
        
        self._emit_progress({
            "type": "plan_created",
            "total_steps": plan.total_steps,
            "agent_types": plan.agent_types_used,
            "estimated_time": plan.estimated_total_time
        })
        
        # Step 2: Initialize sub-agent proxies
        for agent_type in plan.agent_types_used:
            if agent_type not in self._sub_agents:
                self._sub_agents[agent_type] = SubAgentProxy(agent_type, self.model)
        
        # Step 3: Execute all steps respecting dependencies
        subtask_results: Dict[str, SubTaskResult] = {}
        completed = set()
        
        # Initialize results for all steps
        for step in plan.steps:
            subtask_results[step.id] = SubTaskResult(
                step_id=step.id,
                description=step.description,
                agent_type=step.agent_type,
                result="",
                status="pending"
            )
        
        self._emit_progress({
            "type": "execution_started",
            "total_steps": len(plan.steps)
        })
        
        # Continue until all steps are complete or failed
        while len(completed) < len(plan.steps):
            # Find steps ready for execution
            ready_steps = []
            for step in plan.steps:
                if step.id in completed:
                    continue
                
                # Check if all dependencies are completed
                deps_complete = all(dep in completed for dep in step.dependencies)
                if deps_complete and subtask_results[step.id].status == "pending":
                    ready_steps.append(step)
            
            if not ready_steps:
                # Deadlock detected
                self._emit_progress({
                    "type": "deadlock_detected",
                    "completed": list(completed),
                    "pending": [s.id for s in plan.steps if s.id not in completed]
                })
                break
            
            # Execute ready steps in parallel (up to max_parallel)
            batch = ready_steps[:self.max_parallel]
            
            # Update status to running
            for step in batch:
                subtask_results[step.id].status = "running"
                subtask_results[step.id].started_at = datetime.now()
                self._emit_progress({
                    "type": "step_started",
                    "step_id": step.id,
                    "agent_type": step.agent_type,
                    "description": step.description[:100]
                })
            
            # Execute batch in parallel
            tasks = [
                self._execute_step(step, subtask_results[step.id], user_id)
                for step in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for step, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    subtask_results[step.id].status = "failed"
                    subtask_results[step.id].error = str(result)
                    self._emit_progress({
                        "type": "step_failed",
                        "step_id": step.id,
                        "error": str(result)[:200]
                    })
                else:
                    subtask_results[step.id].result = result
                    subtask_results[step.id].status = "complete"
                    subtask_results[step.id].completed_at = datetime.now()
                    subtask_results[step.id].duration_ms = (
                        subtask_results[step.id].completed_at - subtask_results[step.id].started_at
                    ).total_seconds() * 1000
                    
                    self._emit_progress({
                        "type": "step_completed",
                        "step_id": step.id,
                        "agent_type": step.agent_type,
                        "duration_ms": subtask_results[step.id].duration_ms
                    })
                
                completed.add(step.id)
        
        # Step 4: Synthesize results
        self._emit_progress({
            "type": "synthesis_started",
            "completed_steps": len(completed),
            "total_steps": len(plan.steps)
        })
        
        synthesis = await self._synthesize_results(task, plan, subtask_results, user_id)
        
        # Step 5: Create final result
        end_time = datetime.now()
        
        return SwarmExecutionResult(
            task=task,
            status="complete" if all(r.status == "complete" for r in subtask_results.values()) else "partial",
            subtasks=subtask_results,
            synthesis=synthesis,
            started_at=start_time,
            completed_at=end_time,
            total_duration_ms=(end_time - start_time).total_seconds() * 1000,
            plan=plan
        )
    
    async def execute_simple(
        self,
        task: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        Simple execution - just returns the synthesis.
        Useful for quick tasks where you don't need detailed results.
        
        Args:
            task: User task description
            user_id: User ID for memory
        
        Returns:
            Synthesized response string
        """
        result = await self.execute(task, user_id=user_id)
        return result.synthesis
    
    def get_available_agents(self) -> List[str]:
        """Get list of available sub-agent types."""
        return AgentType.get_all()
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    async def _execute_step(
        self,
        step: PlanStep,
        result: SubTaskResult,
        user_id: Optional[str] = None
    ) -> str:
        """Execute a single plan step."""
        proxy = self._sub_agents.get(step.agent_type)
        if not proxy:
            return f"Error: No agent available for type '{step.agent_type}'"
        
        return await proxy.execute(step.description, user_id)
    
    async def _synthesize_results(
        self,
        task: str,
        plan: ExecutionPlan,
        results: Dict[str, SubTaskResult],
        user_id: Optional[str] = None
    ) -> str:
        """
        Synthesize all sub-task results into a final response.
        
        Uses the master agent (LLM) to combine results cohesively.
        """
        # Build context from all successful results
        context_parts = []
        
        for step in plan.steps:
            result = results.get(step.id)
            if result and result.status == "complete" and result.result:
                icon = AgentType.get_icon(step.agent_type)
                context_parts.append(f"\n### {icon} {step.agent_type.upper()} Agent\n")
                context_parts.append(f"**Task:** {step.description}\n")
                context_parts.append(f"**Result:**\n{result.result[:1500]}\n")
        
        if not context_parts:
            return "No sub-tasks completed successfully. Unable to synthesize response."
        
        synthesis_prompt = f"""## Original User Task

{task}

## Results from Sub-Agents

{''.join(context_parts)}

## Instructions

Please synthesize the above results into a clear, comprehensive final response that directly addresses the original user task.

Requirements:
1. Be coherent and well-structured
2. Integrate information from all relevant sub-agents
3. Highlight key findings and insights
4. Provide actionable conclusions
5. Use clear headings and formatting if beneficial

Final Response:"""
        
        # Use the master agent for synthesis
        messages = [
            {"role": "system", "content": SystemPrompts.SYNTHESIS_PROMPT},
            {"role": "user", "content": synthesis_prompt}
        ]
        
        response = self.client.chat(
            messages=messages,
            model=self.model,
            temperature=0.5,
            user_id=user_id
        )
        
        return response.get("content", "Synthesis completed but no content generated.")
    
    def _emit_progress(self, data: Dict):
        """Emit progress update to all callbacks."""
        if not self.enable_progress:
            return
        
        for callback in self._progress_callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"Error in progress callback: {e}")


# ============================================================================
# SIMPLIFIED SWARM FUNCTIONS
# ============================================================================

_swarm_instance: Optional[SwarmOrchestrator] = None


def get_swarm(
    model: str = "openai",
    max_parallel: int = None
) -> SwarmOrchestrator:
    """
    Get or create the SwarmOrchestrator singleton.
    
    Args:
        model: Default model for all agents
        max_parallel: Maximum parallel executions
    
    Returns:
        SwarmOrchestrator instance
    """
    global _swarm_instance
    if _swarm_instance is None or _swarm_instance.model != model:
        _swarm_instance = SwarmOrchestrator(model=model, max_parallel=max_parallel)
    return _swarm_instance


async def run_swarm(
    task: str,
    context: Optional[str] = None,
    user_id: Optional[str] = None,
    model: str = "openai"
) -> SwarmExecutionResult:
    """
    Convenience function to run a swarm task.
    
    Args:
        task: User task description
        context: Additional context
        user_id: User ID for memory
        model: Model to use
    
    Returns:
        SwarmExecutionResult
    """
    swarm = get_swarm(model=model)
    return await swarm.execute(task, context, user_id)


async def run_swarm_simple(
    task: str,
    user_id: Optional[str] = None,
    model: str = "openai"
) -> str:
    """
    Convenience function to run a swarm task and get only the synthesis.
    
    Args:
        task: User task description
        user_id: User ID for memory
        model: Model to use
    
    Returns:
        Synthesized response string
    """
    swarm = get_swarm(model=model)
    return await swarm.execute_simple(task, user_id)


# ============================================================================
# SYNC WRAPPERS (for use in non-async contexts)
# ============================================================================

def run_swarm_sync(
    task: str,
    context: Optional[str] = None,
    user_id: Optional[str] = None,
    model: str = "openai"
) -> SwarmExecutionResult:
    """
    Sync wrapper for run_swarm.
    
    Args:
        task: User task description
        context: Additional context
        user_id: User ID for memory
        model: Model to use
    
    Returns:
        SwarmExecutionResult
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_swarm(task, context, user_id, model))
    finally:
        loop.close()


def run_swarm_simple_sync(
    task: str,
    user_id: Optional[str] = None,
    model: str = "openai"
) -> str:
    """
    Sync wrapper for run_swarm_simple.
    
    Args:
        task: User task description
        user_id: User ID for memory
        model: Model to use
    
    Returns:
        Synthesized response string
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_swarm_simple(task, user_id, model))
    finally:
        loop.close()