"""Session management."""
import uuid
import time
from typing import Dict, List
import streamlit as st
from config.models import Session, ChatMessage, MessageRole

class SessionManager:
    def __init__(self):
        if "sessions" not in st.session_state:
            st.session_state.sessions = {}
        if "current_session" not in st.session_state:
            self.create_session("Main")
    
    def create_session(self, name: str = "New Session") -> str:
        sid = str(uuid.uuid4())
        session = Session(id=sid, name=name)
        session.messages.append(ChatMessage(role=MessageRole.SYSTEM, 
                                          content="You are DenLab..."))
        st.session_state.sessions[sid] = session.model_dump()
        st.session_state.current_session = sid
        return sid
    
    def get_current(self) -> Session:
        sid = st.session_state.current_session
        data = st.session_state.sessions.get(sid, {})
        return Session(**data) if data else self.create_session("Recovery")
    
    def update(self, session: Session):
        st.session_state.sessions[session.id] = session.model_dump()
    
    def delete(self, sid: str):
        if sid in st.session_state.sessions:
            del st.session_state.sessions[sid]
            if st.session_state.current_session == sid:
                remaining = list(st.session_state.sessions.keys())
                st.session_state.current_session = remaining[0] if remaining else self.create_session("Main")
