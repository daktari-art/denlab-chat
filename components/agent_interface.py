"""
Agent Interface Components for DenLab Chat.
Displays agent execution traces, swarm status, and progress in the UI.
Pure UI component - no business logic, no API calls.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import from completed files
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui_components import render_agent_progress, render_swarm_progress


# ============================================================================
# AGENT INTERFACE
# ============================================================================

class AgentInterface:
    """
    UI component for displaying agent execution information.
    
    Handles:
    - Agent trace display (step-by-step execution)
    - Tool call details with status icons
    - Swarm execution status
    - Progress indicators
    - Execution logs
    """
    
    def __init__(self):
        self._trace_expander_state = {}
    
    # ========================================================================
    # Trace Display
    # ========================================================================
    
    def render_trace(
        self,
        traces: List[Dict],
        title: str = "Execution Trace",
        expanded: bool = False
    ):
        """
        Render agent execution traces.
        
        Args:
            traces: List of trace dicts with step, thought, tool_calls
            title: Title for the expander
            expanded: Whether the expander is open by default
        """
        if not traces:
            return
        
        with st.expander(f"📋 {title}", expanded=expanded):
            for trace in traces:
                self._render_trace_step(trace)
    
    def _render_trace_step(self, trace: Dict):
        """
        Render a single trace step.
        
        Args:
            trace: Dict with step, thought, tool_calls, provider
        """
        step_num = trace.get("step", "?")
        thought = trace.get("thought", "")
        tool_calls = trace.get("tool_calls", [])
        provider = trace.get("provider", "")
        
        # Determine status icon
        if tool_calls:
            all_success = all(tc.get("status") == "success" for tc in tool_calls)
            has_error = any(tc.get("status") == "error" for tc in tool_calls)
            
            if has_error:
                status_icon = "❌"
                status_color = "#ef4444"
            elif all_success:
                status_icon = "✅"
                status_color = "#10a37f"
            else:
                status_icon = "🔄"
                status_color = "#f59e0b"
        else:
            status_icon = "✅"
            status_color = "#10a37f"
        
        # Step header
        st.markdown(f"""
        <div style="margin: 12px 0 8px 0; padding-bottom: 4px; border-bottom: 1px solid #e8e8e8;">
            <span style="font-weight: 600; font-size: 14px;">{status_icon} Step {step_num}</span>
            <span style="font-size: 11px; color: #999; margin-left: 8px;">{provider}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Thought (if any)
        if thought:
            thought_preview = thought[:300] + "..." if len(thought) > 300 else thought
            st.markdown(f'<div style="font-size: 13px; color: #555; margin: 6px 0 8px 0;">💭 {thought_preview}</div>', unsafe_allow_html=True)
        
        # Tool calls (if any)
        if tool_calls:
            for tc in tool_calls:
                self._render_tool_call(tc)
    
    def _render_tool_call(self, tool_call: Dict):
        """
        Render a single tool call.
        
        Args:
            tool_call: Dict with name, status, result, duration_ms, arguments
        """
        name = tool_call.get("name", "unknown")
        status = tool_call.get("status", "pending")
        result = tool_call.get("result", "")
        duration_ms = tool_call.get("duration_ms", 0)
        arguments = tool_call.get("arguments", {})
        
        # Icon based on status
        if status == "success":
            icon = "✅"
            color = "#10a37f"
        elif status == "error":
            icon = "❌"
            color = "#ef4444"
        else:
            icon = "🔄"
            color = "#f59e0b"
        
        # Tool call header
        st.markdown(f"""
        <div style="margin-left: 20px; margin-top: 6px; margin-bottom: 4px;">
            <span style="font-size: 12px; color: {color};">{icon} <code style="font-size: 12px;">{name}</code></span>
            <span style="font-size: 10px; color: #999;">({duration_ms:.0f}ms)</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Expandable details
        with st.expander(f"Details", expanded=False):
            if arguments:
                st.markdown("**Arguments:**")
                st.json(arguments)
            
            if result:
                st.markdown("**Result:**")
                result_preview = result[:500] + "..." if len(result) > 500 else result
                st.code(result_preview, language="json" if result.startswith("{") else "text")
    
    # ========================================================================
    # Swarm Display
    # ========================================================================
    
    def render_swarm_status(
        self,
        subtasks: Dict[str, Any],
        title: str = "Swarm Execution",
        expanded: bool = False
    ):
        """
        Render swarm execution status.
        
        Args:
            subtasks: Dictionary of sub-task results
            title: Title for the expander
            expanded: Whether the expander is open by default
        """
        if not subtasks:
            return
        
        with st.expander(f"🐝 {title}", expanded=expanded):
            # Summary stats
            total = len(subtasks)
            completed = sum(1 for s in subtasks.values() if s.get("status") == "complete")
            failed = sum(1 for s in subtasks.values() if s.get("status") == "failed")
            running = sum(1 for s in subtasks.values() if s.get("status") == "running")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", total)
            with col2:
                st.metric("✅ Complete", completed)
            with col3:
                st.metric("❌ Failed", failed)
            with col4:
                st.metric("🔄 Running", running)
            
            st.divider()
            
            # Individual sub-tasks
            for step_id, result in subtasks.items():
                self._render_subtask_result(step_id, result)
    
    def _render_subtask_result(self, step_id: str, result: Dict):
        """
        Render a single sub-task result.
        
        Args:
            step_id: Sub-task identifier
            result: Result dict with status, agent_type, description, result, duration_ms
        """
        status = result.get("status", "unknown")
        agent_type = result.get("agent_type", "unknown")
        description = result.get("description", "")
        result_text = result.get("result", "")
        duration_ms = result.get("duration_ms", 0)
        error = result.get("error", "")
        
        # Icon based on status
        icons = {
            "complete": "✅",
            "failed": "❌",
            "running": "🔄",
            "pending": "⏳"
        }
        icon = icons.get(status, "❓")
        
        # Agent icons
        agent_icons = {
            "researcher": "🔍",
            "coder": "💻",
            "analyst": "📊",
            "writer": "✍️"
        }
        agent_icon = agent_icons.get(agent_type, "🤖")
        
        # Status color
        colors = {
            "complete": "#10a37f",
            "failed": "#ef4444",
            "running": "#f59e0b",
            "pending": "#888"
        }
        color = colors.get(status, "#888")
        
        # Header
        st.markdown(f"""
        <div style="margin: 12px 0 8px 0; padding: 8px; background: #fafafa; border-radius: 8px; border-left: 3px solid {color};">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>{icon}</span>
                <span style="font-weight: 600;">{agent_icon} {agent_type.upper()}</span>
                <span style="font-size: 11px; color: #999;">{duration_ms:.0f}ms</span>
            </div>
            <div style="font-size: 12px; color: #666; margin-top: 4px;">{description[:150]}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Expandable result
        if result_text or error:
            with st.expander(f"View Result", expanded=False):
                if error:
                    st.error(f"Error: {error[:500]}")
                else:
                    result_preview = result_text[:1000] + "..." if len(result_text) > 1000 else result_text
                    st.markdown(result_preview)
    
    # ========================================================================
    # Progress Display
    # ========================================================================
    
    def render_step_progress(
        self,
        step: int,
        max_steps: int,
        thought: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None
    ):
        """
        Render real-time step progress.
        
        Args:
            step: Current step number
            max_steps: Maximum steps
            thought: Current thought/reasoning
            tool_calls: Current tool calls
        """
        render_agent_progress(step, max_steps, thought, tool_calls)
    
    def render_swarm_step_progress(
        self,
        current: int,
        total: int,
        agent_type: str,
        description: str
    ):
        """
        Render real-time swarm step progress.
        
        Args:
            current: Current sub-task number
            total: Total sub-tasks
            agent_type: Type of agent
            description: Task description
        """
        render_swarm_progress(current, total, agent_type, description)
    
    # ========================================================================
    # Simple Status
    # ========================================================================
    
    def render_status_message(
        self,
        message: str,
        status: str = "info"
    ):
        """
        Render a simple status message.
        
        Args:
            message: Status message text
            status: "info", "success", "warning", "error"
        """
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icons.get(status, "ℹ️")
        
        colors = {
            "info": "#3b82f6",
            "success": "#10a37f",
            "warning": "#f59e0b",
            "error": "#ef4444"
        }
        color = colors.get(status, "#888")
        
        st.markdown(f"""
        <div style="background: #f8f9fa; border-left: 3px solid {color}; border-radius: 8px; padding: 10px 14px; margin: 8px 0;">
            <span style="font-size: 13px;">{icon} {message}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # Control Buttons
    # ========================================================================
    
    def render_control_buttons(self):
        """
        Render agent control buttons (Show Traces, Auto-execute).
        """
        col1, col2 = st.columns(2)
        
        with col1:
            show_traces = st.toggle(
                "📋 Show Traces",
                value=st.session_state.get("show_agent_traces", True),
                key="show_agent_traces",
                help="Display detailed execution traces"
            )
            st.session_state.show_agent_traces = show_traces
        
        with col2:
            auto_execute = st.toggle(
                "⚡ Auto-execute",
                value=st.session_state.get("agent_auto_execute", False),
                key="agent_auto_execute",
                help="Automatically execute suggested actions"
            )
            st.session_state.agent_auto_execute = auto_execute
    
    def render_swarm_controls(self):
        """
        Render swarm-specific control buttons.
        """
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_parallel = st.number_input(
                "Max Parallel",
                min_value=1,
                max_value=8,
                value=st.session_state.get("swarm_max_parallel", 4),
                key="swarm_max_parallel",
                help="Maximum number of agents running in parallel"
            )
            st.session_state.swarm_max_parallel = max_parallel
        
        with col2:
            show_plan = st.toggle(
                "📋 Show Plan",
                value=st.session_state.get("swarm_show_plan", True),
                key="swarm_show_plan",
                help="Display the execution plan before running"
            )
            st.session_state.swarm_show_plan = show_plan
        
        with col3:
            debug_mode = st.toggle(
                "🐛 Debug Mode",
                value=st.session_state.get("swarm_debug_mode", False),
                key="swarm_debug_mode",
                help="Show detailed debug information"
            )
            st.session_state.swarm_debug_mode = debug_mode


# ============================================================================
# SIMPLE FUNCTIONS (for direct use)
# ============================================================================

def render_trace(traces: List[Dict], title: str = "Execution Trace", expanded: bool = False):
    """Simple function to render traces."""
    interface = AgentInterface()
    interface.render_trace(traces, title, expanded)


def render_swarm_status(subtasks: Dict[str, Any], title: str = "Swarm Execution", expanded: bool = False):
    """Simple function to render swarm status."""
    interface = AgentInterface()
    interface.render_swarm_status(subtasks, title, expanded)


def render_step_progress(step: int, max_steps: int, thought: Optional[str] = None, tool_calls: Optional[List[Dict]] = None):
    """Simple function to render step progress."""
    interface = AgentInterface()
    interface.render_step_progress(step, max_steps, thought, tool_calls)


def render_swarm_step_progress(current: int, total: int, agent_type: str, description: str):
    """Simple function to render swarm step progress."""
    interface = AgentInterface()
    interface.render_swarm_step_progress(current, total, agent_type, description)


def render_status_message(message: str, status: str = "info"):
    """Simple function to render status message."""
    interface = AgentInterface()
    interface.render_status_message(message, status)


def should_show_traces() -> bool:
    """Check if traces should be shown."""
    return st.session_state.get("show_agent_traces", True)


def get_swarm_config() -> Dict[str, Any]:
    """Get current swarm configuration."""
    return {
        "max_parallel": st.session_state.get("swarm_max_parallel", 4),
        "show_plan": st.session_state.get("swarm_show_plan", True),
        "debug_mode": st.session_state.get("swarm_debug_mode", False)
    }

# ============================================================================
# BACKWARD COMPATIBILITY FUNCTION
# ============================================================================

def render_agent_interface():
    """Placeholder agent interface for backward compatibility."""
    import streamlit as st
    st.markdown("### 🤖 Agent Interface")
    st.info("Agent mode is active. The chat will use tools autonomously.")
