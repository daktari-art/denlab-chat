"""
Task Decomposition Planner for DenLab Swarm Agents.
Breaks down complex tasks into executable steps for parallel agent execution.
No execution logic - pure planning.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Import from centralized config
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Constants, SystemPrompts


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class AgentType(Enum):
    """Types of agents available for task execution."""
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYST = "analyst"
    WRITER = "writer"
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all agent type names."""
        return [agent.value for agent in cls]
    
    @classmethod
    def get_icon(cls, agent_type: str) -> str:
        """Get icon for agent type."""
        icons = {
            "researcher": "🔍",
            "coder": "💻",
            "analyst": "📊",
            "writer": "✍️"
        }
        return icons.get(agent_type, "🤖")
    
    @classmethod
    def get_description(cls, agent_type: str) -> str:
        """Get description for agent type."""
        descriptions = {
            "researcher": "Searches web, reads documents, gathers facts",
            "coder": "Writes and executes Python code",
            "analyst": "Analyzes data, creates summaries, draws insights",
            "writer": "Composes final responses and reports"
        }
        return descriptions.get(agent_type, "General purpose agent")


@dataclass
class PlanStep:
    """
    A single step in the execution plan.
    
    Attributes:
        id: Unique step identifier (e.g., "1", "2a", "final")
        description: Human-readable description of the step
        agent_type: Type of agent to execute this step
        dependencies: List of step IDs that must complete before this step
        estimated_time: Estimated execution time in seconds
        priority: Priority level (1 = highest, 5 = lowest)
        output_key: Key to store result under (for synthesis)
    """
    id: str
    description: str
    agent_type: str
    dependencies: List[str] = field(default_factory=list)
    estimated_time: int = 30
    priority: int = 3
    output_key: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "agent_type": self.agent_type,
            "dependencies": self.dependencies,
            "estimated_time": self.estimated_time,
            "priority": self.priority,
            "output_key": self.output_key or self.id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PlanStep":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            agent_type=data["agent_type"],
            dependencies=data.get("dependencies", []),
            estimated_time=data.get("estimated_time", 30),
            priority=data.get("priority", 3),
            output_key=data.get("output_key")
        )


@dataclass
class ExecutionPlan:
    """
    Complete execution plan for a task.
    
    Attributes:
        task: Original task description
        steps: List of plan steps in execution order
        metadata: Additional metadata about the plan
    """
    task: str
    steps: List[PlanStep]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_steps(self) -> int:
        """Get total number of steps."""
        return len(self.steps)
    
    @property
    def estimated_total_time(self) -> int:
        """Get estimated total execution time in seconds."""
        return sum(step.estimated_time for step in self.steps)
    
    @property
    def agent_types_used(self) -> List[str]:
        """Get unique agent types used in the plan."""
        return list(set(step.agent_type for step in self.steps))
    
    def get_steps_by_agent(self, agent_type: str) -> List[PlanStep]:
        """Get all steps for a specific agent type."""
        return [step for step in self.steps if step.agent_type == agent_type]
    
    def get_dependent_steps(self, step_id: str) -> List[PlanStep]:
        """Get steps that depend on a given step."""
        return [step for step in self.steps if step_id in step.dependencies]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "task": self.task,
            "steps": [step.to_dict() for step in self.steps],
            "metadata": self.metadata,
            "total_steps": self.total_steps,
            "estimated_total_time": self.estimated_total_time,
            "agent_types_used": self.agent_types_used
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ExecutionPlan":
        """Create from JSON string."""
        data = json.loads(json_str)
        steps = [PlanStep.from_dict(step_data) for step_data in data["steps"]]
        return cls(
            task=data["task"],
            steps=steps,
            metadata=data.get("metadata", {})
        )


# ============================================================================
# TASK PLANNER
# ============================================================================

class TaskPlanner:
    """
    Decomposes complex tasks into executable steps.
    
    Features:
    - Keyword-based task classification
    - Dependency detection
    - Priority assignment
    - Time estimation
    - Parallel execution opportunity detection
    """
    
    def __init__(self):
        # Keyword to agent type mapping
        self._keyword_map = {
            AgentType.RESEARCHER.value: [
                "research", "find", "search", "look up", "what is", "who is",
                "when did", "where is", "tell me about", "information on",
                "fetch", "retrieve", "gather", "collect", "source"
            ],
            AgentType.CODER.value: [
                "code", "script", "program", "execute", "run", "calculate",
                "compute", "python", "function", "implement", "write code",
                "solve", "algorithm", "data structure"
            ],
            AgentType.ANALYST.value: [
                "analyze", "compare", "contrast", "evaluate", "assess",
                "review", "examine", "inspect", "audit", "check",
                "validate", "verify", "test", "benchmark"
            ],
            AgentType.WRITER.value: [
                "write", "compose", "draft", "summarize", "synthesize",
                "explain", "describe", "report", "document", "outline",
                "format", "present", "organize", "structure"
            ]
        }
        
        # Complexity triggers
        self._complexity_triggers = {
            "high": ["comprehensive", "thorough", "detailed", "full", "complete", "deep", "extensive"],
            "medium": ["basic", "simple", "quick", "brief", "short"],
            "research": ["multiple sources", "cross-reference", "verify", "fact-check"],
            "code": ["debug", "refactor", "optimize", "test", "document"]
        }
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def create_plan(self, task: str, context: Optional[str] = None) -> ExecutionPlan:
        """
        Create an execution plan for a task.
        
        Args:
            task: User task description
            context: Additional context (optional)
        
        Returns:
            ExecutionPlan with ordered steps
        """
        task_lower = task.lower()
        
        # Detect task type and complexity
        task_type = self._detect_task_type(task_lower)
        complexity = self._detect_complexity(task_lower)
        
        # Generate steps based on task type
        if task_type == "research":
            steps = self._plan_research_task(task, complexity)
        elif task_type == "code":
            steps = self._plan_code_task(task, complexity)
        elif task_type == "analysis":
            steps = self._plan_analysis_task(task, complexity)
        elif task_type == "mixed":
            steps = self._plan_mixed_task(task, complexity)
        else:
            steps = self._plan_general_task(task, complexity)
        
        # Create metadata
        metadata = {
            "task_type": task_type,
            "complexity": complexity,
            "created_at": None,  # Will be set by caller
            "context": context[:200] if context else None
        }
        
        return ExecutionPlan(task=task, steps=steps, metadata=metadata)
    
    def create_plan_from_json(self, json_plan: str) -> ExecutionPlan:
        """
        Create an execution plan from JSON.
        
        Args:
            json_plan: JSON string representing a plan
        
        Returns:
            ExecutionPlan instance
        """
        return ExecutionPlan.from_json(json_plan)
    
    def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Optimize a plan for parallel execution.
        
        - Identifies steps that can run in parallel
        - Reorders steps for efficiency
        - Merges compatible steps
        
        Args:
            plan: Original execution plan
        
        Returns:
            Optimized execution plan
        """
        optimized_steps = []
        
        # Group steps that have no dependencies
        independent_steps = [step for step in plan.steps if not step.dependencies]
        
        # Sort by priority (higher priority first)
        independent_steps.sort(key=lambda x: x.priority)
        
        # Add independent steps first
        optimized_steps.extend(independent_steps)
        
        # Add dependent steps in order
        dependent_steps = [step for step in plan.steps if step.dependencies]
        optimized_steps.extend(dependent_steps)
        
        return ExecutionPlan(
            task=plan.task,
            steps=optimized_steps,
            metadata={**plan.metadata, "optimized": True}
        )
    
    def validate_plan(self, plan: ExecutionPlan) -> Tuple[bool, List[str]]:
        """
        Validate a plan for correctness.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for circular dependencies
        if self._has_circular_dependencies(plan):
            errors.append("Circular dependency detected in plan")
        
        # Check all agent types are valid
        valid_agents = AgentType.get_all()
        for step in plan.steps:
            if step.agent_type not in valid_agents:
                errors.append(f"Invalid agent type: {step.agent_type}")
        
        # Check step IDs are unique
        step_ids = [step.id for step in plan.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Duplicate step IDs detected")
        
        # Check dependencies reference existing steps
        existing_ids = set(step_ids)
        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in existing_ids:
                    errors.append(f"Step '{step.id}' depends on non-existent step '{dep}'")
        
        return len(errors) == 0, errors
    
    def get_plan_summary(self, plan: ExecutionPlan) -> str:
        """
        Get a human-readable summary of a plan.
        
        Args:
            plan: Execution plan
        
        Returns:
            Formatted summary string
        """
        lines = [
            f"## Task: {plan.task[:100]}",
            f"**Total Steps:** {plan.total_steps}",
            f"**Estimated Time:** {plan.estimated_total_time} seconds",
            f"**Agents:** {', '.join(plan.agent_types_used)}",
            "",
            "### Steps:"
        ]
        
        for i, step in enumerate(plan.steps, 1):
            icon = AgentType.get_icon(step.agent_type)
            deps = f" (depends on: {', '.join(step.dependencies)})" if step.dependencies else ""
            lines.append(f"{i}. {icon} **{step.agent_type}**: {step.description}{deps}")
        
        return "\n".join(lines)
    
    # ========================================================================
    # Private Methods - Task Detection
    # ========================================================================
    
    def _detect_task_type(self, task: str) -> str:
        """Detect the primary type of task."""
        scores = {
            "research": 0,
            "code": 0,
            "analysis": 0,
            "writing": 0
        }
        
        # Score each agent type based on keyword matches
        for agent_type, keywords in self._keyword_map.items():
            for keyword in keywords:
                if keyword in task:
                    scores[agent_type] += 1
        
        # Determine primary type
        max_score = max(scores.values())
        if max_score == 0:
            return "general"
        
        # Count how many types have the max score
        top_types = [t for t, s in scores.items() if s == max_score]
        
        if len(top_types) > 1:
            return "mixed"
        
        return top_types[0]
    
    def _detect_complexity(self, task: str) -> str:
        """Detect task complexity level."""
        task_lower = task.lower()
        
        # Check high complexity triggers
        for trigger in self._complexity_triggers["high"]:
            if trigger in task_lower:
                return "high"
        
        # Check medium complexity triggers
        for trigger in self._complexity_triggers["medium"]:
            if trigger in task_lower:
                return "medium"
        
        # Check research-specific complexity
        for trigger in self._complexity_triggers["research"]:
            if trigger in task_lower:
                return "high"
        
        # Check code-specific complexity
        for trigger in self._complexity_triggers["code"]:
            if trigger in task_lower:
                return "high"
        
        # Default to low complexity
        return "low"
    
    # ========================================================================
    # Private Methods - Plan Generation
    # ========================================================================
    
    def _plan_research_task(self, task: str, complexity: str) -> List[PlanStep]:
        """Generate plan for research tasks."""
        steps = []
        
        # Step 1: Research/Information Gathering
        depth = 3 if complexity == "high" else 2 if complexity == "medium" else 1
        steps.append(PlanStep(
            id="research",
            description=f"Research: {task[:100]} (depth={depth})",
            agent_type=AgentType.RESEARCHER.value,
            dependencies=[],
            estimated_time=45 if complexity == "high" else 30,
            priority=1
        ))
        
        # Step 2: Analysis (for complex tasks)
        if complexity in ["medium", "high"]:
            steps.append(PlanStep(
                id="analysis",
                description=f"Analyze research findings for: {task[:80]}",
                agent_type=AgentType.ANALYST.value,
                dependencies=["research"],
                estimated_time=30,
                priority=2
            ))
        
        # Step 3: Synthesis/Writing
        steps.append(PlanStep(
            id="synthesis",
            description=f"Synthesize findings into final response for: {task[:80]}",
            agent_type=AgentType.WRITER.value,
            dependencies=["analysis"] if complexity in ["medium", "high"] else ["research"],
            estimated_time=25,
            priority=3
        ))
        
        return steps
    
    def _plan_code_task(self, task: str, complexity: str) -> List[PlanStep]:
        """Generate plan for coding tasks."""
        steps = []
        
        # Step 1: Code generation
        steps.append(PlanStep(
            id="code_gen",
            description=f"Write code for: {task[:100]}",
            agent_type=AgentType.CODER.value,
            dependencies=[],
            estimated_time=40 if complexity == "high" else 25,
            priority=1
        ))
        
        # Step 2: Code analysis/review (for complex tasks)
        if complexity in ["medium", "high"]:
            steps.append(PlanStep(
                id="code_review",
                description=f"Review and analyze generated code",
                agent_type=AgentType.ANALYST.value,
                dependencies=["code_gen"],
                estimated_time=20,
                priority=2
            ))
        
        # Step 3: Documentation/Writing
        steps.append(PlanStep(
            id="documentation",
            description=f"Document the solution for: {task[:60]}",
            agent_type=AgentType.WRITER.value,
            dependencies=["code_review"] if complexity in ["medium", "high"] else ["code_gen"],
            estimated_time=20,
            priority=3
        ))
        
        return steps
    
    def _plan_analysis_task(self, task: str, complexity: str) -> List[PlanStep]:
        """Generate plan for analysis tasks."""
        steps = []
        
        # Step 1: Data gathering (if needed)
        if "compare" in task.lower() or "multiple" in task.lower():
            steps.append(PlanStep(
                id="gather",
                description=f"Gather information/data for: {task[:80]}",
                agent_type=AgentType.RESEARCHER.value,
                dependencies=[],
                estimated_time=35,
                priority=1
            ))
        
        # Step 2: Analysis
        analysis_deps = ["gather"] if steps else []
        steps.append(PlanStep(
            id="analyze",
            description=f"Analyze and evaluate: {task[:80]}",
            agent_type=AgentType.ANALYST.value,
            dependencies=analysis_deps,
            estimated_time=40 if complexity == "high" else 25,
            priority=2 if analysis_deps else 1
        ))
        
        # Step 3: Summary/Report
        steps.append(PlanStep(
            id="report",
            description=f"Summarize analysis findings",
            agent_type=AgentType.WRITER.value,
            dependencies=["analyze"],
            estimated_time=25,
            priority=3
        ))
        
        return steps
    
    def _plan_mixed_task(self, task: str, complexity: str) -> List[PlanStep]:
        """Generate plan for mixed/complex tasks."""
        steps = []
        
        # Step 1: Research
        steps.append(PlanStep(
            id="research",
            description=f"Research: {task[:100]}",
            agent_type=AgentType.RESEARCHER.value,
            dependencies=[],
            estimated_time=50 if complexity == "high" else 35,
            priority=1
        ))
        
        # Step 2: Code (if code-related keywords present)
        if any(word in task.lower() for word in self._keyword_map[AgentType.CODER.value]):
            steps.append(PlanStep(
                id="code",
                description=f"Implement solution",
                agent_type=AgentType.CODER.value,
                dependencies=["research"],
                estimated_time=45 if complexity == "high" else 30,
                priority=2
            ))
        
        # Step 3: Analysis
        steps.append(PlanStep(
            id="analysis",
            description=f"Analyze findings and code",
            agent_type=AgentType.ANALYST.value,
            dependencies=["code"] if any(s.id == "code" for s in steps) else ["research"],
            estimated_time=35,
            priority=3
        ))
        
        # Step 4: Final Synthesis
        steps.append(PlanStep(
            id="final",
            description=f"Synthesize final comprehensive response",
            agent_type=AgentType.WRITER.value,
            dependencies=["analysis"],
            estimated_time=30,
            priority=4
        ))
        
        return steps
    
    def _plan_general_task(self, task: str, complexity: str) -> List[PlanStep]:
        """Generate plan for general tasks."""
        steps = []
        
        # Simple single-step plan for general tasks
        steps.append(PlanStep(
            id="process",
            description=f"Process and respond to: {task[:100]}",
            agent_type=AgentType.WRITER.value,
            dependencies=[],
            estimated_time=20,
            priority=1
        ))
        
        return steps
    
    # ========================================================================
    # Private Methods - Validation Helpers
    # ========================================================================
    
    def _has_circular_dependencies(self, plan: ExecutionPlan) -> bool:
        """Check for circular dependencies in the plan."""
        visited = set()
        recursion_stack = set()
        
        def dfs(step_id: str) -> bool:
            visited.add(step_id)
            recursion_stack.add(step_id)
            
            # Find the step
            step = next((s for s in plan.steps if s.id == step_id), None)
            if step:
                for dep in step.dependencies:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in recursion_stack:
                        return True
            
            recursion_stack.discard(step_id)
            return False
        
        for step in plan.steps:
            if step.id not in visited:
                if dfs(step.id):
                    return True
        
        return False


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_planner_instance: Optional[TaskPlanner] = None


def get_planner() -> TaskPlanner:
    """Get the singleton TaskPlanner instance."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = TaskPlanner()
    return _planner_instance


def create_plan(task: str, context: Optional[str] = None) -> ExecutionPlan:
    """Convenience function to create a plan for a task."""
    planner = get_planner()
    return planner.create_plan(task, context)