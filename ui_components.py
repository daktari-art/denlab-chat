"""UI Components for DenLab v4.2 - Kimi-inspired clean design system.
Provides reusable components for chat interface, sidebar, and agent displays.
"""
import streamlit as st
import base64
import json
from typing import Optional, Dict, Any, List, Callable

# ============ CSS THEME ============
def apply_kimi_theme():
    """Apply Kimi-inspired clean light theme."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important; }
        
        /* Main background - clean light gray */
        .stApp { background-color: #f5f5f5 !important; }
        
        .main > div {
            max-width: 800px;
            margin: 0 auto;
            padding: 0 20px 160px 20px;
        }
        
        /* Sidebar - clean dark */
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #222222 !important;
            min-width: 260px !important;
            max-width: 260px !important;
        }
        
        /* Chat messages */
        .stChatMessage {
            background-color: transparent !important;
            padding: 4px 0 !important;
            margin: 2px 0 !important;
            border: none !important;
        }
        
        [data-testid="stChatMessage"] {
            background: transparent !important;
            border: none !important;
        }
        
        [data-testid="stChatMessageContent"] {
            color: #333333 !important;
            font-size: 14px !important;
            line-height: 1.7 !important;
        }
        
        /* User message bubble */
        [data-testid="stChatMessage"][data-testid*="user"] {
            background: #ffffff !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            margin: 6px 0 !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        }
        
        /* Assistant message bubble */
        [data-testid="stChatMessage"][data-testid*="assistant"] {
            background: #ffffff !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            margin: 6px 0 !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        }
        
        /* Chat input - white/light */
        .stChatInput {
            position: fixed !important;
            bottom: 24px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: calc(100% - 320px) !important;
            max-width: 760px !important;
            background: #ffffff !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 24px !important;
            padding: 4px 12px !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important;
            z-index: 1000 !important;
        }
        
        .stChatInput:focus-within {
            border-color: #10a37f !important;
            box-shadow: 0 4px 20px rgba(16, 163, 127, 0.12) !important;
        }
        
        .stChatInput textarea {
            background: transparent !important;
            border: none !important;
            color: #333333 !important;
            font-size: 14px !important;
            padding: 12px 16px !important;
        }
        
        .stChatInput textarea::placeholder {
            color: #999999 !important;
            font-size: 14px !important;
        }
        
        .stChatInput button {
            background: #10a37f !important;
            color: white !important;
            border-radius: 50% !important;
            width: 32px !important;
            height: 32px !important;
            min-width: 32px !important;
            padding: 0 !important;
            border: none !important;
        }
        
        .stChatInput button:hover {
            background: #0d8c6d !important;
        }
        
        /* Buttons */
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
        
        /* Compact action buttons */
        .action-btn button {
            background: transparent !important;
            border: none !important;
            color: #999 !important;
            padding: 4px 6px !important;
            font-size: 13px !important;
            min-height: 28px !important;
            width: 28px !important;
            border-radius: 6px !important;
        }
        
        .action-btn button:hover {
            background: #f0f0f0 !important;
            color: #555 !important;
        }
        
        /* Code blocks */
        pre {
            background: #f6f8fa !important;
            border: 1px solid #e1e4e8 !important;
            border-radius: 10px !important;
            padding: 14px !important;
            font-size: 13px !important;
        }
        
        code {
            background: #f0f0f0 !important;
            color: #333333 !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            font-size: 13px !important;
            font-family: 'SF Mono', 'Fira Code', monospace !important;
        }
        
        pre code {
            background: transparent !important;
            padding: 0 !important;
        }
        
        /* Typography */
        h1 { font-size: 20px !important; font-weight: 700 !important; color: #111 !important; }
        h2 { font-size: 16px !important; font-weight: 600 !important; color: #333 !important; }
        h3 { font-size: 14px !important; font-weight: 600 !important; color: #444 !important; }
        h4 { font-size: 13px !important; font-weight: 600 !important; color: #555 !important; }
        p { color: #333 !important; font-size: 14px !important; line-height: 1.7 !important; }
        strong { font-weight: 600 !important; color: #222 !important; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #d0d0d0; border-radius: 3px; }
        
        /* Spinner */
        .stSpinner > div { border-color: #10a37f !important; }
        
        /* Expander */
        .stExpander {
            border: 1px solid #e8e8e8 !important;
            border-radius: 10px !important;
            background: #ffffff !important;
        }
        
        /* Dividers */
        hr { border-color: #e8e8e8 !important; margin: 10px 0 !important; }
        
        /* Caption */
        .stCaption { color: #999 !important; font-size: 11px !important; }
        
        /* Sidebar elements */
        [data-testid="stSidebar"] h1 { color: #ffffff !important; font-size: 16px !important; }
        [data-testid="stSidebar"] p { color: #888 !important; font-size: 12px !important; }
        
        [data-testid="stSidebar"] .stButton button {
            background: #1a1a1a !important;
            color: #e0e0e0 !important;
            border: 1px solid #2a2a2a !important;
            font-size: 12px !important;
        }
        
        [data-testid="stSidebar"] .stButton button:hover {
            background: #2a2a2a !important;
            border-color: #444 !important;
        }
        
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background: #1a1a1a !important;
            border-color: #2a2a2a !important;
            color: #e0e0e0 !important;
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
            animation: agent-pulse 1.5s infinite;
        }
        
        @keyframes agent-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
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
        }
        
        /* Agent progress */
        .agent-progress-container {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 14px 16px;
            margin: 8px 0;
        }
        
        .agent-step-row {
            display: flex;
            align-items: center;
            padding: 4px 0;
            font-size: 12px;
            color: #666;
        }
        
        .step-indicator {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            margin-right: 10px;
            flex-shrink: 0;
        }
        
        .step-pending { background: #f0f0f0; color: #aaa; }
        .step-running { background: #dbeafe; color: #3b82f6; }
        .step-success { background: #d1fae5; color: #10a37f; }
        .step-error { background: #fee2e2; color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)


# ============ SIDEBAR COMPONENT ============
def render_sidebar(model: str, sessions: dict, uploader_key: str) -> tuple:
    """Render sidebar with model selector, sessions, and controls.
    
    Returns:
        tuple: (selected_model, new_session_clicked, uploaded_file)
    """
    from backend import MODELS
    
    with st.sidebar:
        # Header
        st.markdown("""
            <div style="border-bottom: 1px solid #222; padding-bottom: 12px; margin-bottom: 12px;">
                <h1 style="font-size: 16px; margin: 0; color: #fff; font-weight: 700;">DenLab Chat</h1>
                <p style="font-size: 11px; color: #666; margin: 4px 0 0 0;">Kimi-inspired AI</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Model selection
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Model</p>', unsafe_allow_html=True)
        
        model_names = list(MODELS.keys())
        model_values = [MODELS[m]["name"] for m in model_names]
        current_idx = model_values.index(model) if model in model_values else 0
        
        choice = st.selectbox("", model_names, index=current_idx, label_visibility="collapsed")
        selected_model = MODELS[choice]["name"]
        
        # Show capabilities
        caps = MODELS[choice].get("capabilities", [])
        if caps:
            st.caption(" " + " ".join(caps))
        
        st.divider()
        
        # Agent mode
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Agent Mode</p>', unsafe_allow_html=True)
        
        agent_col1, agent_col2 = st.columns([3, 1])
        with agent_col1:
            st.markdown("""
            <div class="agent-badge" style="margin-top:4px;">
                <div class="agent-dot"></div>
                <span>Agent</span>
            </div>
            """, unsafe_allow_html=True)
        with agent_col2:
            agent_mode = st.toggle("", value=st.session_state.get("agent_mode", False), label_visibility="collapsed")
            st.session_state.agent_mode = agent_mode
        
        st.divider()
        
        # Sessions
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Sessions</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            new_name = st.text_input("", placeholder="New session...", label_visibility="collapsed", key="new_sess_input")
        with col2:
            new_clicked = st.button("+", use_container_width=True, help="Create new session")
        
        # Session list
        if sessions:
            sorted_sessions = sorted(
                sessions.items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=True
            )[:10]
            
            for sess_name, sess_data in sorted_sessions:
                c1, c2, c3 = st.columns([6, 1, 1])
                display = sess_name[:20] + "..." if len(sess_name) > 20 else sess_name
                with c1:
                    if st.button(f"{display}", use_container_width=True, key=f"sb_load_{sess_name}"):
                        st.session_state.current_session = sess_name
                        st.session_state.messages = sess_data.get("messages", [])
                        st.session_state.model = sess_data.get("model", "openai")
                        st.rerun()
                with c2:
                    if st.button("📋", key=f"sb_fork_{sess_name}", help="Fork"):
                        fork_name = f"Fork of {sess_name}"
                        sessions[fork_name] = {
                            "messages": sess_data.get("messages", []).copy(),
                            "model": sess_data.get("model", "openai"),
                            "timestamp": __import__('datetime').datetime.now().isoformat()
                        }
                        st.rerun()
                with c3:
                    if st.button("✕", key=f"sb_del_{sess_name}", help="Delete"):
                        if sess_name in sessions:
                            del sessions[sess_name]
                        st.rerun()
        
        st.divider()
        
        # Export
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Export</p>', unsafe_allow_html=True)
        
        if st.button("Export Chat", use_container_width=True):
            if "messages" in st.session_state:
                export_text = "\n\n".join([
                    f"**{m['role'].upper()}**: {m['content']}"
                    for m in st.session_state.messages if m['role'] != 'system'
                ])
                st.download_button(
                    "Download",
                    export_text,
                    f"denlab_{st.session_state.get('current_session', 'chat')}.md",
                    use_container_width=True
                )
        
        st.divider()
        st.caption(f"v4.2 · {st.session_state.get('current_session', 'main')}")
    
    return selected_model, new_clicked, None


# ============ MESSAGE COMPONENTS ============
def render_compact_actions(msg_idx: int, content: str, msg_type: str = "text"):
    """Render compact icon-only action buttons below a message."""
    cols = st.columns([1, 1, 1, 1, 1, 20])
    
    with cols[0]:
        if st.button("📋", key=f"act_copy_{msg_idx}", help="Copy"):
            st.toast("Copied!")
    
    with cols[1]:
        if st.button("🔊", key=f"act_speak_{msg_idx}", help="TTS"):
            try:
                import requests
                audio_url = f"https://gen.pollinations.ai/audio/{requests.utils.quote(content[:500])}?voice=nova"
                st.audio(audio_url, format='audio/mp3')
            except Exception as e:
                st.toast(f"Audio error: {e}")
    
    with cols[2]:
        if st.button("🔄", key=f"act_regen_{msg_idx}", help="Regenerate"):
            st.session_state.messages = st.session_state.messages[:msg_idx]
            st.rerun()
    
    with cols[3]:
        if msg_type == "text":
            st.download_button(
                label="⬇️",
                data=content,
                file_name=f"msg_{msg_idx}.md",
                mime="text/markdown",
                key=f"act_dl_{msg_idx}",
                help="Download"
            )
    
    with cols[4]:
        if st.button("👍", key=f"act_like_{msg_idx}", help="Good"):
            st.toast("Thanks!")


def render_chat_message(msg: dict, msg_idx: int = 0):
    """Render a single chat message with actions."""
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    metadata = msg.get("metadata", {})
    msg_type = metadata.get("type", "text")
    
    with st.chat_message(role):
        if msg_type == "image":
            st.image(content, use_container_width=True)
            st.caption("Generated image")
        elif msg_type == "audio":
            st.audio(content, format='audio/mp3')
        elif msg_type == "file":
            st.markdown(content)
            file_key = metadata.get("file_key")
            if file_key and file_key in st.session_state.get("uploaded_files", {}):
                with st.expander("Preview"):
                    st.code(st.session_state.uploaded_files[file_key].get("content", "")[:3000])
        else:
            st.markdown(content)
        
        # Actions for assistant messages
        if role == "assistant" and msg_idx > 0:
            render_compact_actions(msg_idx, content, msg_type)


def render_welcome():
    """Render welcome screen."""
    st.markdown("""
    <div style="text-align: center; padding: 80px 20px 40px;">
        <div style="font-size: 36px; margin-bottom: 16px;">🧪</div>
        <div style="font-size: 22px; font-weight: 700; color: #111; margin-bottom: 8px;">DenLab Chat</div>
        <div style="font-size: 13px; color: #888; margin-bottom: 40px;">Kimi-inspired AI with multi-provider fallback</div>
        <div style="font-size: 13px; color: #666; line-height: 2.2;">
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;font-weight:500;">/imagine</code> — Generate images</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;font-weight:500;">/research</code> — Deep web research</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;font-weight:500;">/code</code> — Generate & execute Python</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;font-weight:500;">/analyze</code> — Analyze uploaded files</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;font-weight:500;">/audio</code> — Text to speech</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============ AGENT PROGRESS ============
def render_agent_progress_kimi(traces: List[Any]):
    """Render Kimi-style agent progress tracker."""
    if not traces:
        return
    
    html = '<div class="agent-progress-container">'
    html += '<div style="font-size: 11px; font-weight: 600; color: #888; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;">Execution Progress</div>'
    
    for trace in traces:
        has_tools = bool(trace.tool_calls)
        all_success = has_tools and all(tc.status == "success" for tc in trace.tool_calls)
        has_error = has_tools and any(tc.status == "error" for tc in trace.tool_calls)
        
        if has_error:
            status_class = "step-error"
            icon = "✗"
        elif all_success:
            status_class = "step-success"
            icon = "✓"
        elif has_tools:
            status_class = "step-running"
            icon = "◐"
        else:
            status_class = "step-success"
            icon = "✓"
        
        thought = trace.thought[:50] + "..." if len(trace.thought) > 50 else trace.thought
        if not thought:
            thought = f"Step {trace.step}"
        
        html += f'<div class="agent-step-row">'
        html += f'<span class="step-indicator {status_class}">{icon}</span>'
        html += f'<span style="color: #555; font-size: 13px;">{thought}</span>'
        html += f'</div>'
        
        # Tool call details
        for tc in trace.tool_calls:
            tc_icon = "✓" if tc.status == "success" else "✗" if tc.status == "error" else "◐"
            tc_color = "#10a37f" if tc.status == "success" else "#ef4444" if tc.status == "error" else "#3b82f6"
            html += f'<div style="margin-left: 30px; padding: 2px 0; font-size: 11px; color: {tc_color};">'
            html += f'{tc_icon} <code style="font-size: 11px;">{tc.name}</code>'
            if tc.duration_ms:
                html += f' <span style="color: #999;">({tc.duration_ms:.0f}ms)</span>'
            html += '</div>'
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ============ IMAGE COMPONENTS ============
def render_image_with_download(msg_idx: int, img_url: str, caption: str = ""):
    """Render image with download button."""
    st.image(img_url, caption=caption or "Generated image", use_container_width=True)
    
    cols = st.columns([1, 1, 20])
    
    with cols[0]:
        try:
            import requests
            img_data = requests.get(img_url, timeout=15).content
            st.download_button(
                label="⬇️",
                data=img_data,
                file_name=f"denlab_img_{msg_idx}.png",
                mime="image/png",
                key=f"img_dl_{msg_idx}",
                help="Download"
            )
        except:
            st.button("⬇️", key=f"img_dl_fail_{msg_idx}", help="Download failed")
    
    with cols[1]:
        if st.button("🔗", key=f"img_link_{msg_idx}", help="Copy URL"):
            st.toast("URL copied!")


# ============ COPY TO CLIPBOARD ============
def copy_to_clipboard_button(text: str, key: str, label: str = "📋"):
    """Render a button that copies text to clipboard using JavaScript."""
    escaped = json.dumps(text)
    js = f"""
    <script>
    function copy_{key}() {{
        navigator.clipboard.writeText({escaped}).then(function() {{
            const btn = document.getElementById('btn_{key}');
            btn.innerHTML = '✓';
            setTimeout(() => {{ btn.innerHTML = '{label}'; }}, 2000);
        }});
    }}
    </script>
    <button id="btn_{key}" onclick="copy_{key}()" style="
        background: transparent; border: none; color: #999; 
        padding: 4px 8px; border-radius: 6px; cursor: pointer;
        font-size: 13px;
    " onmouseover="this.style.background='#f0f0f0'" onmouseout="this.style.background='transparent'">
        {label}
    </button>
    """
    st.markdown(js, unsafe_allow_html=True)


# ============ PWA INJECTION ============
def inject_pwa():
    """Inject PWA service worker and manifest references."""
    pwa_html = """
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('service-worker.js')
            .then(function(reg) { console.log('SW registered'); })
            .catch(function(err) { console.log('SW error:', err); });
    }
    </script>
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#f5f5f5">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="DenLab">
    """
    st.markdown(pwa_html, unsafe_allow_html=True)
