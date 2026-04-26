"""
Developer Panel for DenLab Chat.
Gives the developer (Dennis) comprehensive control and visibility into:
- Source code inspection of all running files
- System statistics and health
- User management
- Cache and memory inspection
- Live logs and traces
- Runtime configuration changes
- Agent execution debugging

Connected to: app.py (gateway), auth.py (users), chat_db.py (conversations),
client.py (API stats), features/cache.py (cache), features/memory.py (memory),
backend.py (tools metadata).
"""

import streamlit as st
import json
import os
import sys
import time
import inspect
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AppConfig, DeveloperConfig
from auth import get_auth_manager
from chat_db import get_chat_db, delete_user_chat_data
from backend import get_tools_metadata


# ============================================================================
# DEVELOPER PANEL
# ============================================================================

class DeveloperPanel:
    """
    Comprehensive developer control panel.
    
    Access: Only available when is_developer=True in session state.
    Features:
    - Code Inspector: View any file's source code
    - System Stats: Cache, memory, sessions, users
    - User Management: List, view, delete users
    - Runtime Config: Modify settings on the fly
    - Agent Debug: View traces, tool calls, routing decisions
    - Health Check: Verify all file connections
    """
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def render(self):
        """Render the full developer panel."""
        if not st.session_state.get("is_developer"):
            st.error("Access denied. Developer only.")
            return
        
        st.markdown("# 👑 Developer Control Panel")
        st.markdown(f"**Developer:** {DeveloperConfig.DISPLAY_NAME} | **Version:** {AppConfig.version}")
        st.divider()
        
        tabs = st.tabs([
            "📁 Code Inspector",
            "📊 System Stats",
            "👥 User Mgmt",
            "⚙️ Runtime Config",
            "🐛 Agent Debug",
            "🔍 Health Check"
        ])
        
        with tabs[0]:
            self._render_code_inspector()
        with tabs[1]:
            self._render_system_stats()
        with tabs[2]:
            self._render_user_management()
        with tabs[3]:
            self._render_runtime_config()
        with tabs[4]:
            self._render_agent_debug()
        with tabs[5]:
            self._render_health_check()
        
        st.divider()
        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.show_developer_panel = False
            st.rerun()
    
    # ========================================================================
    # Tab 1: Code Inspector
    # ========================================================================
    
    def _render_code_inspector(self):
        """Allow developer to inspect any source file."""
        st.markdown("### 📁 Source Code Inspector")
        st.caption("View the exact code running in each module.")
        
        # Discover all Python files
        py_files = self._discover_python_files()
        
        selected_file = st.selectbox(
            "Select file to inspect",
            options=py_files,
            format_func=lambda x: x.replace(self.project_root + "/", "")
        )
        
        if selected_file:
            try:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Stats
                lines = content.split('\n')
                st.caption(f"📐 {len(lines)} lines | {len(content)} chars | {os.path.getmtime(selected_file):.0f} modified")
                
                # Show code
                rel_path = selected_file.replace(self.project_root + "/", "")
                st.code(content, language="python")
                
                # Copy button
                escaped = json.dumps(content)
                st.markdown(f"""
                <button onclick="navigator.clipboard.writeText({escaped})" 
                    style="background:#10a37f;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">
                    📋 Copy Code
                </button>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    def _discover_python_files(self) -> List[str]:
        """Discover all Python files in the project."""
        files = []
        for root, _, filenames in os.walk(self.project_root):
            # Skip hidden dirs, data dirs, and venv
            if any(skip in root for skip in ['__pycache__', '.git', 'data/', 'venv', 'env/', '.streamlit']):
                continue
            for f in filenames:
                if f.endswith('.py'):
                    files.append(os.path.join(root, f))
        return sorted(files)
    
    # ========================================================================
    # Tab 2: System Stats
    # ========================================================================
    
    def _render_system_stats(self):
        """Show system-wide statistics."""
        st.markdown("### 📊 System Statistics")
        
        # Cache stats
        try:
            from features.cache import get_cache
            cache = get_cache()
            cache_stats = cache.get_stats()
        except Exception as e:
            cache_stats = {"error": str(e)}
        
        # Memory stats
        try:
            from features.memory import get_all_memory_stats
            memory_stats = get_all_memory_stats()
        except Exception as e:
            memory_stats = {"error": str(e)}
        
        # Auth stats
        try:
            auth = get_auth_manager()
            user_count = auth.get_user_count()
            session_count = auth.get_active_sessions_count()
        except Exception as e:
            user_count = 0
            session_count = 0
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Registered Users", user_count)
        with col2:
            st.metric("Active Sessions", session_count)
        with col3:
            st.metric("Cache Entries", cache_stats.get("size", 0))
        with col4:
            total_mem_users = len(memory_stats) if isinstance(memory_stats, dict) else 0
            st.metric("Memory Users", total_mem_users)
        
        st.divider()
        
        # Cache details
        with st.expander("💾 Cache Details"):
            st.json(cache_stats)
            if st.button("🗑️ Clear All Cache", key="dev_clear_cache"):
                cache.clear()
                st.success("Cache cleared!")
                st.rerun()
        
        # Memory details
        with st.expander("🧠 Memory Details"):
            st.json(memory_stats)
        
        # Tool registry
        with st.expander("🔧 Tool Registry"):
            try:
                tools = get_tools_metadata()
                st.json({name: {"desc": info["description"], "params": list(info["params"].keys())} 
                        for name, info in tools.items()})
            except Exception as e:
                st.error(f"Tool registry error: {e}")
    
    # ========================================================================
    # Tab 3: User Management
    # ========================================================================
    
    def _render_user_management(self):
        """Manage users and their data."""
        st.markdown("### 👥 User Management")
        
        auth = get_auth_manager()
        
        # Cannot easily list all users from AuthManager (private _users),
        # so we use file-based discovery
        data_dir = os.path.join(self.project_root, "data")
        user_files = []
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                if f.startswith("chats_") and f.endswith(".json"):
                    username = f[6:-5]  # Extract username from chats_<user>.json
                    user_files.append(username)
        
        st.markdown(f"**Users with chat data:** {len(user_files)}")
        
        for username in sorted(user_files):
            db = get_chat_db(username)
            stats = db.get_stats()
            
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.markdown(f"**@{username}**")
            with col2:
                st.caption(f"{stats['conversation_count']} convs")
            with col3:
                st.caption(f"{stats['total_messages']} msgs")
            with col4:
                if st.button("🗑", key=f"del_user_{username}", help=f"Delete {username}'s data"):
                    delete_user_chat_data(username)
                    st.success(f"Deleted data for @{username}")
                    st.rerun()
        
        st.divider()
        st.markdown("#### Danger Zone")
        if st.button("⚠️ Delete ALL User Data", type="primary", key="dev_delete_all"):
            confirm = st.checkbox("I understand this will delete all chat data for all users", key="dev_confirm_delete")
            if confirm:
                for username in user_files:
                    delete_user_chat_data(username)
                st.success("All user data deleted!")
                st.rerun()
    
    # ========================================================================
    # Tab 4: Runtime Config
    # ========================================================================
    
    def _render_runtime_config(self):
        """Modify runtime configuration."""
        st.markdown("### ⚙️ Runtime Configuration")
        st.warning("Changes here affect the current session only. Restart to reset.")
        
        # Agent config
        st.markdown("#### Agent Settings")
        st.session_state.agent_max_steps = st.slider(
            "Max Agent Steps",
            5, 100,
            st.session_state.get("agent_max_steps", AppConfig.max_agent_steps),
            key="dev_agent_steps"
        )
        st.session_state.swarm_max_parallel = st.slider(
            "Swarm Max Parallel",
            1, 16,
            st.session_state.get("swarm_max_parallel", 4),
            key="dev_swarm_parallel"
        )
        
        # Cache/Memory toggles
        st.markdown("#### Subsystem Toggles")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.cache_enabled = st.toggle("Cache", st.session_state.get("cache_enabled", True), key="dev_cache")
        with col2:
            st.session_state.memory_enabled = st.toggle("Memory", st.session_state.get("memory_enabled", True), key="dev_memory")
        with col3:
            st.session_state.auto_route = st.toggle("Auto Route", st.session_state.get("auto_route", True), key="dev_autoroute")
        
        # Developer debug flags
        st.markdown("#### Debug Flags")
        st.session_state.show_agent_traces = st.toggle(
            "Show Agent Traces",
            st.session_state.get("show_agent_traces", True),
            key="dev_show_traces"
        )
        st.session_state.swarm_debug_mode = st.toggle(
            "Swarm Debug Mode",
            st.session_state.get("swarm_debug_mode", False),
            key="dev_swarm_debug"
        )
        st.session_state.show_memory_context = st.toggle(
            "Show Memory Context",
            st.session_state.get("show_memory_context", False),
            key="dev_show_mem_ctx"
        )
        
        # Session state dump
        with st.expander("🔍 Full Session State"):
            safe_state = {k: str(v)[:500] for k, v in st.session_state.items()}
            st.json(safe_state)
    
    # ========================================================================
    # Tab 5: Agent Debug
    # ========================================================================
    
    def _render_agent_debug(self):
        """Debug agent execution."""
        st.markdown("### 🐛 Agent Debug Console")
        
        # Show last agent progress
        progress = st.session_state.get("agent_progress", [])
        if progress:
            st.markdown("#### Recent Agent Progress")
            for item in progress[-10:]:
                st.json(item)
        else:
            st.info("No agent activity recorded yet. Run an agent task to see traces here.")
        
        # Tool routing log
        with st.expander("🧭 Last Routing Decision"):
            last_route = st.session_state.get("last_route_result")
            if last_route:
                st.json(last_route)
            else:
                st.caption("No routing data available")
        
        # Manual tool test
        st.markdown("#### Manual Tool Test")
        tool_name = st.selectbox(
            "Select tool",
            ["web_search", "deep_research", "get_current_time", "calculate", "list_files"],
            key="dev_tool_select"
        )
        tool_input = st.text_area("Tool arguments (JSON)", '{"query": "AI news"}', key="dev_tool_input")
        
        if st.button("▶️ Execute Tool", key="dev_exec_tool"):
            try:
                from agents.tool_registry import get_tool_registry
                registry = get_tool_registry()
                args = json.loads(tool_input)
                result = registry.execute(tool_name, **args)
                st.success("Tool executed!")
                st.json(json.loads(result) if isinstance(result, str) and result.startswith("{") else {"result": result})
            except Exception as e:
                st.error(f"Tool execution failed: {e}")
    
    # ========================================================================
    # Tab 6: Health Check
    # ========================================================================
    
    def _render_health_check(self):
        """Check connectivity between all files."""
        st.markdown("### 🔍 System Health Check")
        st.caption("Verifies that all modules can import and communicate correctly.")
        
        checks = []
        
        # Check config
        try:
            from config.settings import AppConfig, Models, SystemPrompts
            checks.append(("✅", "config/settings.py", "Settings loaded"))
        except Exception as e:
            checks.append(("❌", "config/settings.py", str(e)))
        
        # Check auth
        try:
            from auth import get_auth_manager
            auth = get_auth_manager()
            checks.append(("✅", "auth.py", f"AuthManager ready ({auth.get_user_count()} users)"))
        except Exception as e:
            checks.append(("❌", "auth.py", str(e)))
        
        # Check chat_db
        try:
            from chat_db import get_chat_db
            checks.append(("✅", "chat_db.py", "Database module ready"))
        except Exception as e:
            checks.append(("❌", "chat_db.py", str(e)))
        
        # Check client
        try:
            from client import get_client
            client = get_client()
            checks.append(("✅", "client.py", "MultiProviderClient ready"))
        except Exception as e:
            checks.append(("❌", "client.py", str(e)))
        
        # Check backend tools
        try:
            from backend import get_tools_metadata
            tools = get_tools_metadata()
            checks.append(("✅", "backend.py", f"{len(tools)} tools registered"))
        except Exception as e:
            checks.append(("❌", "backend.py", str(e)))
        
        # Check tool_registry
        try:
            from agents.tool_registry import get_tool_registry
            reg = get_tool_registry()
            checks.append(("✅", "agents/tool_registry.py", f"{reg.get_tools_count()} tools in registry"))
        except Exception as e:
            checks.append(("❌", "agents/tool_registry.py", str(e)))
        
        # Check base_agent
        try:
            from agents.base_agent import BaseAgent, create_simple_agent
            checks.append(("✅", "agents/base_agent.py", "Agent classes ready"))
        except Exception as e:
            checks.append(("❌", "agents/base_agent.py", str(e)))
        
        # Check orchestrator
        try:
            from agents.orchestrator import get_swarm
            checks.append(("✅", "agents/orchestrator.py", "Swarm orchestrator ready"))
        except Exception as e:
            checks.append(("❌", "agents/orchestrator.py", str(e)))
        
        # Check planner
        try:
            from agents.planner import get_planner
            checks.append(("✅", "agents/planner.py", "Task planner ready"))
        except Exception as e:
            checks.append(("❌", "agents/planner.py", str(e)))
        
        # Check memory
        try:
            from features.memory import get_memory
            checks.append(("✅", "features/memory.py", "Memory system ready"))
        except Exception as e:
            checks.append(("❌", "features/memory.py", str(e)))
        
        # Check cache
        try:
            from features.cache import get_cache
            cache = get_cache()
            checks.append(("✅", "features/cache.py", "Cache system ready"))
        except Exception as e:
            checks.append(("❌", "features/cache.py", str(e)))
        
        # Check tool_router
        try:
            from features.tool_router import get_router
            checks.append(("✅", "features/tool_router.py", "Intent router ready"))
        except Exception as e:
            checks.append(("❌", "features/tool_router.py", str(e)))
        
        # Check vision
        try:
            from features.vision import VisionAnalyzer
            checks.append(("✅", "features/vision.py", "Vision analyzer ready"))
        except Exception as e:
            checks.append(("❌", "features/vision.py", str(e)))
        
        # Check components
        try:
            from components.floating_menu import FloatingMenu
            checks.append(("✅", "components/floating_menu.py", "Floating menu ready"))
        except Exception as e:
            checks.append(("❌", "components/floating_menu.py", str(e)))
        
        try:
            from components.chat_interface import ChatInterface
            checks.append(("✅", "components/chat_interface.py", "Chat interface ready"))
        except Exception as e:
            checks.append(("❌", "components/chat_interface.py", str(e)))
        
        # Check Hermes/Kimi new modules
        try:
            from agents.hermes_agent import HermesAgent
            checks.append(("✅", "agents/hermes_agent.py", "Hermes agent ready"))
        except Exception as e:
            checks.append(("❌", "agents/hermes_agent.py", str(e)))
        
        try:
            from agents.kimi_swarm import KimiSwarmOrchestrator
            checks.append(("✅", "agents/kimi_swarm.py", "Kimi swarm ready"))
        except Exception as e:
            checks.append(("❌", "agents/kimi_swarm.py", str(e)))
        
        # Display results
        for icon, name, status in checks:
            color = "#10a37f" if icon == "✅" else "#ef4444"
            st.markdown(f"<span style='color:{color}'>{icon}</span> **{name}** — {status}", unsafe_allow_html=True)
        
        # Summary
        total = len(checks)
        passed = sum(1 for c in checks if c[0] == "✅")
        st.divider()
        st.markdown(f"**Health Score:** {passed}/{total} modules healthy")
        
        if passed == total:
            st.success("🎉 All systems operational!")
        elif passed >= total * 0.8:
            st.warning("⚠️ Most systems operational. Check failed modules above.")
        else:
            st.error("🚨 Multiple system failures detected. Review errors above.")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def render_developer_panel():
    """Convenience function to render the developer panel."""
    panel = DeveloperPanel()
    panel.render()


def is_developer() -> bool:
    """Check if current session is developer."""
    return st.session_state.get("is_developer", False)
