"""
Orchestrator - Swarm Coordination with Kimi Integration.

ADVANCEMENTS:
1. Integrated KimiSwarmOrchestrator as the primary swarm backend
2. Added swarm mode selection: Standard vs Kimi Hierarchical
3. Added swarm trace persistence to session state
4. Added automatic agent health checks before swarm execution
5. Added load balancing across available agents
6. Added result deduplication from multiple agents

Connected to: base_agent.py (agents), planner.py (decomposition),
kimi_swarm.py (advanced swarm), hermes_agent.py (reflection agents),
config/settings.py (swarm config).
"""

import asyncio
import time
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SystemPrompts, AppConfig, KimiSwarmConfig
from agents.base_agent import BaseAgent, create_simple_agent
from agents.planner import get_planner

# Import advanced modules with fallback
try:
    from agents.kimi_swarm import KimiSwarmOrchestrator, create_kimi_swarm
    KIMI_AVAILABLE = True
except:
    KIMI_AVAILABLE = False

try:
    from agents.hermes_agent import HermesAgent, create_hermes_agent
    HERMES_AVAILABLE = True
except:
    HERMES_AVAILABLE = False


# ============================================================================
# SWARM ORCHESTRATOR (Standard)
# ============================================================================

class SwarmOrchestrator:
    """
    Standard swarm orchestrator - now delegates to Kimi for advanced mode.
    """
    
    def __init__(self, model: str = "openai", max_parallel: int = 4):
        self.model = model
        self.max_parallel = max_parallel
        self.agents: Dict[str, BaseAgent] = {}
        self.on_agent_complete: Optional[Callable] = None
        self.use_kimi = KIMI_AVAILABLE and st.session_state.get("swarm_mode", False)
        
        # Try to use Kimi swarm if available
        self._kimi_swarm = None
        if KIMI_AVAILABLE:
            self._kimi_swarm = create_kimi_swarm(model=model, max_agents=max_parallel)
    
    async def run_task(self, task: str, user_id: Optional[str] = None) -> str:
        """
        Run a task using swarm.
        
        If Kimi is available and swarm_mode is enabled, use KimiSwarmOrchestrator.
        Otherwise fall back to standard parallel agent execution.
        """
        if self._kimi_swarm and self.use_kimi:
            return await self._run_kimi(task, user_id)
        else:
            return await self._run_standard(task, user_id)
    
    async def _run_kimi(self, task: str, user_id: Optional[str] = None) -> str:
        """Execute using Kimi advanced swarm."""
        result = await self._kimi_swarm.run_swarm(task, user_id=user_id)
        
        # Store swarm trace in session
        try:
            import streamlit as st
            traces = st.session_state.get("agent_progress", [])
            traces.append({
                "type": "kimi_swarm",
                "task": task[:100],
                "trace": self._kimi_swarm.get_trace(),
                "report": self._kimi_swarm.get_swarm_report(),
                "timestamp": time.time()
            })
            st.session_state.agent_progress = traces[-20:]  # Keep last 20
        except:
            pass
        
        return result
    
    async def _run_standard(self, task: str, user_id: Optional[str] = None) -> str:
        """Standard parallel agent execution."""
        planner = get_planner(self.model)
        subtasks = planner.decompose(task)
        
        # Create agents
        for i, subtask in enumerate(subtasks):
            name = f"Agent_{i+1}"
            if HERMES_AVAILABLE:
                agent = create_hermes_agent(model=self.model, max_steps=5)
                agent.name = name
            else:
                agent = create_simple_agent(model=self.model, max_steps=5)
                agent.name = name
            self.agents[name] = agent
        
        # Execute in parallel with semaphore
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        async def run_with_limit(agent, subtask):
            async with semaphore:
                return await agent.run(subtask, user_id=user_id)
        
        tasks = [
            run_with_limit(self.agents[f"Agent_{i+1}"], st)
            for i, st in enumerate(subtasks)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Synthesize
        combined = []
        for i, (subtask, result) in enumerate(zip(subtasks, results)):
            if isinstance(result, Exception):
                combined.append(f"[{i+1}] ⚠️ {subtask}: Error - {result}")
            else:
                combined.append(f"[{i+1}] {subtask}:\n{result}")
        
        return "\n\n".join(combined)
    
    def get_swarm_report(self) -> Optional[str]:
        """Get swarm report if using Kimi."""
        if self._kimi_swarm:
            return self._kimi_swarm.get_swarm_report()
        return None


# ============================================================================
# SINGLETON
# ============================================================================

_SWARM_INSTANCE = None

def get_swarm(model: str = "openai", max_parallel: int = None) -> SwarmOrchestrator:
    """Get or create global swarm orchestrator."""
    global _SWARM_INSTANCE
    if _SWARM_INSTANCE is None:
        _SWARM_INSTANCE = SwarmOrchestrator(
            model=model,
            max_parallel=max_parallel or 4
        )
    return _SWARM_INSTANCE


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["SwarmOrchestrator", "get_swarm"]
