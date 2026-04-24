"""
Sidebar Component for DenLab Chat.
Renders the sidebar UI including user info, model selection, agent mode toggles,
conversation list, and settings. No business logic - pure UI component.
"""

import streamlit as st
import html as html_module
from typing import Tuple, Optional, Dict, Any

# Import from completed files
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Models, AppConfig, DeveloperConfig
from auth import get_auth_manager
from chat_db import get_chat_db
from ui_components import render_developer_badge, render_agent_badge, render_version_footer


# ============================================================================
# SIDEBAR COMPONENT
# ============================================================================

class Sidebar:
    """
    Sidebar UI component for DenLab Chat.
    
    Handles:
    - User profile display (with developer badge)
    - Model selection dropdown
    - Agent mode selection (Standard vs Swarm)
    - Conversation list with load/delete
    - Export chat functionality
    - Settings button
    - Sign out button
    """
    
    def __init__(self):
        self.auth = get_auth_manager()
    
    # ========================================================================
    # Main Render Method
    # ========================================================================
    
    def render(self) -> Tuple[str, bool, bool]:
        """
        Render the sidebar and return user choices.
        
        Returns:
            Tuple of (selected_model, agent_mode, swarm_mode)
        """
        user = st.session_state.get("current_user")
        if not user:
            return "openai", False, False
        
        with st.sidebar:
            # User profile section
            self._render_user_profile(user)
            
            # Settings and sign out buttons
            self._render_action_buttons()
            
            st.divider()
            
            # Model selection
            selected_model = self._render_model_selector()
            
            st.divider()
            
            # Agent mode selection (Standard vs Swarm)
            agent_mode, swarm_mode = self._render_agent_selector()
            
            st.divider()
            
            # Conversation list
            self._render_conversation_list(user)
            
            st.divider()
            
            # Export chat
            self._render_export_button()
            
            st.divider()
            
            # Version footer
            render_version_footer()
        
        return selected_model, agent_mode, swarm_mode
    
    # ========================================================================
    # Private Render Methods
    # ========================================================================
    
    def _render_user_profile(self, user: Dict):
        """Render user profile section with optional developer badge."""
        is_developer = st.session_state.get("is_developer", False)
        display_name = user.get("display_name", "User")
        username = user.get("username", "")
        
        if is_developer:
            # Developer profile with special styling
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px;background:#1a1a1a;border-radius:10px;margin-bottom:10px;border:1px solid #10a37f;">
                <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#10a37f,#34d399);display:flex;align-items:center;justify-content:center;font-weight:600;color:white;font-size:14px;">
                    {display_name[0].upper()}
                </div>
                <div>
                    <div style="font-weight:600;color:#e8e8e8;font-size:13px;">{html_module.escape(display_name)}</div>
                    <div style="font-size:11px;color:#10a37f;">👑 Developer / Creator</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Regular user profile
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px;background:#1a1a1a;border-radius:10px;margin-bottom:10px;">
                <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#10a37f,#34d399);display:flex;align-items:center;justify-content:center;font-weight:600;color:white;font-size:14px;">
                    {display_name[0].upper()}
                </div>
                <div>
                    <div style="font-weight:600;color:#e8e8e8;font-size:13px;">{html_module.escape(display_name)}</div>
                    <div style="font-size:11px;color:#888;">@{html_module.escape(username)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_action_buttons(self):
        """Render Settings and Sign Out buttons."""
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("⚙️ Settings", use_container_width=True, key="sidebar_settings"):
                st.session_state.show_settings = True
                st.rerun()
        
        with col2:
            if st.button("🚪 Sign Out", use_container_width=True, key="sidebar_signout"):
                token = st.session_state.get("user_token")
                if token and token != "dev_token":
                    self.auth.logout(token)
                
                # Clear session state
                for key in ['user_token', 'current_user', 'current_conversation_id', 
                           'is_developer', 'show_settings', 'agent_mode', 'swarm_mode']:
                    if key in st.session_state:
                        if key in ['agent_mode', 'swarm_mode', 'show_settings']:
                            st.session_state[key] = False
                        else:
                            st.session_state[key] = None
                
                st.rerun()
    
    def _render_model_selector(self) -> str:
        """
        Render model selection dropdown.
        
        Returns:
            Selected model API name (e.g., "openai", "claude")
        """
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">MODEL</p>', unsafe_allow_html=True)
        
        # Get display names and current model
        display_names = Models.get_display_names()
        current_model = st.session_state.get("selected_model", Models.DEFAULT_MODEL)
        
        # Find index of current model
        current_display = None
        for display, api_name in Models.MODEL_MAP.items():
            if api_name == current_model:
                current_display = display
                break
        
        if current_display not in display_names:
            current_display = display_names[0]
        
        current_idx = display_names.index(current_display)
        
        # Model selection dropdown
        choice = st.selectbox(
            "",
            display_names,
            index=current_idx,
            label_visibility="collapsed",
            key="model_selector"
        )
        
        selected_model = Models.get_api_name(choice)
        st.session_state.selected_model = selected_model
        
        # Show model capabilities
        caps = Models.get_capabilities(selected_model)
        if caps:
            st.caption(" ".join([f"[{c.upper()}]" for c in caps]))
        
        return selected_model
    
    def _render_agent_selector(self) -> Tuple[bool, bool]:
        """
        Render agent mode selection (Standard vs Swarm).
        
        Returns:
            Tuple of (agent_mode, swarm_mode)
        """
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">AGENT MODE</p>', unsafe_allow_html=True)
        
        # Get current states
        current_agent_mode = st.session_state.get("agent_mode", False)
        current_swarm_mode = st.session_state.get("swarm_mode", False)
        
        # Two-column layout for Standard/Swarm buttons
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button(
                "🤖 Standard",
                use_container_width=True,
                type="primary" if current_agent_mode and not current_swarm_mode else "secondary",
                key="mode_standard"
            ):
                st.session_state.agent_mode = True
                st.session_state.swarm_mode = False
                st.rerun()
        
        with col_b:
            if st.button(
                "🐝 Swarm",
                use_container_width=True,
                type="primary" if current_agent_mode and current_swarm_mode else "secondary",
                key="mode_swarm"
            ):
                st.session_state.agent_mode = True
                st.session_state.swarm_mode = True
                st.rerun()
        
        # Status caption
        if current_agent_mode:
            if current_swarm_mode:
                st.caption("🐝 Swarm: Master + sub-agents (parallel execution)")
            else:
                max_steps = st.session_state.get("agent_max_steps", AppConfig.max_agent_steps)
                st.caption(f"🤖 Standard agent • {max_steps} steps max")
        else:
            st.caption("Enable agent mode for autonomous task execution")
        
        return current_agent_mode, current_swarm_mode
    
    def _render_conversation_list(self, user: Dict):
        """Render conversation list with load and delete buttons."""
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">CONVERSATIONS</p>', unsafe_allow_html=True)
        
        # New chat button
        if st.button("+ New Chat", use_container_width=True, key="new_chat_btn"):
            db = get_chat_db(user["username"])
            conv_id = db.create_conversation(model=st.session_state.get("selected_model", "openai"))
            st.session_state.current_conversation_id = conv_id
            st.rerun()
        
        # Get conversations
        db = get_chat_db(user["username"])
        conversations = db.get_conversations()
        
        if not conversations:
            st.caption("No conversations yet")
            return
        
        # Display up to 15 recent conversations
        for conv in conversations[:15]:
            conv_id = conv["id"]
            title = conv.get("title", "Untitled")
            is_active = conv_id == st.session_state.get("current_conversation_id")
            
            # Truncate long titles
            display_title = title[:24] + "..." if len(title) > 24 else title
            display_title = html_module.escape(display_title)
            
            col1, col2 = st.columns([0.85, 0.15])
            
            with col1:
                btn_type = "primary" if is_active else "secondary"
                if st.button(
                    display_title,
                    key=f"conv_{conv_id}",
                    use_container_width=True,
                    type=btn_type
                ):
                    st.session_state.current_conversation_id = conv_id
                    st.rerun()
            
            with col2:
                if st.button("🗑", key=f"del_{conv_id}", help="Delete conversation"):
                    db.delete_conversation(conv_id)
                    # If we deleted the active conversation, load the most recent one
                    if st.session_state.get("current_conversation_id") == conv_id:
                        remaining = db.get_conversations()
                        if remaining:
                            st.session_state.current_conversation_id = remaining[0]["id"]
                        else:
                            # Create new conversation if none left
                            new_id = db.create_conversation()
                            st.session_state.current_conversation_id = new_id
                    st.rerun()
    
    def _render_export_button(self):
        """Render export chat button."""
        current_conv = st.session_state.get("current_conversation_id")
        user = st.session_state.get("current_user")
        
        if current_conv and user:
            if st.button("📥 Export Chat", use_container_width=True, key="export_chat"):
                db = get_chat_db(user["username"])
                export_data = db.export_conversation(current_conv)
                conv = db.get_conversation(current_conv)
                title = conv.get("title", "chat") if conv else "chat"
                
                st.download_button(
                    label="Download",
                    data=export_data,
                    file_name=f"denlab_{title.replace(' ', '_')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="download_export"
                )


# ============================================================================
# ADVANCED SETTINGS COMPONENT
# ============================================================================

class AdvancedSettings:
    """
    Advanced settings expander component.
    Handles cache, memory, auto-route, and agent max steps toggles.
    """
    
    def __init__(self):
        self._init_settings()
    
    def _init_settings(self):
        """Initialize settings in session state if not present."""
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
        """Render advanced settings expander."""
        with st.expander("⚙️ Advanced Settings"):
            # Cache toggle
            st.session_state.cache_enabled = st.toggle(
                "💾 Response Cache",
                value=st.session_state.cache_enabled,
                help="Cache responses to reduce API calls and improve speed"
            )
            
            # Memory toggle
            st.session_state.memory_enabled = st.toggle(
                "🧠 Memory System",
                value=st.session_state.memory_enabled,
                help="Remember past conversations for personalized responses"
            )
            
            # Auto-route toggle
            st.session_state.auto_route = st.toggle(
                "🔄 Auto Route Queries",
                value=st.session_state.auto_route,
                help="Automatically detect intent and route to appropriate tools"
            )
            
            # Show memory context toggle
            st.session_state.show_memory_context = st.toggle(
                "📋 Show Memory Context",
                value=st.session_state.show_memory_context,
                help="Display when memory or cache is used in responses"
            )
            
            st.divider()
            
            # Agent max steps slider
            st.session_state.agent_max_steps = st.slider(
                "📊 Agent Max Steps",
                min_value=5,
                max_value=50,
                value=st.session_state.agent_max_steps,
                help="More steps = better for complex tasks, but slower"
            )
            
            st.divider()
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Clear Cache", use_container_width=True):
                    from client import get_client
                    client = get_client()
                    client.clear_cache()
                    st.success("Cache cleared!")
                    st.rerun()
            
            with col2:
                if st.button("🧹 Clear Memory", use_container_width=True):
                    from client import get_client
                    client = get_client()
                    user = st.session_state.get("current_user")
                    if user:
                        client.clear_memory(user["username"])
                    st.success("Memory cleared!")
                    st.rerun()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def render_sidebar() -> Tuple[str, bool, bool]:
    """Convenience function to render the sidebar."""
    sidebar = Sidebar()
    return sidebar.render()


def render_advanced_settings():
    """Convenience function to render advanced settings."""
    settings = AdvancedSettings()
    settings.render()


def get_sidebar_state() -> Dict[str, Any]:
    """Get current sidebar-related state values."""
    return {
        "agent_mode": st.session_state.get("agent_mode", False),
        "swarm_mode": st.session_state.get("swarm_mode", False),
        "selected_model": st.session_state.get("selected_model", "openai"),
        "cache_enabled": st.session_state.get("cache_enabled", True),
        "memory_enabled": st.session_state.get("memory_enabled", True),
        "auto_route": st.session_state.get("auto_route", True),
        "agent_max_steps": st.session_state.get("agent_max_steps", AppConfig.max_agent_steps)
    }