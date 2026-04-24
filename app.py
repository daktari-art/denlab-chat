"""
DenLab Chat - Main Application Gateway
Version 7.0 - Modular Architecture

This file is the entry point. It handles:
- Page configuration
- Authentication
- Importing and orchestrating components
- NO business logic - everything delegated to components/
"""

import streamlit as st
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from components (modular architecture)
from config.settings import AppConfig, DeveloperConfig
from auth import get_auth_manager
from chat_db import get_chat_db
from ui_components import apply_clean_theme
from components.sidebar import Sidebar, AdvancedSettings
from components.chat_interface import ChatInterface, process_file_upload


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title=AppConfig.title,
    page_icon=AppConfig.icon,
    layout=AppConfig.layout,
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/daktari-art/denlab-chat',
        'Report a bug': 'https://github.com/daktari-art/denlab-chat/issues',
        'About': f'{AppConfig.title} v{AppConfig.version} - {AppConfig.description}'
    }
)


# ============================================================================
# CSS - CLEAN THEME (NO FORCED SIDEBAR - COLLAPSIBLE)
# ============================================================================

def apply_custom_css():
    """Apply custom CSS with collapsible sidebar."""
    st.markdown("""
    <style>
        /* Make collapse button visible and clickable */
        button[kind="header"] {
            display: flex !important;
            background: transparent !important;
            color: #888 !important;
            border: none !important;
        }
        
        button[kind="header"]:hover {
            color: #10a37f !important;
            background: rgba(255,255,255,0.05) !important;
        }
        
        /* Chat input - fixed at bottom */
        .stChatInput {
            position: fixed !important;
            bottom: 20px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: calc(100% - 300px) !important;
            max-width: 760px !important;
            background: #ffffff !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 28px !important;
            padding: 4px 12px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
            z-index: 999 !important;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .stChatInput {
                width: calc(100% - 20px) !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "user_token": None,
        "current_user": None,
        "current_conversation_id": None,
        "selected_model": "openai",
        "agent_mode": False,
        "swarm_mode": False,
        "uploader_key": "0",
        "pending_upload": None,
        "processing_upload": False,
        "show_settings": False,
        "uploaded_files": {},
        "messages_cache": [],
        "sidebar_collapsed": False,
        "agent_progress": [],
        "auto_route": True,
        "show_memory_context": False,
        "current_branch": None,
        "cache_enabled": True,
        "memory_enabled": True,
        "agent_max_steps": AppConfig.max_agent_steps,
        "is_developer": False,
        "show_agent_traces": True,
        "swarm_max_parallel": 4,
        "swarm_show_plan": True,
        "swarm_debug_mode": False,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Validate existing session
    if st.session_state.user_token and st.session_state.user_token != "dev_token":
        auth = get_auth_manager()
        user = auth.validate_token(st.session_state.user_token)
        if not user:
            st.session_state.user_token = None
            st.session_state.current_user = None
        elif user.get("username") == DeveloperConfig.USERNAME:
            st.session_state.is_developer = True


# ============================================================================
# AUTHENTICATION UI
# ============================================================================

def show_login_page():
    """Display login/registration page."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"""
        <div style="max-width:400px;margin:0 auto;padding:40px 24px;">
            <div style="text-align:center;font-size:28px;margin-bottom:16px;">{AppConfig.icon}</div>
            <div style="text-align:center;font-size:24px;font-weight:700;margin-bottom:8px;color:#111;">{AppConfig.title}</div>
            <div style="text-align:center;font-size:13px;color:#888;margin-bottom:32px;">{AppConfig.description}</div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Sign In", "Create Account"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="your_username")
                password = st.text_input("Password", type="password", placeholder="••••••")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                
                if submitted:
                    if not username or not password:
                        st.error("Please fill in all fields")
                    else:
                        auth = get_auth_manager()
                        result = auth.login(username, password)
                        
                        if result["success"]:
                            st.session_state.user_token = result["token"]
                            st.session_state.current_user = result["user"]
                            if result["user"]["username"] == DeveloperConfig.USERNAME:
                                st.session_state.is_developer = True
                            st.success(f"Welcome back, {result['user']['display_name']}!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(result["error"])
        
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Choose Username", placeholder="e.g., johndoe")
                new_display = st.text_input("Display Name (optional)", placeholder="John Doe")
                new_password = st.text_input("Password", type="password", placeholder="Min 6 characters")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                
                if submitted:
                    if not new_username or not new_password:
                        st.error("Username and password are required")
                    elif new_password != confirm_password:
                        st.error("Passwords don't match")
                    elif new_username.lower() == DeveloperConfig.USERNAME:
                        st.error("This username is reserved. Please choose another.")
                    else:
                        auth = get_auth_manager()
                        result = auth.register(new_username, new_password, new_display or None)
                        
                        if result["success"]:
                            st.session_state.user_token = result["token"]
                            st.session_state.current_user = result["user"]
                            st.success("Account created successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(result["error"])
        
        st.markdown(f'<p style="text-align:center;color:#999;font-size:11px;margin-top:32px;">{AppConfig.title} v{AppConfig.version}</p></div>', unsafe_allow_html=True)


# ============================================================================
# SETTINGS PAGE
# ============================================================================

def show_settings_page():
    """Display settings page."""
    st.markdown("## Settings")
    
    user = st.session_state.current_user
    auth = get_auth_manager()
    
    tab1, tab2, tab3 = st.tabs(["Account", "Chat", "Advanced"])
    
    with tab1:
        st.markdown("### Profile")
        st.write(f"**Username:** @{user['username']}")
        if st.session_state.is_developer:
            st.info("👑 **Developer Mode Active** - Full access to all features.")
        
        if st.session_state.user_token != "dev_token":
            with st.form("change_password"):
                st.markdown("**Change Password**")
                old_pass = st.text_input("Current Password", type="password")
                new_pass = st.text_input("New Password", type="password")
                confirm_pass = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Update Password", type="primary"):
                    if new_pass != confirm_pass:
                        st.error("New passwords don't match")
                    else:
                        result = auth.change_password(st.session_state.user_token, old_pass, new_pass)
                        if result["success"]:
                            st.success("Password updated!")
                        else:
                            st.error(result["error"])
    
    with tab2:
        st.markdown("### Chat Settings")
        st.session_state.auto_route = st.toggle("Auto-route to Agent", value=st.session_state.auto_route)
        st.session_state.show_memory_context = st.toggle("Show Memory Context", value=st.session_state.show_memory_context)
        st.session_state.show_agent_traces = st.toggle("Show Agent Traces", value=st.session_state.show_agent_traces)
    
    with tab3:
        st.markdown("### Agent Configuration")
        st.session_state.agent_max_steps = st.slider(
            "Maximum Agent Steps",
            min_value=5,
            max_value=50,
            value=st.session_state.agent_max_steps
        )
        
        st.markdown("### Cache & Memory")
        if st.button("Clear Cache", type="secondary"):
            from client import get_client
            get_client().clear_cache()
            st.success("Cache cleared!")
        
        if st.button("Clear Working Memory", type="secondary"):
            from client import get_client
            get_client().clear_memory(user["username"])
            st.success("Working memory cleared!")
    
    if st.button("← Back to Chat"):
        st.session_state.show_settings = False
        st.rerun()


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application entry point."""
    
    # Initialize
    init_session_state()
    apply_clean_theme()
    apply_custom_css()
    
    # Check authentication
    if not st.session_state.current_user:
        show_login_page()
        return
    
    # Show settings if requested
    if st.session_state.show_settings:
        show_settings_page()
        return
    
    # Ensure conversation exists
    db = get_chat_db(st.session_state.current_user["username"])
    if not st.session_state.current_conversation_id:
        conv_id = db.get_or_create_default(model=st.session_state.selected_model)
        st.session_state.current_conversation_id = conv_id
    
    # Get current conversation
    conv = db.get_conversation(st.session_state.current_conversation_id)
    messages = conv.get("messages", []) if conv else []
    
    # Render sidebar and get user choices
    sidebar = Sidebar()
    selected_model, agent_mode, swarm_mode = sidebar.render()
    
    # Update session state from sidebar choices
    st.session_state.selected_model = selected_model
    st.session_state.agent_mode = agent_mode
    st.session_state.swarm_mode = swarm_mode
    
    # Render advanced settings
    AdvancedSettings().render()
    
    # Handle file upload
    uploaded_file = st.file_uploader(
        "📎 Attach file",
        type=["txt", "py", "js", "ts", "html", "css", "json", "md", "csv", "xml", "yaml", "yml",
              "sh", "c", "cpp", "h", "java", "kt", "swift", "go", "rb", "php", "sql",
              "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "pdf"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        key=f"file_uploader_{st.session_state.uploader_key}"
    )
    
    if uploaded_file and not st.session_state.processing_upload:
        st.session_state.pending_upload = uploaded_file
        st.session_state.processing_upload = True
        st.session_state.uploader_key = str(int(st.session_state.uploader_key) + 1)
        st.rerun()
    
    if st.session_state.pending_upload and st.session_state.processing_upload:
        process_file_upload(db, st.session_state.current_conversation_id, st.session_state.pending_upload)
        st.session_state.pending_upload = None
        st.session_state.processing_upload = False
        st.rerun()
    
    # Render chat interface
    chat_interface = ChatInterface()
    chat_interface.render(
        db=db,
        conv_id=st.session_state.current_conversation_id,
        model=st.session_state.selected_model,
        user_id=st.session_state.current_user["username"],
        messages=messages
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()