"""
Floating Menu Component for DenLab Chat.
Replaces the problematic static sidebar with a slide-out drawer that works on
Streamlit, Hugging Face Spaces, and mobile devices.

This component renders:
- A hamburger menu button (top-left, floating)
- A slide-out drawer with all sidebar functionality
- Model selection, agent mode, conversation list, settings, export
- Developer controls (when is_developer=True)
- Smooth CSS transitions for open/close
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
# FLOATING MENU CSS (Injected once)
# ============================================================================

MENU_CSS = """
<style>
/* Floating hamburger button */
.denlab-menu-btn {
    position: fixed !important;
    top: 12px !important;
    left: 12px !important;
    z-index: 99999 !important;
    width: 40px !important;
    height: 40px !important;
    background: #111 !important;
    border: 1px solid #333 !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-size: 18px !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    transition: all 0.2s ease !important;
}
.denlab-menu-btn:hover {
    background: #222 !important;
    transform: scale(1.05) !important;
}

/* Overlay backdrop */
.denlab-menu-overlay {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background: rgba(0,0,0,0.5) !important;
    z-index: 99998 !important;
    opacity: 0 !important;
    pointer-events: none !important;
    transition: opacity 0.3s ease !important;
}
.denlab-menu-overlay.active {
    opacity: 1 !important;
    pointer-events: auto !important;
}

/* Slide-out drawer */
.denlab-drawer {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 300px !important;
    max-width: 85vw !important;
    height: 100vh !important;
    background: #111 !important;
    border-right: 1px solid #222 !important;
    z-index: 99999 !important;
    transform: translateX(-100%) !important;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    overflow-y: auto !important;
    padding: 16px !important;
    box-sizing: border-box !important;
}
.denlab-drawer.active {
    transform: translateX(0) !important;
}

/* Drawer content styling */
.denlab-drawer h3 {
    color: #fff !important;
    font-size: 14px !important;
    margin: 16px 0 8px 0 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
}
.denlab-drawer .section {
    margin-bottom: 16px !important;
}
.denlab-drawer .user-card {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    padding: 10px !important;
    background: #1a1a1a !important;
    border-radius: 10px !important;
    margin-bottom: 12px !important;
    border: 1px solid #10a37f !important;
}
.denlab-drawer .user-avatar {
    width: 32px !important;
    height: 32px !important;
    border-radius: 50% !important;
    background: linear-gradient(135deg, #10a37f, #34d399) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-weight: 600 !important;
    color: white !important;
    font-size: 14px !important;
}
.denlab-drawer .user-info {
    flex: 1 !important;
}
.denlab-drawer .user-name {
    font-weight: 600 !important;
    color: #e8e8e8 !important;
    font-size: 13px !important;
}
.denlab-drawer .user-role {
    font-size: 11px !important;
    color: #10a37f !important;
}

/* Conversation list items */
.denlab-drawer .conv-item {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 8px 10px !important;
    margin: 4px 0 !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
    color: #ccc !important;
    font-size: 13px !important;
}
.denlab-drawer .conv-item:hover {
    background: #1a1a1a !important;
}
.denlab-drawer .conv-item.active {
    background: #1a1a1a !important;
    border-left: 3px solid #10a37f !important;
}
.denlab-drawer .conv-delete {
    background: none !important;
    border: none !important;
    color: #666 !important;
    cursor: pointer !important;
    font-size: 14px !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
}
.denlab-drawer .conv-delete:hover {
    color: #ef4444 !important;
    background: rgba(239, 68, 68, 0.1) !important;
}

/* Buttons inside drawer */
.denlab-drawer .btn-row {
    display: flex !important;
    gap: 8px !important;
    margin: 8px 0 !important;
}
.denlab-drawer .btn-row button {
    flex: 1 !important;
}

/* Close button */
.denlab-drawer .drawer-close {
    position: absolute !important;
    top: 12px !important;
    right: 12px !important;
    background: none !important;
    border: none !important;
    color: #888 !important;
    font-size: 20px !important;
    cursor: pointer !important;
    width: 32px !important;
    height: 32px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 8px !important;
}
.denlab-drawer .drawer-close:hover {
    background: #222 !important;
    color: #fff !important;
}

/* Ensure main content is not hidden behind fixed elements */
.main .block-container {
    padding-left: 60px !important;
}
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 50px !important;
    }
}

/* Hide Streamlit default sidebar entirely */
[data-testid="stSidebar"] {
    display: none !important;
}
[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}
</style>
"""


def inject_menu_css():
    """Inject the floating menu CSS into the page."""
    st.markdown(MENU_CSS, unsafe_allow_html=True)


# ============================================================================
# FLOATING MENU COMPONENT
# ============================================================================

class FloatingMenu:
    """
    Floating hamburger menu that opens a slide-out drawer.
    
    Works on Streamlit Cloud, Hugging Face Spaces, and mobile.
    Replaces the problematic native sidebar which was static and unhideable.
    """
    
    DRAWER_KEY = "denlab_drawer_open"
    
    def __init__(self):
        self.auth = get_auth_manager()
        if self.DRAWER_KEY not in st.session_state:
            st.session_state[self.DRAWER_KEY] = False
    
    # ========================================================================
    # Main Render
    # ========================================================================
    
    def render(self) -> Tuple[str, bool, bool]:
        """
        Render the floating menu and drawer.
        
        Returns:
            Tuple of (selected_model, agent_mode, swarm_mode)
        """
        user = st.session_state.get("current_user")
        if not user:
            return "openai", False, False
        
        inject_menu_css()
        
        # Render the floating hamburger button (always visible)
        self._render_hamburger()
        
        # Render overlay and drawer
        self._render_overlay()
        self._render_drawer(user)
        
        return (
            st.session_state.get("selected_model", "openai"),
            st.session_state.get("agent_mode", False),
            st.session_state.get("swarm_mode", False)
        )
    
    # ========================================================================
    # Hamburger Button
    # ========================================================================
    
    def _render_hamburger(self):
        """Render the fixed hamburger button."""
        # Use a button with custom CSS class via markdown + JS
        col1, col2, col3 = st.columns([1, 20, 1])
        with col1:
            # We use a small trick: a native Streamlit button styled via CSS
            # The CSS class injection targets buttons in the first column
            btn = st.button(
                "☰",
                key="denlab_hamburger",
                help="Open menu",
                use_container_width=True
            )
            if btn:
                st.session_state[self.DRAWER_KEY] = True
                st.rerun()
        
        # Apply custom class to the button via JS after render
        st.markdown("""
        <script>
        (function() {
            const btn = window.parent.document.querySelector('button[kind="secondary"][data-testid="baseButton-secondary"]');
            if (btn && btn.textContent.trim() === '☰') {
                btn.classList.add('denlab-menu-btn');
                btn.style.position = 'fixed';
                btn.style.top = '12px';
                btn.style.left = '12px';
                btn.style.zIndex = '99999';
                btn.style.width = '40px';
                btn.style.height = '40px';
                btn.style.background = '#111';
                btn.style.border = '1px solid #333';
                btn.style.borderRadius = '10px';
                btn.style.color = '#fff';
                btn.style.fontSize = '18px';
            }
        })();
        </script>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # Overlay
    # ========================================================================
    
    def _render_overlay(self):
        """Render the backdrop overlay."""
        is_open = st.session_state.get(self.DRAWER_KEY, False)
        active_class = "active" if is_open else ""
        st.markdown(
            f'<div class="denlab-menu-overlay {active_class}" onclick="closeDenlabDrawer()"></div>',
            unsafe_allow_html=True
        )
    
    # ========================================================================
    # Drawer
    # ========================================================================
    
    def _render_drawer(self, user: Dict):
        """Render the slide-out drawer content."""
        is_open = st.session_state.get(self.DRAWER_KEY, False)
        active_class = "active" if is_open else ""
        
        # JavaScript to handle closing
        st.markdown("""
        <script>
        function closeDenlabDrawer() {
            const drawer = window.parent.document.querySelector('.denlab-drawer');
            const overlay = window.parent.document.querySelector('.denlab-menu-overlay');
            if (drawer) drawer.classList.remove('active');
            if (overlay) overlay.classList.remove('active');
            // Also notify Streamlit via URL fragment (lightweight signal)
            window.parent.location.hash = 'drawer_closed';
        }
        </script>
        """, unsafe_allow_html=True)
        
        # Drawer container
        st.markdown(f'<div class="denlab-drawer {active_class}">', unsafe_allow_html=True)
        
        # Close button
        if st.button("✕", key="drawer_close_btn"):
            st.session_state[self.DRAWER_KEY] = False
            st.rerun()
        
        # User profile
        self._render_user_profile(user)
        
        # Action buttons (Settings, Sign Out)
        self._render_action_buttons()
        
        st.markdown("<hr style='border-color:#333;margin:12px 0;'>", unsafe_allow_html=True)
        
        # Model selection
        selected_model = self._render_model_selector()
        
        st.markdown("<hr style='border-color:#333;margin:12px 0;'>", unsafe_allow_html=True)
        
        # Agent mode selection
        agent_mode, swarm_mode = self._render_agent_selector()
        
        st.markdown("<hr style='border-color:#333;margin:12px 0;'>", unsafe_allow_html=True)
        
        # Conversation list
        self._render_conversation_list(user)
        
        st.markdown("<hr style='border-color:#333;margin:12px 0;'>", unsafe_allow_html=True)
        
        # Export button
        self._render_export_button()
        
        st.markdown("<hr style='border-color:#333;margin:12px 0;'>", unsafe_allow_html=True)
        
        # Version footer
        st.caption(f"{AppConfig.title} v{AppConfig.version} | 🧠 Memory • ⚡ Cache • 🤖 Agent • 🐝 Swarm")
        
        # Developer section (only for developer)
        if st.session_state.get("is_developer"):
            self._render_developer_section()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Update session state
        st.session_state.selected_model = selected_model
        st.session_state.agent_mode = agent_mode
        st.session_state.swarm_mode = swarm_mode
    
    # ========================================================================
    # Drawer Sub-sections
    # ========================================================================
    
    def _render_user_profile(self, user: Dict):
        """Render user profile card in drawer."""
        is_developer = st.session_state.get("is_developer", False)
        display_name = user.get("display_name", "User")
        username = user.get("username", "")
        
        role_text = "👑 Developer / Creator" if is_developer else f"@{html_module.escape(username)}"
        border_color = "#10a37f" if is_developer else "#333"
        
        st.markdown(f"""
        <div class="user-card" style="border-color: {border_color} !important;">
            <div class="user-avatar">{display_name[0].upper()}</div>
            <div class="user-info">
                <div class="user-name">{html_module.escape(display_name)}</div>
                <div class="user-role">{role_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_action_buttons(self):
        """Render Settings and Sign Out buttons."""
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚙️ Settings", use_container_width=True, key="fm_settings"):
                st.session_state.show_settings = True
                st.session_state[self.DRAWER_KEY] = False
                st.rerun()
        with col2:
            if st.button("🚪 Sign Out", use_container_width=True, key="fm_signout"):
                token = st.session_state.get("user_token")
                if token and token != "dev_token":
                    self.auth.logout(token)
                for key in ['user_token', 'current_user', 'current_conversation_id',
                            'is_developer', 'show_settings', 'agent_mode', 'swarm_mode']:
                    st.session_state[key] = None if key in ['agent_mode', 'swarm_mode', 'show_settings'] else False
                    if key in ['agent_mode', 'swarm_mode', 'show_settings']:
                        st.session_state[key] = False
                st.rerun()
    
    def _render_model_selector(self) -> str:
        """Render model selection dropdown."""
        st.markdown('<p style="font-size:10px;color:#666;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 6px;">MODEL</p>', unsafe_allow_html=True)
        
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
            "",
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
        """Render agent mode selection."""
        st.markdown('<p style="font-size:10px;color:#666;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 6px;">AGENT MODE</p>', unsafe_allow_html=True)
        
        current_agent = st.session_state.get("agent_mode", False)
        current_swarm = st.session_state.get("swarm_mode", False)
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(
                "🤖 Standard",
                use_container_width=True,
                type="primary" if current_agent and not current_swarm else "secondary",
                key="fm_mode_standard"
            ):
                st.session_state.agent_mode = True
                st.session_state.swarm_mode = False
                st.rerun()
        with col_b:
            if st.button(
                "🐝 Swarm",
                use_container_width=True,
                type="primary" if current_agent and current_swarm else "secondary",
                key="fm_mode_swarm"
            ):
                st.session_state.agent_mode = True
                st.session_state.swarm_mode = True
                st.rerun()
        
        if current_agent:
            if current_swarm:
                st.caption("🐝 Swarm: Master + sub-agents (parallel)")
            else:
                max_steps = st.session_state.get("agent_max_steps", AppConfig.max_agent_steps)
                st.caption(f"🤖 Standard agent • {max_steps} steps max")
        else:
            st.caption("Enable agent mode for autonomous execution")
        
        return current_agent, current_swarm
    
    def _render_conversation_list(self, user: Dict):
        """Render conversation list in drawer."""
        st.markdown('<p style="font-size:10px;color:#666;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 6px;">CONVERSATIONS</p>', unsafe_allow_html=True)
        
        if st.button("+ New Chat", use_container_width=True, key="fm_new_chat"):
            db = get_chat_db(user["username"])
            conv_id = db.create_conversation(model=st.session_state.get("selected_model", "openai"))
            st.session_state.current_conversation_id = conv_id
            st.session_state[self.DRAWER_KEY] = False
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
            display_title = title[:24] + "..." if len(title) > 24 else title
            
            active_class = "active" if is_active else ""
            
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                if st.button(
                    display_title,
                    key=f"fm_conv_{conv_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.current_conversation_id = conv_id
                    st.session_state[self.DRAWER_KEY] = False
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
        """Render export chat button."""
        current_conv = st.session_state.get("current_conversation_id")
        user = st.session_state.get("current_user")
        
        if current_conv and user:
            if st.button("📥 Export Chat", use_container_width=True, key="fm_export"):
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
                    key="fm_download_export"
                )
    
    def _render_developer_section(self):
        """Render developer-specific quick links."""
        st.markdown("<hr style='border-color:#10a37f;margin:12px 0;'>", unsafe_allow_html=True)
        st.markdown('<p style="font-size:10px;color:#10a37f;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 6px;">👑 DEVELOPER</p>', unsafe_allow_html=True)
        
        if st.button("🔧 Dev Panel", use_container_width=True, key="fm_dev_panel", type="primary"):
            st.session_state.show_developer_panel = True
            st.session_state[self.DRAWER_KEY] = False
            st.rerun()
        
        if st.button("📊 System Stats", use_container_width=True, key="fm_sys_stats"):
            st.session_state.show_system_stats = True
            st.session_state[self.DRAWER_KEY] = False
            st.rerun()


# ============================================================================
# ADVANCED SETTINGS (inline, not sidebar-dependent)
# ============================================================================

class AdvancedSettings:
    """Advanced settings rendered in main content area, not sidebar."""
    
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
        """Render advanced settings expander in main area."""
        with st.expander("⚙️ Advanced Settings"):
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
