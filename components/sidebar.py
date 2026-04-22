"""Sidebar component - Kimi-inspired clean design."""
import streamlit as st
from core.session_manager import SessionManager
from config.settings import MODELS

class Sidebar:
    """Clean sidebar with model switching, agent mode, and session management."""
    
    def __init__(self):
        self.sessions = SessionManager()
    
    def render(self):
        with st.sidebar:
            # Clean header
            st.markdown("""
            <div style="border-bottom: 1px solid #222; padding-bottom: 12px; margin-bottom: 12px;">
                <h1 style="font-size: 16px; margin: 0; color: #fff; font-weight: 700;">DenLab Chat</h1>
                <p style="font-size: 11px; color: #666; margin: 4px 0 0 0;">Kimi-inspired AI</p>
            </div>
            """, unsafe_allow_html=True)
            
            # New session
            if st.button("+ New Session", use_container_width=True, type="primary"):
                self.sessions.create_session()
                st.rerun()
            
            st.divider()
            
            # Model selector - compact
            st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Model</p>', unsafe_allow_html=True)
            
            session = self.sessions.get_current()
            model_names = list(MODELS.keys())
            model_values = [MODELS[m]["name"] for m in model_names]
            current = model_values.index(session.model) if session.model in model_values else 0
            choice = st.selectbox("", model_names, index=current, label_visibility="collapsed")
            session.model = MODELS[choice]["name"]
            
            # Agent mode toggle
            st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 12px 0 6px;">Agent Mode</p>', unsafe_allow_html=True)
            
            agent_col1, agent_col2 = st.columns([3, 1])
            with agent_col1:
                st.markdown("""
                <div class="agent-badge" style="margin-top:4px;">
                    <div class="agent-dot"></div>
                    <span>Agent</span>
                </div>
                """, unsafe_allow_html=True)
            with agent_col2:
                agent_mode = st.toggle("", value=st.session_state.get("agent_mode", False), label_visibility="collapsed", key="sidebar_agent_toggle")
                st.session_state.agent_mode = agent_mode
            
            st.divider()
            
            # Sessions
            st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Sessions</p>', unsafe_allow_html=True)
            
            for sid, data in st.session_state.sessions.items():
                col1, col2 = st.columns([0.85, 0.15])
                display = data['name'][:22] + "..." if len(data['name']) > 22 else data['name']
                with col1:
                    if st.button(f"{display}", key=f"load_{sid}", use_container_width=True):
                        st.session_state.current_session = sid
                        st.rerun()
                with col2:
                    if st.button("", key=f"del_{sid}", help="Delete", icon="✕"):
                        self.sessions.delete(sid)
                        st.rerun()
            
            # Export
            st.divider()
            if st.button("Export Chat", use_container_width=True):
                session = self.sessions.get_current()
                text = "\n\n".join([f"**{m['role']}**: {m['content']}" 
                                  for m in session.messages if m['role'] != 'system'])
                st.download_button("Download", text, "chat.md", use_container_width=True)
            
            self.sessions.update(session)
