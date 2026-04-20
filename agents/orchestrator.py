"""Swarm orchestrator for parallel agent execution."""
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SubTask:
    id: str
    description: str
    agent_type: str
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class SwarmOrchestrator:
    """Coordinates parallel agent execution."""
    
    def __init__(self, max_parallel: int = 4):
        self.max_parallel = max_parallel
        self.subtasks: Dict[str, SubTask] = {}
        self.agent_factories: Dict[str, Callable] = {}
        self.on_progress: Optional[Callable] = None
        
    def register_agent(self, agent_type: str, factory: Callable):
        """Register agent factory."""
        self.agent_factories[agent_type] = factory
    
    async def execute(self, task: str, plan: Optional[List[SubTask]] = None) -> Dict:
        """Execute task with parallel agents."""
        if plan is None:
            from .planner import TaskPlanner
            planner = TaskPlanner()
            plan = planner.create_plan(task)
        
        # Initialize subtasks
        self.subtasks = {st.id: st for st in plan}
        
        completed = {}
        running = set()
        
        while len(completed) < len(self.subtasks):
            # Find ready tasks
            ready = [
                st for st in self.subtasks.values()
                if st.status == "pending"
                and all(dep in completed for dep in st.dependencies)
                and st.id not in running
            ]
            
            # Launch batch
            to_launch = ready[:self.max_parallel - len(running)]
            
            if to_launch:
                tasks = []
                for st in to_launch:
                    st.status = "running"
                    st.started_at = datetime.now()
                    running.add(st.id)
                    
                    if st.agent_type in self.agent_factories:
                        agent = self.agent_factories[st.agent_type]()
                        coro = self._run_with_timeout(agent, st)
                        tasks.append(coro)
                    else:
                        # Fallback to generic agent
                        st.result = f"No agent factory for {st.agent_type}"
                        st.status = "failed"
                        completed[st.id] = st.result
                        running.discard(st.id)
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for st, result in zip(to_launch, results):
                        st.completed_at = datetime.now()
                        if isinstance(result, Exception):
                            st.status = "failed"
                            st.result = str(result)
                        else:
                            st.status = "complete"
                            st.result = result
                        completed[st.id] = st.result
                        running.discard(st.id)
                        
                        if self.on_progress:
                            self.on_progress(st)
            else:
                if not running and len(completed) < len(self.subtasks):
                    # Deadlock detected
                    break
                await asyncio.sleep(0.1)
        
        # Synthesize results
        synthesis = await self._synthesize(completed, task)
        
        return {
            "task": task,
            "subtasks": {k: {
                "status": v.status,
                "result": v.result,
                "duration": (v.completed_at - v.started_at).total_seconds() if v.completed_at and v.started_at else 0
            } for k, v in self.subtasks.items()},
            "completed": completed,
            "synthesis": synthesis
        }
    
    async def _run_with_timeout(self, agent, subtask: SubTask, timeout: int = 60):
        """Run agent with timeout."""
        try:
            return await asyncio.wait_for(
                agent.run(subtask.description),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return "Task timed out"
    
    async def _synthesize(self, results: Dict, original_task: str) -> str:
        """Synthesize parallel results."""
        # Simple synthesis - can be enhanced with LLM
        parts = [f"## Task: {original_task}\n"]
        for st_id, result in results.items():
            st = self.subtasks.get(st_id)
            if st:
                parts.append(f"\n### {st.description}\n{str(result)[:500]}")
        
        return "\n".join(parts)
