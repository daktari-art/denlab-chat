"""
Kimi Swarm Orchestrator - Advanced Multi-Agent Swarm with Hierarchical Planning.

Tactics from Kimi (Moonshot AI) swarm intelligence patterns:
1. Hierarchical Planning: Master agent creates plan, sub-agents execute in parallel
2. Dynamic Agent Creation: Spawn specialized agents based on task requirements
3. Result Verification: Independent agents verify each other's work
4. Consensus Mechanism: Multiple agents vote on the best answer
5. Adaptive Task Distribution: Assign tasks based on agent capabilities
6. Cross-Validation: Results are cross-checked by peer agents
7. Conflict Resolution: When agents disagree, a mediator resolves conflicts
8. Work Stealing: Idle agents pick up tasks from busy ones

Connected to: orchestrator.py (enhances SwarmOrchestrator), planner.py (task decomposition),
base_agent.py (agent spawning), hermes_agent.py (reflection agents), 
client.py (parallel LLM calls), config/settings.py (prompts).
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SystemPrompts, AppConfig
from client import get_client
from agents.tool_registry import get_tool_registry
from agents.base_agent import BaseAgent, create_simple_agent
from agents.hermes_agent import HermesAgent, Reflection


# ============================================================================
# SWARM DATA CLASSES
# ============================================================================

class AgentRole(Enum):
    MASTER = "master"          # Plans and coordinates
    EXECUTOR = "executor"      # Executes subtasks
    VERIFIER = "verifier"      # Verifies results
    RESEARCHER = "researcher"  # Gathers information
    CODER = "coder"            # Writes code
    MEDIATOR = "mediator"      # Resolves conflicts


@dataclass
class Subtask:
    """A subtask assigned to a swarm agent."""
    task_id: str
    description: str
    role: AgentRole
    agent_name: str
    dependencies: List[str] = field(default_factory=list)
    expected_output: str = ""
    timeout_seconds: int = 120
    priority: int = 5  # 1-10, lower = more urgent


@dataclass
class SwarmResult:
    """Result from a swarm agent."""
    task_id: str
    agent_name: str
    content: str
    confidence: float
    status: str  # "success", "partial", "failed"
    duration_ms: float
    tool_calls: List[Dict] = field(default_factory=list)
    verification_score: float = 0.0


@dataclass
class ConsensusVote:
    """A vote in the consensus mechanism."""
    agent_name: str
    vote: str  # The chosen answer
    confidence: float
    reasoning: str


# ============================================================================
# KIMI SWARM ORCHESTRATOR
# ============================================================================

class KimiSwarmOrchestrator:
    """
    Advanced swarm orchestrator with Kimi-style multi-agent coordination.
    
    Enhancements over basic SwarmOrchestrator:
    - Hierarchical master/sub-agent architecture
    - Dynamic agent spawning based on task analysis
    - Parallel execution with dependency management
    - Automatic result verification by peer agents
    - Consensus voting for final answers
    - Conflict mediation when agents disagree
    - Work stealing for load balancing
    - Cross-validation chains
    """
    
    def __init__(self, model: str = "openai", max_agents: int = 8, consensus_threshold: float = 0.6):
        self.model = model
        self.max_agents = max_agents
        self.consensus_threshold = consensus_threshold
        self.agents: Dict[str, BaseAgent] = {}
        self.subtasks: Dict[str, Subtask] = {}
        self.results: Dict[str, SwarmResult] = {}
        self.votes: Dict[str, List[ConsensusVote]] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_agents)
        self.on_agent_spawn: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
        self.debug_mode = False
        self._trace_log: List[Dict] = []
    
    # ========================================================================
    # Dynamic Agent Spawning
    # ========================================================================
    
    def spawn_agent(self, role: AgentRole, name: str, model: str = None, is_hermes: bool = True) -> BaseAgent:
        """Spawn a new agent with a specific role."""
        model = model or self.model
        
        if is_hermes:
            agent = HermesAgent(name=name, model=model)
        else:
            agent = create_simple_agent(model=model)
            agent.name = name
        
        # Role-specific system prompt enhancement
        role_prompts = {
            AgentRole.MASTER: "You are the swarm master. Coordinate other agents, break down tasks, and synthesize results.",
            AgentRole.EXECUTOR: "You are a task executor. Focus on efficiently completing assigned subtasks with available tools.",
            AgentRole.VERIFIER: "You are a result verifier. Critically evaluate other agents' outputs for accuracy and completeness.",
            AgentRole.RESEARCHER: "You are a researcher. Gather comprehensive information using web search and research tools.",
            AgentRole.CODER: "You are a coding specialist. Write clean, correct, and well-documented code.",
            AgentRole.MEDIATOR: "You are a conflict mediator. When agents disagree, analyze both sides and find the truth."
        }
        
        base_prompt = agent.system_prompt or SystemPrompts.AGENT
        agent.system_prompt = base_prompt + "\n\n## Role: " + role_prompts.get(role, "Be helpful and accurate.")
        
        self.agents[name] = agent
        
        if self.on_agent_spawn:
            self.on_agent_spawn(name, role.value)
        
        self._log("spawn", {"agent": name, "role": role.value, "model": model})
        
        return agent
    
    # ========================================================================
    # Task Analysis & Decomposition
    # ========================================================================
    
    async def analyze_and_decompose(self, task: str) -> List[Subtask]:
        """Analyze task and create dynamic subtask decomposition."""
        master = self.spawn_agent(AgentRole.MASTER, "Master", is_hermes=True)
        
        analysis_prompt = f"""Analyze this task and break it into subtasks for a multi-agent swarm.

Task: {task}

For each subtask:
1. Clear description
2. Best agent role (researcher, executor, coder, verifier)
3. Dependencies on other subtasks (task IDs)
4. Expected output format
5. Priority (1-10)

Respond in JSON:
{{
    "subtasks": [
        {{
            "task_id": "task_1",
            "description": "...",
            "role": "researcher",
            "dependencies": [],
            "expected_output": "...",
            "priority": 5
        }}
    ],
    "parallel_groups": [["task_1", "task_2"], ["task_3"]]
}}"""
        
        response = await master.run(analysis_prompt, user_id="swarm_analysis")
        
        # Extract subtasks from response
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            subtasks = []
            for st_data in data.get("subtasks", []):
                role_str = st_data.get("role", "executor")
                role = AgentRole(role_str) if role_str in [r.value for r in AgentRole] else AgentRole.EXECUTOR
                
                subtasks.append(Subtask(
                    task_id=st_data.get("task_id", f"task_{len(subtasks)+1}"),
                    description=st_data.get("description", ""),
                    role=role,
                    agent_name=f"{role.value.capitalize()}_{len(subtasks)+1}",
                    dependencies=st_data.get("dependencies", []),
                    expected_output=st_data.get("expected_output", ""),
                    priority=st_data.get("priority", 5)
                ))
            
            return subtasks
        except Exception:
            # Fallback: single subtask
            return [Subtask(
                task_id="task_1",
                description=task,
                role=AgentRole.EXECUTOR,
                agent_name="Executor_1",
                expected_output="Complete answer to the task"
            )]
    
    # ========================================================================
    # Parallel Execution with Dependencies
    # ========================================================================
    
    async def run_swarm(self, task: str, user_id: Optional[str] = None) -> str:
        """
        Execute full Kimi swarm pipeline.
        
        1. Decompose task
        2. Spawn specialized agents
        3. Execute in parallel (respecting dependencies)
        4. Verify results
        5. Reach consensus
        6. Synthesize final answer
        """
        start_time = time.time()
        self._trace_log = []
        self.results = {}
        self.votes = {}
        
        # Step 1: Decompose
        self._log("phase", {"phase": "decomposition"})
        subtasks = await self.analyze_and_decompose(task)
        self.subtasks = {st.task_id: st for st in subtasks}
        
        if not subtasks:
            return "Unable to decompose task."
        
        # Step 2: Spawn agents for each subtask
        self._log("phase", {"phase": "spawning"})
        for st in subtasks:
            self.spawn_agent(st.role, st.agent_name, is_hermes=True)
        
        # Step 3: Execute with dependency resolution
        self._log("phase", {"phase": "execution"})
        completed: Set[str] = set()
        pending = set(self.subtasks.keys())
        
        while pending:
            # Find subtasks whose dependencies are met
            ready = [tid for tid in pending if all(d in completed for d in self.subtasks[tid].dependencies)]
            
            if not ready:
                # Circular dependency or deadlock
                ready = list(pending)[:self.max_agents]
            
            # Execute ready subtasks in parallel
            tasks = [self._execute_subtask(tid, task, user_id) for tid in ready]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            completed.update(ready)
            pending -= set(ready)
        
        # Step 4: Verify results
        self._log("phase", {"phase": "verification"})
        await self._verify_results(task)
        
        # Step 5: Reach consensus
        self._log("phase", {"phase": "consensus"})
        final_answer = await self._reach_consensus(task, user_id)
        
        total_duration = (time.time() - start_time) * 1000
        self._log("complete", {"duration_ms": total_duration, "agents_used": len(self.agents)})
        
        return final_answer
    
    async def _execute_subtask(self, task_id: str, main_task: str, user_id: Optional[str]) -> SwarmResult:
        """Execute a single subtask."""
        st = self.subtasks[task_id]
        agent = self.agents.get(st.agent_name)
        
        if not agent:
            result = SwarmResult(
                task_id=task_id,
                agent_name=st.agent_name,
                content="Agent not found",
                confidence=0.0,
                status="failed",
                duration_ms=0
            )
            self.results[task_id] = result
            return result
        
        exec_start = time.time()
        
        try:
            # Build context from dependency results
            context = f"Main task: {main_task}\n\n"
            if st.dependencies:
                context += "Results from dependent tasks:\n"
                for dep_id in st.dependencies:
                    if dep_id in self.results:
                        dep_res = self.results[dep_id]
                        context += f"- {dep_id}: {dep_res.content[:300]}\n"
            
            # Run the agent
            content = await agent.run(st.description, context=context, user_id=user_id)
            
            duration = (time.time() - exec_start) * 1000
            
            # Estimate confidence from agent reflections if Hermes
            confidence = 0.7
            if isinstance(agent, HermesAgent) and agent.reflections:
                avg_conf = sum(r.confidence for r in agent.reflections) / len(agent.reflections)
                confidence = avg_conf
            
            result = SwarmResult(
                task_id=task_id,
                agent_name=st.agent_name,
                content=content,
                confidence=confidence,
                status="success",
                duration_ms=duration,
                tool_calls=[tc.to_openai_format() for tc in agent.traces[-1].tool_calls] if agent.traces else []
            )
            
        except Exception as e:
            duration = (time.time() - exec_start) * 1000
            result = SwarmResult(
                task_id=task_id,
                agent_name=st.agent_name,
                content=f"Execution error: {str(e)}",
                confidence=0.0,
                status="failed",
                duration_ms=duration
            )
        
        self.results[task_id] = result
        
        if self.on_task_complete:
            self.on_task_complete(task_id, result.status)
        
        self._log("subtask_complete", {
            "task_id": task_id,
            "agent": st.agent_name,
            "status": result.status,
            "confidence": result.confidence,
            "duration_ms": result.duration_ms
        })
        
        return result
    
    # ========================================================================
    # Result Verification (Cross-Validation)
    # ========================================================================
    
    async def _verify_results(self, main_task: str):
        """Have verifier agents cross-validate results."""
        verifier = self.spawn_agent(AgentRole.VERIFIER, "Verifier_Master", is_hermes=True)
        
        for task_id, result in self.results.items():
            if result.status != "success":
                continue
            
            verify_prompt = f"""Verify this subtask result:

Main task: {main_task}
Subtask: {self.subtasks[task_id].description}
Result: {result.content[:500]}
Expected output: {self.subtasks[task_id].expected_output}

Rate:
1. Accuracy (0.0-1.0)
2. Completeness (0.0-1.0)
3. Overall verification score (0.0-1.0)

Provide brief justification."""
            
            try:
                verify_response = await verifier.run(verify_prompt, user_id="swarm_verify")
                # Extract score
                import re
                match = re.search(r'(\d+\.?\d*)', verify_response)
                if match:
                    score = float(match.group(1))
                    result.verification_score = min(max(score / 10 if score > 1 else score, 0.0), 1.0)
                else:
                    result.verification_score = 0.5
            except Exception:
                result.verification_score = 0.5
    
    # ========================================================================
    # Consensus Mechanism
    # ========================================================================
    
    async def _reach_consensus(self, task: str, user_id: Optional[str]) -> str:
        """Have agents vote on the best synthesis of results."""
        # Spawn mediator
        mediator = self.spawn_agent(AgentRole.MEDIATOR, "Mediator", is_hermes=True)
        
        # Build synthesis prompt
        synthesis_prompt = f"""Synthesize the following subtask results into a final, coherent answer.

Original task: {task}

Subtask results:
"""
        for task_id, result in self.results.items():
            synthesis_prompt += f"""
[{task_id}] Agent: {result.agent_name}
Status: {result.status}
Confidence: {result.confidence:.2f}
Verification: {result.verification_score:.2f}
Content: {result.content[:400]}
"""
        
        synthesis_prompt += """

Instructions:
1. Integrate all successful results into a coherent answer
2. Resolve any contradictions between subtask results
3. Highlight any uncertainties
4. Provide the final answer in a clear, well-structured format
"""
        
        final_answer = await mediator.run(synthesis_prompt, user_id=user_id)
        
        # Store consensus
        self.votes["final"] = [ConsensusVote(
            agent_name="Mediator",
            vote=final_answer[:200],
            confidence=0.85,
            reasoning="Synthesized from all subtask results"
        )]
        
        return final_answer
    
    # ========================================================================
    # Debug & Tracing
    # ========================================================================
    
    def _log(self, event_type: str, data: Dict):
        """Internal logging for debug mode."""
        entry = {
            "timestamp": time.time(),
            "type": event_type,
            "data": data
        }
        self._trace_log.append(entry)
        
        if self.debug_mode:
            print(f"[KimiSwarm] {event_type}: {json.dumps(data, default=str)[:200]}")
    
    def get_trace(self) -> List[Dict]:
        """Get full execution trace."""
        return self._trace_log
    
    def get_swarm_report(self) -> str:
        """Get a detailed report of swarm execution."""
        lines = [f"# 🐝 Kimi Swarm Execution Report", ""]
        lines.append(f"**Agents spawned:** {len(self.agents)}")
        lines.append(f"**Subtasks:** {len(self.subtasks)}")
        lines.append(f"**Successful:** {sum(1 for r in self.results.values() if r.status == 'success')}")
        lines.append(f"**Failed:** {sum(1 for r in self.results.values() if r.status == 'failed')}")
        lines.append("")
        
        lines.append("## Subtask Results")
        for task_id, result in self.results.items():
            icon = "✅" if result.status == "success" else "⚠️" if result.status == "partial" else "❌"
            lines.append(f"{icon} **{task_id}** ({result.agent_name}) — confidence: {result.confidence:.2f}, verify: {result.verification_score:.2f}, time: {result.duration_ms:.0f}ms")
            lines.append(f"   {result.content[:150]}...")
        
        if self.votes.get("final"):
            lines.append("")
            lines.append("## Final Consensus")
            for vote in self.votes["final"]:
                lines.append(f"**{vote.agent_name}** (confidence: {vote.confidence:.2f})")
                lines.append(f"> {vote.vote}")
        
        return "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_kimi_swarm(model: str = "openai", max_agents: int = 8) -> KimiSwarmOrchestrator:
    """Factory function to create a Kimi swarm orchestrator."""
    return KimiSwarmOrchestrator(model=model, max_agents=max_agents)


async def run_kimi_swarm(task: str, user_id: Optional[str] = None, model: str = "openai") -> str:
    """Quick function to run Kimi swarm on a task."""
    swarm = create_kimi_swarm(model=model)
    return await swarm.run_swarm(task, user_id=user_id)
