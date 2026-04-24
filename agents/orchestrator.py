"""Advanced Swarm orchestrator for parallel agent execution - Kimi-inspired."""
import asyncio
import uuid
import json
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
    progress: float = 0.0  # 0-100 progress tracking

class SwarmOrchestrator:
    """Advanced swarm orchestrator with progress tracking and parallel execution."""
    
    def __init__(self, max_parallel: int = 4):
        self.max_parallel = max_parallel
        self.subtasks: Dict[str, SubTask] = {}
        self.agent_factories: Dict[str, Callable] = {}
        self.on_progress: Optional[Callable] = None
        self._execution_log: List[Dict] = []
        
    def register_agent(self, agent_type: str, factory: Callable):
        """Register agent factory."""
        self.agent_factories[agent_type] = factory
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current execution progress."""
        total = len(self.subtasks)
        if total == 0:
            return {"total": 0, "completed": 0, "running": 0, "pending": 0, "percentage": 0}
        
        completed = sum(1 for s in self.subtasks.values() if s.status == "complete")
        running = sum(1 for s in self.subtasks.values() if s.status == "running")
        pending = sum(1 for s in self.subtasks.values() if s.status == "pending")
        failed = sum(1 for s in self.subtasks.values() if s.status == "failed")
        
        return {
            "total": total,
            "completed": completed,
            "running": running,
            "pending": pending,
            "failed": failed,
            "percentage": int((completed / total) * 100) if total > 0 else 0
        }
    
    async def execute(self, task: str, plan: Optional[List[SubTask]] = None) -> Dict:
        """Execute task with parallel agents and progress tracking."""
        if plan is None:
            from .planner import TaskPlanner
            planner = TaskPlanner()
            plan = planner.create_plan(task)
        
        self.subtasks = {st_obj.id: st_obj for st_obj in plan}
        self._execution_log = []
        
        completed = {}
        running = set()
        
        # Report initial progress
        if self.on_progress:
            self.on_progress({"type": "start", "task": task, **self.get_progress()})
        
        while len(completed) < len(self.subtasks):
            # Find ready tasks
            ready = [
                subtask for subtask in self.subtasks.values()
                if subtask.status == "pending"
                and all(dep in completed for dep in subtask.dependencies)
                and subtask.id not in running
            ]
            
            to_launch = ready[:self.max_parallel - len(running)]
            
            if to_launch:
                tasks = []
                for subtask in to_launch:
                    subtask.status = "running"
                    subtask.started_at = datetime.now()
                    running.add(subtask.id)
                    
                    if self.on_progress:
                        self.on_progress({
                            "type": "step_start",
                            "step_id": subtask.id,
                            "description": subtask.description,
                            **self.get_progress()
                        })
                    
                    if subtask.agent_type in self.agent_factories:
                        agent = self.agent_factories[subtask.agent_type]()
                        coro = self._run_with_timeout_and_progress(agent, subtask)
                        tasks.append(coro)
                    else:
                        # Fallback to generic execution
                        subtask.result = await self._generic_execute(subtask)
                        subtask.status = "complete"
                        subtask.completed_at = datetime.now()
                        completed[subtask.id] = subtask.result
                        running.discard(subtask.id)
                        
                        self._log_step(subtask)
                        if self.on_progress:
                            self.on_progress({
                                "type": "step_complete",
                                "step_id": subtask.id,
                                **self.get_progress()
                            })
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for subtask, result in zip(to_launch, results):
                        subtask.completed_at = datetime.now()
                        if isinstance(result, Exception):
                            subtask.status = "failed"
                            subtask.result = str(result)
                            # Retry once on failure
                            retry_result = await self._retry_step(subtask)
                            if retry_result is not None:
                                subtask.status = "complete"
                                subtask.result = retry_result
                                completed[subtask.id] = retry_result
                            else:
                                completed[subtask.id] = subtask.result
                        else:
                            subtask.status = "complete"
                            subtask.result = result
                            completed[subtask.id] = result
                        
                        running.discard(subtask.id)
                        self._log_step(subtask)
                        
                        if self.on_progress:
                            self.on_progress({
                                "type": "step_complete",
                                "step_id": subtask.id,
                                **self.get_progress()
                            })
            else:
                if not running and len(completed) < len(self.subtasks):
                    # Deadlock detected - mark remaining as failed
                    for st in self.subtasks.values():
                        if st.status == "pending":
                            st.status = "failed"
                            st.result = "Deadlock: dependencies could not be satisfied"
                            completed[st.id] = st.result
                    break
                await asyncio.sleep(0.1)
        
        # Synthesize results
        synthesis = await self._synthesize_with_llm(completed, task)
        
        final_result = {
            "task": task,
            "subtasks": {k: {
                "status": v.status,
                "result": str(v.result)[:1000] if v.result else None,
                "duration": (v.completed_at - v.started_at).total_seconds() if v.completed_at and v.started_at else 0,
                "agent_type": v.agent_type
            } for k, v in self.subtasks.items()},
            "completed": {k: str(v)[:500] for k, v in completed.items()},
            "synthesis": synthesis,
            "execution_log": self._execution_log,
            "progress": self.get_progress()
        }
        
        if self.on_progress:
            self.on_progress({"type": "complete", **final_result})
        
        return final_result
    
    async def _run_with_timeout_and_progress(self, agent, subtask: SubTask, timeout: int = 60):
        """Run agent with timeout and progress updates."""
        try:
            # Set up progress callback
            if hasattr(agent, 'on_progress'):
                agent.on_progress = lambda p: self._update_subtask_progress(subtask, p)
            
            return await asyncio.wait_for(
                agent.run(subtask.description),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return "Task timed out after 60 seconds"
    
    async def _retry_step(self, subtask: SubTask) -> Optional[Any]:
        """Retry a failed step once with a different approach."""
        try:
            if subtask.agent_type in self.agent_factories:
                agent = self.agent_factories[subtask.agent_type]()
                return await asyncio.wait_for(
                    agent.run(f"{subtask.description}\n\nPrevious attempt failed. Try a different approach."),
                    timeout=45
                )
        except Exception:
            pass
        return None
    
    async def _generic_execute(self, subtask: SubTask) -> str:
        """Generic execution for unregistered agent types."""
        # Use direct LLM call as fallback
        try:
            import requests
            api_url = "https://text.pollinations.ai/openai"
            payload = {
                "model": "openai",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant. Execute the given task to the best of your ability."},
                    {"role": "user", "content": subtask.description}
                ],
                "temperature": 0.7
            }
            resp = requests.post(api_url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return f"API error: HTTP {resp.status_code}"
        except Exception as e:
            return f"Execution error: {str(e)}"
    
    def _update_subtask_progress(self, subtask: SubTask, progress_update: Dict):
        """Update subtask progress and report."""
        if "progress" in progress_update:
            subtask.progress = progress_update["progress"]
        
        if self.on_progress:
            self.on_progress({
                "type": "step_progress",
                "step_id": subtask.id,
                "progress": subtask.progress,
                **self.get_progress()
            })
    
    def _log_step(self, subtask: SubTask):
        """Log step execution."""
        self._execution_log.append({
            "step_id": subtask.id,
            "description": subtask.description,
            "agent_type": subtask.agent_type,
            "status": subtask.status,
            "duration": (subtask.completed_at - subtask.started_at).total_seconds() if subtask.completed_at and subtask.started_at else 0,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _synthesize_with_llm(self, results: Dict, original_task: str) -> str:
        """Synthesize parallel results using LLM for coherent output."""
        try:
            import requests
            
            # Build synthesis prompt
            parts = [f"## Task: {original_task}\n\n### Results from parallel execution:\n"]
            for st_id, result in results.items():
                subtask = self.subtasks.get(st_id)
                if subtask:
                    parts.append(f"\n**{subtask.description}** ({subtask.agent_type}):\n{str(result)[:800]}")
            
            synthesis_prompt = "\n".join(parts)
            synthesis_prompt += "\n\nPlease synthesize these results into a coherent, well-structured response that directly addresses the original task."
            
            api_url = "https://text.pollinations.ai/openai"
            payload = {
                "model": "openai",
                "messages": [
                    {"role": "system", "content": "You are a synthesis expert. Combine multiple task results into a clear, coherent response."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                "temperature": 0.5
            }
            
            resp = requests.post(api_url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Fallback to basic synthesis
            return self._basic_synthesize(results, original_task)
            
        except Exception:
            return self._basic_synthesize(results, original_task)
    
    def _basic_synthesize(self, results: Dict, original_task: str) -> str:
        """Basic synthesis without LLM."""
        parts = [f"## Task: {original_task}\n"]
        for st_id, result in results.items():
            subtask = self.subtasks.get(st_id)
            if subtask:
                parts.append(f"\n### {subtask.description}\n{str(result)[:500]}")
        return "\n".join(parts)


# Convenience function for simple swarm execution
def run_swarm_task(task: str, max_parallel: int = 3) -> Dict:
    """Run a swarm task and return results."""
    orchestrator = SwarmOrchestrator(max_parallel=max_parallel)
    
    # Register default agent factories
    try:
        from .base_agent import BaseAgent
        
        class SimpleAgent(BaseAgent):
            async def _llm_call(self, messages, tools=None):
                import requests
                api_url = "https://text.pollinations.ai/openai"
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7
                }
                if tools:
                    payload["tools"] = tools
                resp = requests.post(api_url, json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    msg = data.get("choices", [{}])[0].get("message", {})
                    return {
                        "content": msg.get("content", ""),
                        "tool_calls": msg.get("tool_calls")
                    }
                return {"content": "", "tool_calls": None}
        
        orchestrator.register_agent("researcher", lambda: SimpleAgent("Researcher", model="openai"))
        orchestrator.register_agent("coder", lambda: SimpleAgent("Coder", model="openai"))
        orchestrator.register_agent("analyst", lambda: SimpleAgent("Analyst", model="openai"))
        orchestrator.register_agent("writer", lambda: SimpleAgent("Writer", model="openai"))
        orchestrator.register_agent("browser", lambda: SimpleAgent("Browser", model="openai"))
    except Exception:
        pass
    
    return asyncio.run(orchestrator.execute(task))
