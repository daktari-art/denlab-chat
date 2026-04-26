"""
Sidebar Component - DEPRECATED / LEGACY.

NOTE: This file is kept for backward compatibility but is NO LONGER USED
in the main app flow. The floating_menu.py component has replaced it.

The sidebar was problematic because:
- Streamlit's native sidebar cannot be hidden on Hugging Face Spaces
- It was always visible and took up permanent screen real estate
- On mobile, it blocked half the interface

Replacement: components/floating_menu.py provides:
- A hamburger menu button (top-left, floating)
- A slide-out drawer with all sidebar functionality
- Proper hide/show behavior on all platforms
- Better mobile experience

If you are migrating from sidebar.py, simply replace:
    from components.sidebar import render_sidebar
    render_sidebar(...)
With:
    from components.floating_menu import render_floating_menu
    render_floating_menu()

Connected to: DEPRECATED. Use floating_menu.py instead.
"""

import streamlit as st
from typing import Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Models, AppConfig
from auth import get_auth_manager
from chat_db import get_chat_db
from ui_components import render_version_footer


def render_sidebar() -> Tuple[str, bool]:
    """
    DEPRECATED: Render sidebar. Use floating_menu.render_floating_menu() instead.
    
    This function now redirects to the floating menu and shows a deprecation notice.
    """
    st.sidebar.warning("⚠️ Sidebar is deprecated. Use the ☰ menu button instead.")
    
    # Minimal legacy implementation
    auth = get_auth_manager()
    user = st.session_state.get("current_user")
    
    if not user:
        return "openai", False
    
    st.sidebar.markdown(f"### {AppConfig.title}")
    
    # Model selection
    display_names = Models.get_display_names()
    selected = st.sidebar.selectbox("Model", display_names)
    model = Models.get_api_name(selected)
    
    # Agent toggle
    agent_mode = st.sidebar.toggle("Agent Mode", value=st.session_state.get("agent_mode", False))
    
    # New conversation
    if st.sidebar.button("+ New Chat"):
        db = get_chat_db(user["username"])
        conv_id = db.create_conversation(model=model)
        st.session_state.current_conversation_id = conv_id
        st.rerun()
    
    st.sidebar.divider()
    render_version_footer()
    
    return model, agent_mode


__all__ = ["render_sidebar"]
