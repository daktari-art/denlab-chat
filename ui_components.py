"""
UI Components for DenLab Chat.
Reusable UI elements - buttons, CSS themes, progress displays, etc.
No business logic - just pure UI helpers.
"""

import streamlit as st
import json
from typing import Optional, Dict, Any, List, Callable

# Import from config (for version, theme colors)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AppConfig


# ============================================================================
# CSS THEMES
# ============================================================================

def apply_clean_theme():
    """Apply the clean light theme to the app."""
    st.markdown("""
    <style>
        /* Import font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }
        
        /* Main background */
        .stApp {
            background-color: #f5f5f5 !important;
        }
        
        /* Main content area - CRITICAL: enough padding at bottom so chat input doesn't hide content */
        .main .block-container {
            max-width: 800px !important;
            margin: 0 auto !important;
            padding: 1rem 1rem 140px 1rem !important;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #222222 !important;
            min-width: 260px !important;
            width: 260px !important;
        }
        
        [data-testid="stSidebar"] .block-container {
            padding: 1rem !important;
        }
        
        /* Sidebar text colors */
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] div:not(.stButton) {
            color: #e0e0e0 !important;
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #ffffff !important;
        }
        
        /* Chat messages container */
        .stChatMessage {
            background: transparent !important;
            border: none !important;
            margin-bottom: 8px !important;
        }
        
        /* Message bubbles - uniform styling */
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            background: #ffffff !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            margin: 4px 0 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }
        
        /* User message specific - subtle distinction */
        [data-testid="stChatMessage"][data-testid*="user"] [data-testid="stMarkdownContainer"] {
            background: #f0f7ff !important;
        }
        
        /* ALL text inside messages - uniform base size */
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            font-size: 14px !important;
            line-height: 1.6 !important;
            color: #333 !important;
        }
        
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
            font-size: 14px !important;
            line-height: 1.6 !important;
        }
        
        /* Headers inside messages - BOLD but SAME SIZE as regular text */
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h4,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h5,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h6,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong {
            font-size: 14px !important;
            font-weight: 700 !important;
            margin-top: 12px !important;
            margin-bottom: 6px !important;
            color: #111 !important;
        }
        
        /* First header in message - no top margin */
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1:first-child,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2:first-child,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3:first-child {
            margin-top: 0 !important;
        }
        
        /* Paragraphs inside messages */
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
            font-size: 14px !important;
            margin-bottom: 10px !important;
            color: #333 !important;
            line-height: 1.6 !important;
        }
        
        /* Lists inside messages */
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ul,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ol {
            margin: 6px 0 10px 20px !important;
            padding-left: 0 !important;
        }
        
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
            font-size: 14px !important;
            margin-bottom: 4px !important;
            color: #333 !important;
            line-height: 1.6 !important;
        }
        
        /* Code blocks */
        [data-testid="stChatMessage"] pre {
            background: #f6f8fa !important;
            border: 1px solid #e1e4e8 !important;
            border-radius: 10px !important;
            padding: 14px !important;
            overflow-x: auto !important;
            margin: 12px 0 !important;
        }
        
        [data-testid="stChatMessage"] code {
            background: #f0f0f0 !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            font-size: 13px !important;
            font-family: 'SF Mono', 'Fira Code', monospace !important;
            color: #d14 !important;
        }
        
        [data-testid="stChatMessage"] pre code {
            background: transparent !important;
            padding: 0 !important;
            font-size: 13px !important;
            color: #333 !important;
        }
        
        /* Blockquotes */
        [data-testid="stChatMessage"] blockquote {
            border-left: 3px solid #10a37f !important;
            margin: 10px 0 !important;
            padding-left: 15px !important;
            color: #666 !important;
            font-style: italic !important;
        }
        
        /* Chat input - FIXED POSITION - no overlap */
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
        
        .stChatInput:focus-within {
            border-color: #10a37f !important;
            box-shadow: 0 4px 12px rgba(16, 163, 127, 0.15) !important;
        }
        
        .stChatInput textarea {
            background: transparent !important;
            border: none !important;
            color: #333 !important;
            font-size: 14px !important;
            padding: 10px 0 !important;
        }
        
        .stChatInput textarea::placeholder {
            color: #999 !important;
        }
        
        .stChatInput button {
            background: #10a37f !important;
            border-radius: 50% !important;
            color: white !important;
        }
        
        .stChatInput button:hover {
            background: #0d8c6d !important;
        }
        
        /* Hide default Streamlit elements */
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        header { visibility: hidden !important; }
        .stDeployButton { display: none !important; }
        
        /* Button styling */
        .stButton button {
            background: transparent !important;
            color: #666 !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 8px !important;
            padding: 6px 12px !important;
            font-size: 12px !important;
            transition: all 0.15s ease !important;
        }
        
        .stButton button:hover {
            background: #f5f5f5 !important;
            border-color: #ccc !important;
            color: #333 !important;
        }
        
        .stButton button[kind="primary"] {
            background: #111111 !important;
            color: #ffffff !important;
            border-color: #111111 !important;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background: #f8f9fa !important;
            border-radius: 10px !important;
            font-size: 13px !important;
            color: #333 !important;
        }
        
        /* Animations */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Status dots */
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }
        
        .status-online {
            background: #10a37f;
        }
        
        .status-busy {
            background: #f59e0b;
            animation: pulse 1.5s infinite;
        }
        
        .status-offline {
            background: #ef4444;
        }
        
        /* Developer badge */
        .dev-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: #fef3c7;
            border: 1px solid #fbbf24;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            color: #92400e;
        }
        
        /* Agent badge */
        .agent-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 20px;
            font-size: 12px;
            color: #166534;
            font-weight: 500;
        }
        
        .agent-dot {
            width: 6px;
            height: 6px;
            background: #10a37f;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        
        /* File attachment */
        .file-attachment {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            font-size: 13px;
            color: #555;
            margin: 4px 0;
        }
        
        /* Agent progress container */
        .agent-progress-container {
            background: #ffffff !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 12px !important;
            padding: 14px 16px !important;
            margin: 8px 0 !important;
        }
        
        /* Swarm progress container */
        .swarm-progress-container {
            background: #f0fdf4 !important;
            border: 1px solid #bbf7d0 !important;
            border-radius: 12px !important;
            padding: 14px 16px !important;
            margin: 8px 0 !important;
        }
        
        /* Divider */
        hr {
            border-color: #e8e8e8 !important;
            margin: 12px 0 !important;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #d0d0d0;
            border-radius: 3px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #aaa;
        }
        
        /* Loading spinner */
        .stSpinner > div {
            border-color: #10a37f !important;
        }
        
        /* Toast/Success messages */
        .stAlert {
            border-radius: 10px !important;
            font-size: 13px !important;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .stChatInput {
                width: calc(100% - 20px) !important;
            }
            .main .block-container {
                padding: 0.5rem 0.5rem 100px 0.5rem !important;
            }
            [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
                padding: 8px 12px !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)


def apply_dark_theme():
    """Apply dark theme (alternative)."""
    st.markdown("""
    <style>
        .stApp {
            background-color: #0d0d0d !important;
        }
        
        [data-testid="stSidebar"] {
            background-color: #0a0a0a !important;
            border-right: 1px solid #1a1a1a !important;
        }
        
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            background: #1a1a1a !important;
            color: #e0e0e0 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.2) !important;
        }
        
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
            color: #e0e0e0 !important;
        }
        
        .stChatInput {
            background: #1a1a1a !important;
            border: 1px solid #2a2a2a !important;
        }
        
        .stChatInput textarea {
            color: #e0e0e0 !important;
        }
        
        .stChatInput textarea::placeholder {
            color: #666 !important;
        }
        
        pre {
            background: #1a1a1a !important;
            border-color: #2a2a2a !important;
        }
        
        code {
            background: #252525 !important;
            color: #a5b4fc !important;
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# MESSAGE ACTIONS
# ============================================================================

def render_message_actions(
    msg_idx: int,
    content: str,
    msg_type: str = "text",
    on_copy: Optional[Callable] = None,
    on_speak: Optional[Callable] = None,
    on_regen: Optional[Callable] = None,
    on_download: Optional[Callable] = None,
    on_like: Optional[Callable] = None
):
    """
    Render compact action buttons below a message.
    
    Args:
        msg_idx: Message index for unique keys
        content: Message content
        msg_type: Type of message (text, image, audio, code)
        on_copy: Callback for copy action
        on_speak: Callback for text-to-speech
        on_regen: Callback for regenerate
        on_download: Callback for download
        on_like: Callback for like/feedback
    """
    cols = st.columns([1, 1, 1, 1, 1, 20])
    
    with cols[0]:
        if st.button("📋", key=f"act_copy_{msg_idx}", help="Copy to clipboard"):
            if on_copy:
                on_copy(content)
            else:
                st.toast("Copied!")
    
    with cols[1]:
        if st.button("🔊", key=f"act_speak_{msg_idx}", help="Text to speech"):
            if on_speak:
                on_speak(content)
            else:
                try:
                    import requests
                    audio_url = f"https://gen.pollinations.ai/audio/{requests.utils.quote(content[:500])}?voice=nova"
                    st.audio(audio_url, format='audio/mp3')
                except:
                    st.toast("Audio unavailable")
    
    with cols[2]:
        if st.button("🔄", key=f"act_regen_{msg_idx}", help="Regenerate"):
            if on_regen:
                on_regen(msg_idx)
            else:
                if "messages" in st.session_state:
                    st.session_state.messages = st.session_state.messages[:msg_idx]
                st.rerun()
    
    with cols[3]:
        if msg_type == "text":
            if st.download_button(
                label="⬇️",
                data=content,
                file_name=f"message_{msg_idx}.md",
                mime="text/markdown",
                key=f"act_dl_{msg_idx}",
                help="Download"
            ):
                if on_download:
                    on_download(content)
    
    with cols[4]:
        if st.button("👍", key=f"act_like_{msg_idx}", help="Helpful"):
            if on_like:
                on_like(msg_idx)
            else:
                st.toast("Thanks for the feedback!")


# ============================================================================
# AGENT PROGRESS DISPLAY
# ============================================================================

def render_agent_progress(
    step: int,
    max_steps: int,
    thought: Optional[str] = None,
    tool_calls: Optional[List[Dict]] = None,
    status: str = "running"
):
    """
    Render agent progress container.
    
    Args:
        step: Current step number
        max_steps: Maximum steps
        thought: Agent's thought/reasoning
        tool_calls: List of tool calls with results
        status: Status (running, complete, error)
    """
    progress_percent = int((step / max_steps) * 100) if max_steps > 0 else 0
    
    if status == "complete":
        bg_color = "#d1fae5"
        border_color = "#bbf7d0"
        icon = "✅"
        title = "Complete"
    elif status == "error":
        bg_color = "#fee2e2"
        border_color = "#fecaca"
        icon = "❌"
        title = "Error"
    else:
        bg_color = "#ffffff"
        border_color = "#e0e0e0"
        icon = "🤖"
        title = f"Step {step}/{max_steps}"
    
    html = f"""
    <div class="agent-progress-container" style="background:{bg_color};border-color:{border_color};">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span>{icon}</span>
            <span style="font-weight:500;">{title}</span>
            <span style="width:7px;height:7px;border-radius:50%;background:#f59e0b;display:inline-block;"></span>
        </div>
        <div style="height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden;margin-bottom:10px;">
            <div style="height:100%;width:{progress_percent}%;background:linear-gradient(90deg,#10a37f,#34d399);border-radius:2px;"></div>
        </div>
    """
    
    if thought:
        html += f'<div style="font-size:12px;color:#666;margin-top:8px;">💭 {thought[:200]}...</div>'
    
    if tool_calls:
        html += '<div style="margin-top:8px;">'
        for tc in tool_calls:
            icon = "✓" if tc.get("status") == "success" else "✗" if tc.get("status") == "error" else "◐"
            color = "#10a37f" if tc.get("status") == "success" else "#ef4444" if tc.get("status") == "error" else "#3b82f6"
            html += f'<div style="font-size:11px;margin:4px 0;color:{color};">'
            html += f'{icon} <code>{tc.get("name", "unknown")}</code>'
            if tc.get("duration_ms"):
                html += f' <span style="color:#999;">({tc.get("duration_ms"):.0f}ms)</span>'
            html += '</div>'
        html += '</div>'
    
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)


def render_swarm_progress(
    current: int,
    total: int,
    agent_type: str,
    description: str,
    status: str = "running"
):
    """
    Render swarm progress container.
    
    Args:
        current: Current sub-task number
        total: Total sub-tasks
        agent_type: Type of agent (researcher, coder, analyst, writer)
        description: Task description
        status: Status (running, complete)
    """
    icons = {
        "researcher": "🔍",
        "coder": "💻",
        "analyst": "📊",
        "writer": "✍️"
    }
    icon = icons.get(agent_type, "🤖")
    progress_percent = int((current / total) * 100) if total > 0 else 0
    
    if status == "complete":
        bg_color = "#f0fdf4"
        border_color = "#bbf7d0"
    else:
        bg_color = "#ffffff"
        border_color = "#e0e0e0"
    
    html = f"""
    <div class="swarm-progress-container" style="background:{bg_color};border-color:{border_color};">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span>{icon}</span>
            <span style="font-weight:500;">{agent_type.upper()} Agent</span>
            <span style="color:#3b82f6;font-size:12px;">({current}/{total})</span>
        </div>
        <div style="height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden;margin-bottom:8px;">
            <div style="height:100%;width:{progress_percent}%;background:#10a37f;border-radius:2px;"></div>
        </div>
        <div style="font-size:11px;color:#666;">{description[:100]}</div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)


# ============================================================================
# WELCOME SCREEN
# ============================================================================

def render_welcome():
    """Render the welcome screen when no messages exist."""
    st.markdown(f"""
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:48px;margin-bottom:16px;">🧠</div>
        <div style="font-size:24px;font-weight:700;color:#111;margin-bottom:8px;">{AppConfig.title}</div>
        <div style="font-size:14px;color:#666;margin-bottom:32px;">Advanced AI Assistant with Swarm Agents</div>
        <div style="font-size:13px;color:#888;line-height:2.2;">
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/imagine</code> — Generate images</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/research</code> — Deep web research</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/code</code> — Generate & execute Python</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/analyze</code> — Analyze uploaded files</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/audio</code> — Text to speech</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/agent</code> — Standard or Swarm agent</div>
        </div>
        <div style="margin-top:40px;font-size:11px;color:#aaa;">
            🧠 Memory • ⚡ Cache • 🤖 Agent • 🐝 Swarm • 🐙 GitHub
        </div>
        <div style="margin-top:8px;font-size:10px;color:#ccc;">
            v{AppConfig.version}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# BADGES AND INDICATORS
# ============================================================================

def render_developer_badge():
    """Render developer mode badge for sidebar."""
    st.markdown("""
    <div class="dev-badge">
        👑 Developer Mode
    </div>
    """, unsafe_allow_html=True)


def render_agent_badge(agent_type: str = "standard"):
    """Render agent mode badge."""
    if agent_type == "swarm":
        st.markdown("""
        <div class="agent-badge">
            <div class="agent-dot"></div>
            <span>🐝 Swarm Mode</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="agent-badge">
            <div class="agent-dot"></div>
            <span>🤖 Agent Mode</span>
        </div>
        """, unsafe_allow_html=True)


def render_file_attachment(filename: str, file_type: str = "text"):
    """Render a file attachment card."""
    icon = "📎" if file_type == "text" else "🖼️" if file_type == "image" else "📄"
    st.markdown(f"""
    <div class="file-attachment">
        <span>{icon}</span>
        <span class="file-name">{filename}</span>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# STATUS INDICATORS
# ============================================================================

def status_online() -> str:
    """Return online status dot HTML."""
    return '<span class="status-dot status-online"></span>'


def status_busy() -> str:
    """Return busy status dot HTML."""
    return '<span class="status-dot status-busy"></span>'


def status_offline() -> str:
    """Return offline status dot HTML."""
    return '<span class="status-dot status-offline"></span>'


# ============================================================================
# VERSION FOOTER
# ============================================================================

def render_version_footer():
    """Render version footer in sidebar."""
    st.caption(f"{AppConfig.title} v{AppConfig.version} | 🧠 Memory • ⚡ Cache • 🤖 Agent • 🐝 Swarm")


# ============================================================================
# COPY TO CLIPBOARD (JS Utility)
# ============================================================================

def copy_to_clipboard_js(text: str, key: str, label: str = "📋") -> str:
    """
    Generate JavaScript for copy-to-clipboard functionality.
    
    Returns:
        HTML/JS string to embed
    """
    escaped = json.dumps(text)
    return f"""
    <script>
    function copy_{key}() {{
        navigator.clipboard.writeText({escaped}).then(function() {{
            const btn = document.getElementById('btn_{key}');
            const orig = btn.innerHTML;
            btn.innerHTML = '✓';
            btn.style.color = '#10a37f';
            setTimeout(() => {{ 
                btn.innerHTML = orig;
                btn.style.color = '';
            }}, 2000);
        }});
    }}
    </script>
    <button id="btn_{key}" onclick="copy_{key}()" style="
        background: transparent;
        border: none;
        color: #666;
        padding: 4px 8px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
    " onmouseover="this.style.background='#f0f0f0'" onmouseout="this.style.background='transparent'">
        {label}
    </button>
    """


# ============================================================================
# SIMPLE STATUS MESSAGE
# ============================================================================

def render_status_message(message: str, status: str = "info"):
    """
    Render a simple status message.
    
    Args:
        message: Status message text
        status: "info", "success", "warning", "error"
    """
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    icon = icons.get(status, "ℹ️")
    
    colors = {
        "info": "#3b82f6",
        "success": "#10a37f",
        "warning": "#f59e0b",
        "error": "#ef4444"
    }
    color = colors.get(status, "#888")
    
    st.markdown(f"""
    <div style="background: #f8f9fa; border-left: 3px solid {color}; border-radius: 8px; padding: 10px 14px; margin: 8px 0;">
        <span style="font-size: 13px;">{icon} {message}</span>
    </div>
    """, unsafe_allow_html=True)