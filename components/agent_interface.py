"""Agent UI components for Streamlit."""
import streamlit as st
from typing import List, Dict, Any
from agents.base_agent import AgentTrace

class AgentInterface:
    """Render agent execution traces and controls."""
    
    @staticmethod
    def render_trace_card(trace: AgentTrace):
        """Render a single trace step."""
        with st.container():
            st.markdown(f"**Step {trace.step}**")
            
            if trace.thought:
                st.markdown(f"💭 *{trace.thought[:200]}...*" if len(trace.thought) > 200 else f"💭 *{trace.thought}*")
            
            for tc in trace.tool_calls:
                icon = "✅" if tc.status == "success" else "❌" if tc.status == "error" else "🔄"
                
                with st.expander(f"{icon} `{tc.name}` ({tc.duration_ms:.0f}ms)", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Arguments:**")
                        st.json(tc.arguments)
                    with col2:
                        st.markdown("**Result:**")
                        st.text(str(tc.result)[:500])
    
    @staticmethod
    def render_swarm_status(subtasks: Dict[str, Any]):
        """Render swarm execution status."""
        if not subtasks:
            return
        
        cols = st.columns(min(len(subtasks), 3))
        for idx, (st_id, st_data) in enumerate(subtasks.items()):
            with cols[idx % 3]:
                status = st_data.get("status", "unknown")
                icon = {
                    "complete": "✅",
                    "failed": "❌",
                    "running": "🔄",
                    "pending": "⏳"
                }.get(status, "⏳")
                
                duration = st_data.get("duration", 0)
                st.metric(
                    label=f"{icon} {st_id}",
                    value=f"{duration:.1f}s" if duration else status.upper(),
                    delta=status
                )
    
    @staticmethod
    def render_agent_controls():
        """Render agent mode controls."""
        col1, col2 = st.columns(2)
        with col1:
            st.toggle("Show Traces", key="show_agent_traces", value=True)
        with col2:
            st.toggle("Auto-execute", key="agent_auto", value=False)
