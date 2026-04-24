"""Task decomposition planner."""
import json
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class PlanStep:
    id: str
    description: str
    agent_type: str
    dependencies: List[str]
    estimated_time: int  # seconds

class TaskPlanner:
    """Decomposes complex tasks into executable steps."""
    
    def __init__(self):
        self.agent_types = {
            "researcher": "Searches web, reads documents, gathers facts",
            "coder": "Writes and executes Python code",
            "analyst": "Analyzes data, creates summaries",
            "writer": "Composes final responses and reports",
            "browser": "Navigates websites, extracts specific data"
        }
    
    def create_plan(self, task: str) -> List[PlanStep]:
        """Create execution plan for task."""
        # Simple rule-based planning (can be enhanced with LLM)
        plan = []
        
        if any(kw in task.lower() for kw in ['research', 'find', 'search', 'look up']):
            plan.append(PlanStep(
                id="1", description=f"Research: {task}",
                agent_type="researcher", dependencies=[], estimated_time=30
            ))
        
        if any(kw in task.lower() for kw in ['code', 'script', 'program', 'calculate']):
            plan.append(PlanStep(
                id="2", description="Write and test code",
                agent_type="coder", dependencies=["1"] if plan else [], estimated_time=20
            ))
        
        if any(kw in task.lower() for kw in ['analyze', 'compare', 'summarize']):
            plan.append(PlanStep(
                id="3", description="Analyze findings",
                agent_type="analyst", dependencies=["1"] if plan else [], estimated_time=15
            ))
        
        # Always add writer if complex task
        if len(plan) > 1:
            plan.append(PlanStep(
                id="final", description="Synthesize final answer",
                agent_type="writer", dependencies=[p.id for p in plan], estimated_time=10
            ))
        else:
            # Simple task - just do it
            plan.append(PlanStep(
                id="1", description=task,
                agent_type="researcher", dependencies=[], estimated_time=20
            ))
        
        return plan
    
    def to_json(self, plan: List[PlanStep]) -> str:
        """Convert plan to JSON."""
        return json.dumps([
            {
                "id": p.id,
                "description": p.description,
                "agent_type": p.agent_type,
                "dependencies": p.dependencies,
                "estimated_time": p.estimated_time
            }
            for p in plan
        ], indent=2)

