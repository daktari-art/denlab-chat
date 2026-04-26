"""
Task Planner with Dynamic Decomposition and Dependency Graph.

ADVANCEMENTS:
1. Dynamic decomposition: LLM-based or heuristic based on complexity
2. Dependency graph: Subtasks have explicit dependencies
3. Complexity scoring: Simple tasks get fewer subtasks
4. Estimation: Estimated time and confidence per subtask
5. Retry planning: If initial plan fails, replan with different strategy
6. Template plans: Predefined plans for common task types

Connected to: base_agent.py (agents), config/settings.py (planner config).
"""

import json
import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AppConfig
from client import get_client


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Subtask:
    """A subtask with metadata."""
    id: str
    description: str
    estimated_time_seconds: int = 30
    confidence: float = 0.8
    dependencies: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    is_parallel_safe: bool = True


@dataclass
class TaskPlan:
    """A complete task plan."""
    original_task: str
    subtasks: List[Subtask]
    estimated_total_time: int = 0
    complexity_score: float = 0.5
    fallback_strategy: str = ""


# ============================================================================
# PLANNER
# ============================================================================

class TaskPlanner:
    """
    Advanced task planner with dynamic decomposition.
    """
    
    # Template plans for common tasks
    TEMPLATES = {
        "web_research": [
            Subtask(id="search", description="Search web for relevant information",
                   required_tools=["web_search"], estimated_time_seconds=30),
            Subtask(id="synthesize", description="Synthesize search results into coherent answer",
                   dependencies=["search"], estimated_time_seconds=20),
        ],
        "code_debug": [
            Subtask(id="analyze", description="Analyze code for errors",
                   required_tools=["execute_code"], estimated_time_seconds=20),
            Subtask(id="fix", description="Propose and apply fixes",
                   dependencies=["analyze"], required_tools=["execute_code"], estimated_time_seconds=40),
            Subtask(id="verify", description="Verify the fix works",
                   dependencies=["fix"], required_tools=["execute_code"], estimated_time_seconds=20),
        ],
        "file_analysis": [
            Subtask(id="read", description="Read and parse the file",
                   required_tools=["read_file"], estimated_time_seconds=15),
            Subtask(id="analyze", description="Analyze content and extract insights",
                   dependencies=["read"], estimated_time_seconds=25),
            Subtask(id="summarize", description="Summarize findings",
                   dependencies=["analyze"], estimated_time_seconds=15),
        ],
        "github_explore": [
            Subtask(id="list_files", description="List repository files",
                   required_tools=["github_get_files"], estimated_time_seconds=20),
            Subtask(id="analyze_structure", description="Analyze project structure",
                   dependencies=["list_files"], estimated_time_seconds=20),
            Subtask(id="read_key_files", description="Read important files",
                   dependencies=["analyze_structure"], required_tools=["github_get_files"], estimated_time_seconds=30),
        ]
    }
    
    def __init__(self, model: str = "openai"):
        self.model = model
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            self._client = get_client()
        return self._client
    
    # ========================================================================
    # DECOMPOSITION
    # ========================================================================
    
    def decompose(self, task: str) -> List[str]:
        """
        Decompose a task into subtasks.
        
        Returns list of subtask descriptions for backward compatibility.
        """
        plan = self.create_plan(task)
        return [st.description for st in plan.subtasks]
    
    def create_plan(self, task: str) -> TaskPlan:
        """Create a full task plan with dependencies and metadata."""
        # Check templates first
        template = self._match_template(task)
        if template:
            plan = TaskPlan(
                original_task=task,
                subtasks=[Subtask(id=st.id, description=st.description,
                                dependencies=st.dependencies,
                                required_tools=st.required_tools,
                                estimated_time_seconds=st.estimated_time_seconds)
                         for st in template],
                estimated_total_time=sum(st.estimated_time_seconds for st in template),
                complexity_score=0.5
            )
            return plan
        
        # Check complexity
        complexity = self._score_complexity(task)
        
        if complexity < 0.3:
            # Simple task - no decomposition
            return TaskPlan(
                original_task=task,
                subtasks=[Subtask(id="main", description=task, estimated_time_seconds=30)],
                complexity_score=complexity
            )
        
        # Complex task - LLM decomposition
        return self._llm_decompose(task, complexity)
    
    def _match_template(self, task: str) -> Optional[List[Subtask]]:
        """Match task against predefined templates."""
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in ["research", "search", "find information", "look up"]):
            return self.TEMPLATES["web_research"]
        
        if any(kw in task_lower for kw in ["debug", "fix", "error", "bug", "test code"]):
            return self.TEMPLATES["code_debug"]
        
        if any(kw in task_lower for kw in ["analyze file", "read document", "parse csv", "pdf"]):
            return self.TEMPLATES["file_analysis"]
        
        if any(kw in task_lower for kw in ["github", "repo", "repository", "codebase"]):
            return self.TEMPLATES["github_explore"]
        
        return None
    
    def _score_complexity(self, task: str) -> float:
        """Score task complexity (0.0-1.0)."""
        score = 0.0
        
        # Length
        score += min(len(task) / 500, 0.2)
        
        # Multiple requirements
        conjunctions = ["and", "then", "also", "additionally", "furthermore", "moreover"]
        score += sum(0.05 for c in conjunctions if c in task.lower())
        
        # Domain complexity
        complex_keywords = ["research", "analyze", "compare", "evaluate", "synthesize",
                           "implement", "design", "architecture", "optimization"]
        score += sum(0.08 for kw in complex_keywords if kw in task.lower())
        
        # Tool requirements
        tool_keywords = ["search", "code", "file", "github", "calculate", "plot"]
        score += sum(0.05 for kw in tool_keywords if kw in task.lower())
        
        return min(score, 1.0)
    
    def _llm_decompose(self, task: str, complexity: float) -> TaskPlan:
        """Use LLM to decompose complex task."""
        prompt = f"""Break down this task into clear subtasks:

Task: {task}
Complexity: {complexity:.2f}/1.0

Respond in JSON:
{{
    "subtasks": [
        {{
            "id": "step_1",
            "description": "...",
            "dependencies": [],
            "estimated_seconds": 30
        }}
    ],
    "fallback": "Alternative approach if this fails"
}}"""
        
        try:
            response = self._get_client().generate([
                {"role": "system", "content": "You are a task planner. Break down tasks into clear subtasks."},
                {"role": "user", "content": prompt}
            ], model=self.model)
            
            content = response.get("content", "")
            
            # Extract JSON
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            subtasks = []
            for st_data in data.get("subtasks", []):
                subtasks.append(Subtask(
                    id=st_data.get("id", f"step_{len(subtasks)+1}"),
                    description=st_data.get("description", ""),
                    dependencies=st_data.get("dependencies", []),
                    estimated_time_seconds=st_data.get("estimated_seconds", 30)
                ))
            
            total_time = sum(st.estimated_time_seconds for st in subtasks) if subtasks else 30
            
            return TaskPlan(
                original_task=task,
                subtasks=subtasks,
                estimated_total_time=total_time,
                complexity_score=complexity,
                fallback_strategy=data.get("fallback", "Use web search for more context")
            )
        
        except Exception:
            # Fallback: single subtask
            return TaskPlan(
                original_task=task,
                subtasks=[Subtask(id="main", description=task, estimated_time_seconds=60)],
                complexity_score=complexity,
                fallback_strategy="Break into smaller queries"
            )
    
    # ========================================================================
    # PLAN EXECUTION ORDER
    # ========================================================================
    
    def get_execution_order(self, plan: TaskPlan) -> List[Subtask]:
        """Get subtasks in dependency-respecting order."""
        # Topological sort
        completed: Set[str] = set()
        pending = {st.id: st for st in plan.subtasks}
        order = []
        
        while pending:
            ready = [
                st for st in pending.values()
                if all(dep in completed for dep in st.dependencies)
            ]
            
            if not ready:
                # Circular dependency - break it
                ready = list(pending.values())[:1]
            
            for st in ready:
                order.append(st)
                completed.add(st.id)
                del pending[st.id]
        
        return order
    
    def get_parallel_groups(self, plan: TaskPlan) -> List[List[Subtask]]:
        """Group subtasks that can execute in parallel."""
        order = self.get_execution_order(plan)
        groups = []
        current_group = []
        current_deps: Set[str] = set()
        
        for st in order:
            if all(dep in current_deps for dep in st.dependencies) or not st.dependencies:
                current_group.append(st)
                current_deps.add(st.id)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [st]
                current_deps = set(st.dependencies) | {st.id}
        
        if current_group:
            groups.append(current_group)
        
        return groups


# ============================================================================
# SINGLETON
# ============================================================================

_PLANNER_INSTANCE = None

def get_planner(model: str = "openai") -> TaskPlanner:
    """Get or create global planner."""
    global _PLANNER_INSTANCE
    if _PLANNER_INSTANCE is None:
        _PLANNER_INSTANCE = TaskPlanner(model=model)
    return _PLANNER_INSTANCE


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["TaskPlanner", "Subtask", "TaskPlan", "get_planner"]
