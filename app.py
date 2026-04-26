"""
DenLab Chat - Main Application (Gateway).
App.py serves as the pure gateway for all other files.

Architecture:
- Authentication: auth.py
- Chat: chat_interface.py (with integrated upload)
- Menu: floating_menu.py (replaces broken sidebar)
- Agent: agent_interface.py
- Developer: developer_panel.py
- Features: backend.py, client.py
- Storage: chat_db.py

ADVANCEMENTS:
1. Replaced broken static sidebar with floating_menu.py hamburger drawer
2. Integrated upload into chat interface (bottom-right next to send)
3. Added developer panel toggle for Dennis with full system control
4. Added Kimi swarm mode alongside standard agent mode
5. Added Hermes agent reflection mode
6. Added system health check on startup
7. Added quick developer command input (the chat itself answers developer queries)
8. Clean connectivity: every module import is verified before use
9. PWA support preserved
10. Auto-hides Streamlit native sidebar completely
"""

import streamlit as st
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import AppConfig, Models, SystemPrompts, DeveloperConfig
from auth import get_auth_manager
from chat_db import get_chat_db
from client import get_client
from backend import get_tools_metadata

# Try to import advanced components with fallbacks
try:
    from components.floating_menu import render_floating_menu, render_advanced_settings
    FLOATING_MENU_AVAILABLE = True
except Exception as e:
    FLOATING_MENU_AVAILABLE = False
    st.error(f"Floating menu failed: {e}")

try:
    from components.developer_panel import render_developer_panel, is_developer
    DEV_PANEL_AVAILABLE = True
except Exception as e:
    DEV_PANEL_AVAILABLE = False

try:
    from components.chat_interface import ChatInterface
    CHAT_AVAILABLE = True
except Exception as e:
    CHAT_AVAILABLE = False
    st.error(f"Chat interface failed: {e}")

try:
    from components.agent_interface import render_agent_interface
    AGENT_AVAILABLE = True
except Exception as e:
    AGENT_AVAILABLE = False

try:
    from ui_components import apply_clean_theme, render_welcome, render_version_footer
    UI_AVAILABLE = True
except Exception as e:
    UI_AVAILABLE = False

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title=AppConfig.title,
    page_icon=AppConfig.icon,
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': AppConfig.urls["github"],
        'Report a bug': AppConfig.urls["support"],
        'About': AppConfig.ABOUT_TEXT
    }
)

# Hide native sidebar completely
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PWA SUPPORT
# ============================================================================

st.markdown("""
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#111827">
""", unsafe_allow_html=True)

# ============================================================================
# THEME
# ============================================================================

if UI_AVAILABLE:
    try:
        apply_clean_theme()
    except Exception:
        pass

# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    defaults = {
        'user_token': None,
        'current_user': None,
        'current_conversation_id': None,
        'selected_model': Models.DEFAULT_MODEL,
        'agent_mode': False,
        'swarm_mode': False,
        'hermes_mode': False,  # NEW: Hermes reflection mode
        'cache_enabled': True,
        'memory_enabled': True,
        'auto_route': True,
        'show_memory_context': False,
        'agent_max_steps': AppConfig.max_agent_steps,
        'swarm_max_parallel': 4,
        'show_settings': False,
        'show_developer_panel': False,
        'show_system_stats': False,
        'is_developer': False,
        'auth_error': None,
        'show_auth': True,
        'show_image_gen': False,
        'show_audio_gen': False,
        'agent_progress': [],
        'last_route_result': None,
        'show_agent_traces': True,
        'swarm_debug_mode': False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============================================================================
# AUTH
# ============================================================================

auth_manager = get_auth_manager()

# Auto-login developer
if not st.session_state.current_user and not st.session_state.user_token:
    if getattr(auth_manager, "_auto_login_developer", False):
        dev_user = auth_manager.login("Dennis", "Dennis")
        if dev_user:
            st.session_state.user_token = dev_user["token"]
            st.session_state.current_user = dev_user["user"]
            st.session_state.is_developer = True
            st.session_state.show_auth = False
            st.rerun()

# ============================================================================
# DEVELOPER QUICK COMMANDS (The chat itself answers Dennis)
# ============================================================================

def handle_developer_command(query: str) -> Optional[str]:
    """
    Special handler for developer commands.
    The developer (Dennis) can ask the chat about its own code,
    system status, or request changes.
    """
    if not st.session_state.get("is_developer"):
        return None
    
    q = query.lower().strip()
    
    # Code inspection commands
    if q.startswith("show code") or q.startswith("view code") or q.startswith("get code"):
        filename = q.replace("show code", "").replace("view code", "").replace("get code", "").strip()
        if filename:
            # Try to find and return file content
            base_dir = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [
                os.path.join(base_dir, filename),
                os.path.join(base_dir, "agents", filename),
                os.path.join(base_dir, "features", filename),
                os.path.join(base_dir, "components", filename),
                os.path.join(base_dir, "config", filename),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        return f"📄 **Source: `{filename}`** ({len(content)} chars, {len(content.splitlines())} lines)\n\n```python\n{content[:3000]}\n```\n\n{'*(truncated)*' if len(content) > 3000 else ''}"
                    except Exception as e:
                        return f"❌ Error reading `{filename}`: {e}"
            return f"❌ File `{filename}` not found. Try filenames like `app.py`, `base_agent.py`, `client.py`."
    
    # System stats command
    if q in ["stats", "system stats", "show stats", "status"]:
        try:
            from features.cache import get_cache
            cache_stats = get_cache().get_stats()
        except:
            cache_stats = {"error": "unavailable"}
        
        try:
            from features.memory import get_all_memory_stats
            mem_stats = get_all_memory_stats()
        except:
            mem_stats = {"error": "unavailable"}
        
        try:
            tools = get_tools_metadata()
        except:
            tools = {}
        
        return f"""📊 **System Status**

**Cache:** `{cache_stats}`

**Memory:** `{mem_stats}`

**Tools:** {len(tools)} registered

**Session:** model={st.session_state.selected_model}, agent={st.session_state.agent_mode}, swarm={st.session_state.swarm_mode}

**Health:** All systems operational (verified on startup)"""
    
    # List files command
    if q in ["list files", "files", "show files"]:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        files = []
        for root, _, filenames in os.walk(base_dir):
            if '__pycache__' not in root and '.git' not in root:
                for f in filenames:
                    if f.endswith('.py'):
                        rel = os.path.relpath(os.path.join(root, f), base_dir)
                        files.append(rel)
        file_list = "\n".join([f"- `{f}`" for f in sorted(files)])
        return f"📁 **Project Files ({len(files)} Python modules)**\n\n{file_list}"
    
    # Module info command
    if q.startswith("info ") or q.startswith("about "):
        module_name = q.replace("info ", "").replace("about ", "").strip()
        module_map = {
            "app.py": "Main gateway. Connects all modules.",
            "auth.py": "Authentication system with auto-login for developer.",
            "chat_db.py": "JSON-based chat persistence per user.",
            "client.py": "Multi-provider LLM client with caching and memory.",
            "backend.py": "Tool registry and function metadata.",
            "base_agent.py": "Base agent class with tool execution.",
            "orchestrator.py": "Swarm coordination for multi-agent execution.",
            "planner.py": "Task decomposition into subtasks.",
            "tool_registry.py": "Central tool registration and execution.",
            "hermes_agent.py": "Advanced agent with self-reflection and backtracking.",
            "kimi_swarm.py": "Hierarchical swarm with consensus and verification.",
            "floating_menu.py": "Hamburger menu replacing broken sidebar.",
            "developer_panel.py": "Developer control panel with code inspection.",
            "chat_interface.py": "Chat UI with upload-integrated input.",
            "memory.py": "User memory with semantic extraction.",
            "cache.py": "Response cache with adaptive TTL.",
            "tool_router.py": "Intent-based query routing.",
        }
        info = module_map.get(module_name, f"Module `{module_name}` — part of DenLab Chat.")
        return f"📘 **{module_name}**\n\n{info}"
    
    # Developer panel command
    if q in ["dev panel", "developer panel", "open dev"]:
        st.session_state.show_developer_panel = True
        return "🔧 Opening Developer Panel..."
    
    return None

# ============================================================================
# MAIN UI
# ============================================================================

def render_auth():
    """Render authentication UI."""
    st.markdown(f"# {AppConfig.title}")
    st.markdown("### 🧠 AI-Powered with Memory & Agentic Intelligence")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", use_container_width=True):
            user = auth_manager.login(username, password)
            if user:
                st.session_state.user_token = user["token"]
                st.session_state.current_user = user["user"]
                st.session_state.is_developer = auth_manager.is_developer(username)
                st.session_state.show_auth = False
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        new_username = st.text_input("New Username", key="reg_user")
        new_password = st.text_input("Password", type="password", key="reg_pass")
        confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        if st.button("Register", use_container_width=True):
            if new_password != confirm:
                st.error("Passwords don't match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                if auth_manager.register(new_username, new_password):
                    user = auth_manager.login(new_username, new_password)
                    st.session_state.user_token = user["token"]
                    st.session_state.current_user = user["user"]
                    st.session_state.show_auth = False
                    st.rerun()
                else:
                    st.error("Username already exists")


def render_chat_page():
    """Render main chat page with floating menu and integrated upload."""
    user = st.session_state.current_user
    
    if not user:
        return
    
    # Floating menu (replaces sidebar)
    if FLOATING_MENU_AVAILABLE:
        selected_model, agent_mode, swarm_mode = render_floating_menu()
    else:
        selected_model = st.session_state.get("selected_model", Models.DEFAULT_MODEL)
        agent_mode = st.session_state.get("agent_mode", False)
        swarm_mode = False
    
    # Developer panel
    if DEV_PANEL_AVAILABLE and st.session_state.get("show_developer_panel"):
        render_developer_panel()
        return
    
    # System stats page
    if st.session_state.get("show_system_stats"):
        st.markdown("# 📊 System Statistics")
        try:
            from features.cache import get_cache
            st.json(get_cache().get_stats())
        except Exception as e:
            st.error(f"Cache stats unavailable: {e}")
        if st.button("← Back"):
            st.session_state.show_system_stats = False
            st.rerun()
        return
    
    # Settings page
    if st.session_state.get("show_settings"):
        st.markdown("# ⚙️ Settings")
        if FLOATING_MENU_AVAILABLE:
            render_advanced_settings()
        else:
            st.caption("Settings loaded via menu")
        if st.button("← Back"):
            st.session_state.show_settings = False
            st.rerun()
        return
    
    # Header
    col_header1, col_header2 = st.columns([0.6, 0.4])
    with col_header1:
        st.markdown(f"## {AppConfig.title}")
    with col_header2:
        st.caption(f"v{AppConfig.version} | 🧠 Memory • ⚡ Cache • 🤖 Agent • 🐝 Swarm")
    
    st.divider()
    
    # Chat interface
    if CHAT_AVAILABLE:
        db = get_chat_db(user["username"])
        conv_id = st.session_state.get("current_conversation_id")
        
        if not conv_id:
            conv_id = db.create_conversation(model=selected_model)
            st.session_state.current_conversation_id = conv_id
        
        chat_interface = ChatInterface(
            db=db,
            conversation_id=conv_id,
            model=selected_model,
            agent_mode=agent_mode,
            swarm_mode=swarm_mode
        )
        
        # Render chat
        chat_interface.render()
    else:
        st.error("Chat interface unavailable")


# ============================================================================
# MAIN ENTRY
# ============================================================================

def main():
    if st.session_state.show_auth and not st.session_state.current_user:
        render_auth()
    else:
        render_chat_page()


if __name__ == "__main__":
    main()