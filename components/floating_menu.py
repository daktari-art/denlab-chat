"""
Floating Menu Component for DenLab Chat.
Uses Streamlit's native components instead of CSS hacks for reliability.
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
from ui_components import render_version_footer


# ============================================================================
# FLOATING MENU COMPONENT
# ============================================================================

class FloatingMenu:
    """
    Menu component using Streamlit's native dialog/popover.
    Reliable on all platforms without CSS/JS hacks.
    """
    
    MENU_OPEN_KEY = "denlab_menu_open"
    
    def __init__(self):
        self.auth = get_auth_manager()
        if self.MENU_OPEN_KEY not in st.session_state:
            st.session_state[self.MENU_OPEN_KEY] = False
    
    # ========================================================================
    # Main Render
    # ========================================================================
    
    def render(self) -> Tuple[str, bool, bool]:
        """
        Render the menu button and drawer.
        
        Returns:
            Tuple of (selected_model, agent_mode, swarm_mode)
        """
        user = st.session_state.get("current_user")
        if not user:
            return "openai", False, False
        
        # Top bar with hamburger button
        col_menu, col_title, col_spacer = st.columns([0.1, 0.8, 0.1])
        with col_menu:
            if st.button("☰", key="menu_hamburger", help="Open Menu"):
                st.session_state[self.MENU_OPEN_KEY] = not st.session_state[self.MENU_OPEN_KEY]
                st.rerun()
        
        # Show drawer if open
        if st.session_state[self.MENU_OPEN_KEY]:
            self._render_drawer(user)
        
        return (
            st.session_state.get("selected_model", "openai"),
            st.session_state.get("agent_mode", False),
            st.session_state.get("swarm_mode", False)
        )
    
    # ========================================================================
    # Drawer
    # ========================================================================
    
    def _render_drawer(self, user: Dict):
        """Render the menu drawer content in a container."""
        st.markdown("---")
        
        # Close button
        if st.button("✕ Close Menu", key="drawer_close"):
            st.session_state[self.MENU_OPEN_KEY] = False
            st.rerun()
        
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
        st.caption(f"{AppConfig.title} v{AppConfig.version} | 🧠 Memory • ⚡ Cache • 🤖 Agent • 🐝 Swarm")
        
        # Developer section
        if st.session_state.get("is_developer"):
            self._render_developer_section()
        
        st.markdown("---")
        
        # Update session state
        st.session_state.selected_model = selected_model
        st.session_state.agent_mode = agent_mode
        st.session_state.swarm_mode = swarm_mode
    
    # ========================================================================
    # Sub-sections
    # ========================================================================
    
    def _render_user_profile(self, user: Dict):
        """Render user profile."""
        is_developer = st.session_state.get("is_developer", False)
        display_name = user.get("display_name", "User")
        username = user.get("username", "")
        
        initials = display_name[0].upper() if display_name else "?"
        role_text = "👑 Developer / Creator" if is_developer else f"@{username}"
        
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:12px;
                    background:#1a1a1a;border-radius:12px;margin-bottom:12px;
                    border:1px solid {'#10a37f' if is_developer else '#333'};">
            <div style="width:40px;height:40px;border-radius:50%;
                        background:linear-gradient(135deg,#10a37f,#34d399);
                        display:flex;align-items:center;justify-content:center;
                        color:white;font-weight:bold;font-size:18px;">
                {initials}
            </div>
            <div>
                <div style="font-weight:600;color:#e8e8e8;">{display_name}</div>
                <div style="font-size:12px;color:#10a37f;">{role_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_action_buttons(self):
        """Settings and Sign Out."""
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚙️ Settings", use_container_width=True, key="fm_settings"):
                st.session_state.show_settings = True
                st.session_state[self.MENU_OPEN_KEY] = False
                st.rerun()
        with col2:
            if st.button("🚪 Sign Out", use_container_width=True, key="fm_signout"):
                token = st.session_state.get("user_token")
                if token and token != "dev_token":
                    self.auth.logout(token)
                for key in ['user_token', 'current_user', 'current_conversation_id',
                            'is_developer', 'show_settings', 'agent_mode', 'swarm_mode']:
                    if key in ['agent_mode', 'swarm_mode', 'show_settings']:
                        st.session_state[key] = False
                    else:
                        st.session_state[key] = None
                st.rerun()
    
    def _render_model_selector(self) -> str:
        """Model selection."""
        st.markdown("**🤖 MODEL**")
        
        display_names = Models.get_display_names()
        current_model = st.session_state.get("selected_model", Models.DEFAULT_MODEL)
        
        current_display = None
        for display, api_name in Models.MODEL_MAP.items():
            if api_name == current_model:
                current_display = display
                break
        if current_display not in display_names:
            current_display = display_names[0]
        
        current_idx = display_names.index(current_display)
        
        choice = st.selectbox(
            "Select Model",
            display_names,
            index=current_idx,
            label_visibility="collapsed",
            key="fm_model_selector"
        )
        
        selected_model = Models.get_api_name(choice)
        
        caps = Models.get_capabilities(selected_model)
        if caps:
            st.caption(" ".join([f"[{c.upper()}]" for c in caps]))
        
        return selected_model
    
    def _render_agent_selector(self) -> Tuple[bool, bool]:
        """Agent mode selection."""
        st.markdown("**🤖 AGENT MODE**")
        
        current_agent = st.session_state.get("agent_mode", False)
        current_swarm = st.session_state.get("swarm_mode", False)
        
        mode = st.radio(
            "Select mode",
            ["💬 Chat Only", "🤖 Standard Agent", "🐝 Swarm Agent"],
            index=2 if current_agent and current_swarm else 1 if current_agent else 0,
            key="fm_agent_mode",
            label_visibility="collapsed"
        )
        
        if "Chat" in mode:
            agent_mode = False
            swarm_mode = False
        elif "Swarm" in mode:
            agent_mode = True
            swarm_mode = True
        else:
            agent_mode = True
            swarm_mode = False
        
        if agent_mode:
            max_steps = st.session_state.get("agent_max_steps", AppConfig.max_agent_steps)
            st.caption(f"Max steps: {max_steps}")
        
        return agent_mode, swarm_mode
    
    def _render_conversation_list(self, user: Dict):
        """Conversation list."""
        st.markdown("**💬 CONVERSATIONS**")
        
        if st.button("+ New Chat", use_container_width=True, key="fm_new_chat"):
            db = get_chat_db(user["username"])
            conv_id = db.create_conversation(model=st.session_state.get("selected_model", "openai"))
            st.session_state.current_conversation_id = conv_id
            st.session_state[self.MENU_OPEN_KEY] = False
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
                    st.session_state[self.MENU_OPEN_KEY] = False
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"fm_del_{conv_id}", help="Delete"):
                    db.delete_conversation(conv_id)
                    if st.session_state.get("current_conversation_id") == conv_id:
                        remaining = db.get_conversations()
                        if remaining:
                            st.session_state.current_conversation_id = remaining[0]["id"]
                        else:
                            st.session_state.current_conversation_id = db.create_conversation()
                    st.rerun()
    
    def _render_export_button(self):
        """Export chat."""
        current_conv = st.session_state.get("current_conversation_id")
        user = st.session_state.get("current_user")
        
        if current_conv and user:
            if st.button("📥 Export Chat", use_container_width=True, key="fm_export"):
                db = get_chat_db(user["username"])
                export_data = db.export_conversation(current_conv)
                conv = db.get_conversation(current_conv)
                title = conv.get("title", "chat") if conv else "chat"
                st.download_button(
                    label="Download Markdown",
                    data=export_data,
                    file_name=f"denlab_{title.replace(' ', '_')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="fm_download_export"
                )
    
    def _render_developer_section(self):
        """Developer quick links."""
        st.divider()
        st.markdown("**👑 DEVELOPER**")
        
        if st.button("🔧 Dev Panel", use_container_width=True, key="fm_dev_panel", type="primary"):
            st.session_state.show_developer_panel = True
            st.session_state[self.MENU_OPEN_KEY] = False
            st.rerun()
        
        if st.button("📊 System Stats", use_container_width=True, key="fm_sys_stats"):
            st.session_state.show_system_stats = True
            st.session_state[self.MENU_OPEN_KEY] = False
            st.rerun()


# ============================================================================
# ADVANCED SETTINGS
# ============================================================================

class AdvancedSettings:
    """Advanced settings rendered in main content area."""
    
    def __init__(self):
        self._init_settings()
    
    def _init_settings(self):
        defaults = {
            "cache_enabled": True,
            "memory_enabled": True,
            "auto_route": True,
            "show_memory_context": False,
            "agent_max_steps": AppConfig.max_agent_steps
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def render(self):
        """Render advanced settings."""
        st.markdown("### ⚙️ Advanced Settings")
        
        st.session_state.cache_enabled = st.toggle(
            "💾 Response Cache",
            value=st.session_state.cache_enabled,
            help="Cache responses to reduce API calls"
        )
        st.session_state.memory_enabled = st.toggle(
            "🧠 Memory System",
            value=st.session_state.memory_enabled,
            help="Remember past conversations"
        )
        st.session_state.auto_route = st.toggle(
            "🔄 Auto Route Queries",
            value=st.session_state.auto_route,
            help="Auto-detect intent and route to tools"
        )
        st.session_state.show_memory_context = st.toggle(
            "📋 Show Memory Context",
            value=st.session_state.show_memory_context,
            help="Display when memory is used"
        )
        
        st.divider()
        st.session_state.agent_max_steps = st.slider(
            "📊 Agent Max Steps",
            min_value=5,
            max_value=50,
            value=st.session_state.agent_max_steps,
            help="Higher = more complex tasks, but slower"
        )
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Cache", use_container_width=True):
                from client import get_client
                get_client().clear_cache()
                st.success("Cache cleared!")
                st.rerun()
        with col2:
            if st.button("🧹 Clear Memory", use_container_width=True):
                from client import get_client
                user = st.session_state.get("current_user")
                if user:
                    get_client().clear_memory(user["username"])
                st.success("Memory cleared!")
                st.rerun()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def render_floating_menu() -> Tuple[str, bool, bool]:
    """Convenience function to render the floating menu."""
    menu = FloatingMenu()
    return menu.render()


def render_advanced_settings():
    """Convenience function to render advanced settings."""
    settings = AdvancedSettings()
    settings.render()