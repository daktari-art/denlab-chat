"""
Floating Menu Component for DenLab Chat.
Simple inline menu using Streamlit expander - reliable on all platforms.
"""

import streamlit as st
import html as html_module
from typing import Tuple, Optional, Dict, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Models, AppConfig, DeveloperConfig
from auth import get_auth_manager
from chat_db import get_chat_db


class FloatingMenu:
    """Simple inline menu using expander - always works."""
    
    def __init__(self):
        self.auth = get_auth_manager()
    
    def render(self) -> Tuple[str, bool, bool]:
        user = st.session_state.get("current_user")
        if not user:
            return "openai", False, False
        
        # Menu content in an expander
        with st.expander("☰ Menu", expanded=False):
            self._render_drawer(user)
        
        return (
            st.session_state.get("selected_model", "openai"),
            st.session_state.get("agent_mode", False),
            st.session_state.get("swarm_mode", False)
        )
    
    def _render_drawer(self, user: Dict):
        """Render the menu content."""
        # User profile
        self._render_user_profile(user)
        
        # Action buttons
        self._render_action_buttons()
        
        st.divider()
        
        # Model selection
        selected_model = self._render_model_selector()
        
        st.divider()
        
        # Agent mode selection
        agent_mode, swarm_mode = self._render_agent_selector()
        
        st.divider()
        
        # Conversation list
        self._render_conversation_list(user)
        
        st.divider()
        
        # Export
        self._render_export_button()
        
        st.divider()
        
        # Version footer
        st.caption(f"{AppConfig.title} v{AppConfig.version} | Memory | Cache | Agent | Swarm")
        
        # Developer section
        if st.session_state.get("is_developer"):
            self._render_developer_section()
        
        # Update session state
        st.session_state.selected_model = selected_model
        st.session_state.agent_mode = agent_mode
        st.session_state.swarm_mode = swarm_mode
    
    def _render_user_profile(self, user: Dict):
        is_dev = st.session_state.get("is_developer", False)
        display_name = user.get("display_name", "User")
        username = user.get("username", "")
        initials = display_name[0].upper() if display_name else "?"
        role = "Developer / Creator" if is_dev else f"@{username}"
        border = "#10a37f" if is_dev else "#333"
        
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:12px;
                    background:#1a1a1a;border-radius:12px;margin-bottom:12px;
                    border:1px solid {border};">
            <div style="width:40px;height:40px;border-radius:50%;
                        background:linear-gradient(135deg,#10a37f,#34d399);
                        display:flex;align-items:center;justify-content:center;
                        color:white;font-weight:bold;font-size:18px;">
                {initials}
            </div>
            <div>
                <div style="font-weight:600;color:#e8e8e8;">{display_name}</div>
                <div style="font-size:12px;color:#10a37f;">{role}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_action_buttons(self):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Settings", use_container_width=True, key="fm_settings"):
                st.session_state.show_settings = True
                st.rerun()
        with col2:
            if st.button("Sign Out", use_container_width=True, key="fm_signout"):
                for key in ['user_token', 'current_user', 'current_conversation_id',
                            'is_developer', 'show_settings', 'agent_mode', 'swarm_mode']:
                    if key in ['agent_mode', 'swarm_mode', 'show_settings']:
                        st.session_state[key] = False
                    else:
                        st.session_state[key] = None
                st.rerun()
    
    def _render_model_selector(self) -> str:
        st.markdown("**Model**")
        display_names = Models.get_display_names()
        current_model = st.session_state.get("selected_model", Models.DEFAULT_MODEL)
        current_display = display_names[0]
        for display, api_name in Models.MODEL_MAP.items():
            if api_name == current_model:
                current_display = display
                break
        if current_display not in display_names:
            current_display = display_names[0]
        current_idx = display_names.index(current_display)
        
        choice = st.selectbox("Select Model", display_names, index=current_idx,
                            label_visibility="collapsed", key="fm_model_selector")
        selected_model = Models.get_api_name(choice)
        caps = Models.get_capabilities(selected_model)
        if caps:
            st.caption(" ".join([f"[{c.upper()}]" for c in caps]))
        return selected_model
    
    def _render_agent_selector(self) -> Tuple[bool, bool]:
        st.markdown("**Agent Mode**")
        current_agent = st.session_state.get("agent_mode", False)
        current_swarm = st.session_state.get("swarm_mode", False)
        
        if current_swarm:
            idx = 2
        elif current_agent:
            idx = 1
        else:
            idx = 0
        
        mode = st.radio("Select mode", ["Chat Only", "Standard Agent", "Swarm Agent"],
                       index=idx, key="fm_agent_mode", label_visibility="collapsed")
        
        agent_mode = "Chat" not in mode
        swarm_mode = "Swarm" in mode
        
        if agent_mode:
            st.caption(f"Max steps: {st.session_state.get('agent_max_steps', 15)}")
        
        return agent_mode, swarm_mode
    
    def _render_conversation_list(self, user: Dict):
        st.markdown("**Conversations**")
        
        if st.button("+ New Chat", use_container_width=True, key="fm_new_chat"):
            db = get_chat_db(user["username"])
            conv_id = db.create_conversation(model=st.session_state.get("selected_model", "openai"))
            st.session_state.current_conversation_id = conv_id
            st.rerun()
        
        db = get_chat_db(user["username"])
        conversations = db.get_conversations()
        
        if not conversations:
            st.caption("No conversations yet")
            return
        
        for conv in conversations[:15]:
            conv_id = conv["id"]
            title = conv.get("title", "Untitled")
            is_active = conv_id == st.session_state.get("current_conversation_id")
            display_title = title[:30] + "..." if len(title) > 30 else title
            
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                btn_type = "primary" if is_active else "secondary"
                if st.button(display_title, key=f"fm_conv_{conv_id}", use_container_width=True, type=btn_type):
                    st.session_state.current_conversation_id = conv_id
                    st.rerun()
            with col2:
                if st.button("X", key=f"fm_del_{conv_id}", help="Delete"):
                    db.delete_conversation(conv_id)
                    if st.session_state.get("current_conversation_id") == conv_id:
                        remaining = db.get_conversations()
                        if remaining:
                            st.session_state.current_conversation_id = remaining[0]["id"]
                        else:
                            st.session_state.current_conversation_id = db.create_conversation()
                    st.rerun()
    
    def _render_export_button(self):
        current_conv = st.session_state.get("current_conversation_id")
        user = st.session_state.get("current_user")
        if current_conv and user:
            if st.button("Export Chat", use_container_width=True, key="fm_export"):
                db = get_chat_db(user["username"])
                export_data = db.export_conversation(current_conv)
                conv = db.get_conversation(current_conv)
                title = conv.get("title", "chat") if conv else "chat"
                st.download_button("Download", data=export_data,
                                 file_name=f"denlab_{title.replace(' ', '_')}.md",
                                 mime="text/markdown", use_container_width=True)
    
    def _render_developer_section(self):
        st.divider()
        st.markdown("**Developer**")
        if st.button("Dev Panel", use_container_width=True, key="fm_dev_panel", type="primary"):
            st.session_state.show_developer_panel = True
            st.rerun()
        if st.button("System Stats", use_container_width=True, key="fm_sys_stats"):
            st.session_state.show_system_stats = True
            st.rerun()


class AdvancedSettings:
    def __init__(self):
        defaults = {"cache_enabled": True, "memory_enabled": True, "auto_route": True,
                    "show_memory_context": False, "agent_max_steps": AppConfig.max_agent_steps}
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def render(self):
        st.markdown("### Advanced Settings")
        st.session_state.cache_enabled = st.toggle("Response Cache", st.session_state.cache_enabled)
        st.session_state.memory_enabled = st.toggle("Memory System", st.session_state.memory_enabled)
        st.session_state.auto_route = st.toggle("Auto Route Queries", st.session_state.auto_route)
        st.session_state.agent_max_steps = st.slider("Agent Max Steps", 5, 50, st.session_state.agent_max_steps)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Cache", use_container_width=True):
                from client import get_client
                get_client().clear_cache()
                st.success("Cleared!")
                st.rerun()
        with col2:
            if st.button("Clear Memory", use_container_width=True):
                from client import get_client
                user = st.session_state.get("current_user")
                if user:
                    get_client().clear_memory(user["username"])
                st.success("Cleared!")
                st.rerun()


def render_floating_menu() -> Tuple[str, bool, bool]:
    menu = FloatingMenu()
    return menu.render()


def render_advanced_settings():
    AdvancedSettings().render()