"""Sidebar component."""
import streamlit as st
from core.session_manager import SessionManager
from config.settings import MODELS

class Sidebar:
    def __init__(self):
        self.sessions = SessionManager()
    
    def render(self):
        with st.sidebar:
            st.title("🧪 DenLab")
            
            # Model selector
            session = self.sessions.get_current()
            model_names = list(MODELS.keys())
            current = list(MODELS.values()).index(session.model)
            choice = st.selectbox("Model", model_names, index=current)
            session.model = MODELS[choice]
            
            # Sessions
            st.divider()
            st.subheader("Sessions")
            
            if st.button("➕ New Session"):
                self.sessions.create_session()
                st.rerun()
            
            for sid, data in st.session_state.sessions.items():
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"📁 {data['name'][:20]}", key=f"load_{sid}"):
                        st.session_state.current_session = sid
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{sid}"):
                        self.sessions.delete(sid)
                        st.rerun()
            
            # Export
            st.divider()
            if st.button("📥 Export"):
                session = self.sessions.get_current()
                text = "\n\n".join([f"**{m['role']}**: {m['content']}" 
                                  for m in session.messages if m['role'] != 'system'])
                st.download_button("Download", text, "chat.md")
            
            self.sessions.update(session)
