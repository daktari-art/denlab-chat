"""UI Components for DenLab v4.0 - Kimi-inspired design system.
Provides reusable components for chat interface, sidebar, and agent displays.
"""
import streamlit as st
import base64
import json
from typing import Optional, Dict, Any, List, Callable

# ============ CSS THEME ============
def apply_kimi_theme():
    """Apply Kimi-inspired dark theme with high contrast."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        
        /* Main background - near black */
        .stApp { background-color: #0d0d0d !important; }
        
        /* Content area */
        .main > div {
            max-width: 800px;
            margin: 0 auto;
            padding: 0 20px 160px 20px;
        }
        
        /* Sidebar - dark and clean */
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #222222 !important;
            min-width: 280px !important;
            max-width: 280px !important;
        }
        
        /* Chat messages */
        .stChatMessage {
            background-color: transparent !important;
            padding: 6px 0 !important;
            margin: 2px 0 !important;
            border: none !important;
        }
        
        [data-testid="stChatMessage"] {
            background: transparent !important;
            border: none !important;
        }
        
        [data-testid="stChatMessageContent"] {
            color: #e8e8e8 !important;
            font-size: 15px !important;
            line-height: 1.7 !important;
        }
        
        /* User message bubble */
        [data-testid="stChatMessage"][data-testid*="user"] {
            background: #1a1a1a !important;
            border-radius: 16px !important;
            padding: 16px 20px !important;
            margin: 8px 0 !important;
        }
        
        /* Chat input - high contrast */
        .stChatInput {
            position: fixed !important;
            bottom: 30px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: calc(100% - 360px) !important;
            max-width: 760px !important;
            background: #1a1a1a !important;
            border: 1px solid #333333 !important;
            border-radius: 24px !important;
            padding: 4px 8px !important;
            box-shadow: 0 4px 24px rgba(0,0,0,0.6) !important;
            z-index: 1000 !important;
        }
        
        .stChatInput:focus-within {
            border-color: #4a9eff !important;
            box-shadow: 0 4px 24px rgba(74, 158, 255, 0.15) !important;
        }
        
        .stChatInput textarea {
            background: transparent !important;
            border: none !important;
            color: #ffffff !important;
            font-size: 15px !important;
            padding: 12px 60px 12px 16px !important;
        }
        
        .stChatInput textarea::placeholder {
            color: #888888 !important;
            font-size: 15px !important;
        }
        
        /* Buttons */
        .stButton button {
            background: transparent !important;
            color: #999999 !important;
            border: 1px solid #2a2a2a !important;
            border-radius: 8px !important;
            padding: 6px 12px !important;
            font-size: 13px !important;
            transition: all 0.2s ease !important;
        }
        
        .stButton button:hover {
            background: #222222 !important;
            border-color: #4a9eff !important;
            color: #4a9eff !important;
        }
        
        /* Compact action buttons */
        .action-btn button {
            background: transparent !important;
            border: none !important;
            color: #666666 !important;
            padding: 4px 6px !important;
            font-size: 14px !important;
            min-height: 28px !important;
            width: 28px !important;
            border-radius: 6px !important;
        }
        
        .action-btn button:hover {
            background: #222222 !important;
            color: #e0e0e0 !important;
        }
        
        /* Code blocks */
        pre {
            background: #161616 !important;
            border: 1px solid #2a2a2a !important;
            border-radius: 12px !important;
            padding: 16px !important;
        }
        
        code {
            background: #1a1a1a !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            color: #e8e8e8 !important;
            font-family: 'SF Mono', 'Fira Code', monospace !important;
            font-size: 13px !important;
        }
        
        /* Typography */
        h1, h2, h3, h4, h5, h6 { color: #ffffff !important; font-weight: 600 !important; }
        p { color: #d0d0d0 !important; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
        
        /* Status and spinner */
        .stSpinner > div { border-color: #4a9eff !important; }
        
        /* Expander */
        .stExpander {
            border: 1px solid #222 !important;
            border-radius: 8px !important;
            background: #161616 !important;
        }
        
        /* Download button */
        .stDownloadButton button {
            background: #1f6feb !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 6px 14px !important;
            font-size: 13px !important;
        }
        
        /* Dividers */
        hr { border-color: #222222 !important; margin: 12px 0 !important; }
        
        /* Caption */
        .stCaption { color: #666666 !important; font-size: 11px !important; }
        
        /* Agent progress */
        .agent-progress-container {
            background: #161616;
            border: 1px solid #2a2a2a;
            border-radius: 12px;
            padding: 16px;
            margin: 12px 0;
        }
        
        .agent-step-row {
            display: flex;
            align-items: center;
            padding: 6px 0;
            border-bottom: 1px solid #1a1a1a;
        }
        
        .agent-step-row:last-child { border-bottom: none; }
        
        .step-indicator {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            margin-right: 10px;
            flex-shrink: 0;
        }
        
        .step-pending { background: #2a2a2a; color: #666; }
        .step-running { background: #1a3a5c; color: #4a9eff; }
        .step-success { background: #1a3a1a; color: #3fb950; }
        .step-error { background: #3a1a1a; color: #f85149; }
    </style>
    """, unsafe_allow_html=True)


# ============ SIDEBAR COMPONENT ============
def render_sidebar(model: str, sessions: dict, uploader_key: str) -> tuple:
    """Render sidebar with model selector, sessions, and file uploader.
    
    Returns:
        tuple: (selected_model, new_session_clicked, uploaded_file)
    """
    from backend import MODELS
    
    with st.sidebar:
        # Header
        st.markdown("""
            <div style="border-bottom: 1px solid #222; padding-bottom: 12px; margin-bottom: 12px;">
                <h1 style="font-size: 18px; margin: 0; color: #fff; font-weight: 700;">🧪 DenLab</h1>
                <p style="font-size: 11px; color: #666; margin: 4px 0 0 0;">v4.0 · Agentic AI</p>
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
            st.caption(" · ".join(caps))
        
        st.divider()
        
        # Execution mode - STATIC switches (not in scrollable container)
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Execution Mode</p>', unsafe_allow_html=True)
        
        agent_mode = st.toggle("🤖 Agent Mode", value=st.session_state.get("agent_mode", False))
        st.session_state.agent_mode = agent_mode
        
        swarm_mode = False
        if agent_mode:
            swarm_mode = st.toggle("🐝 Swarm Mode", value=st.session_state.get("swarm_mode", False))
            st.session_state.swarm_mode = swarm_mode
            st.caption("Tools: search, research, code, fetch, file")
        
        st.divider()
        
        # Sessions
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Sessions</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            new_name = st.text_input("", placeholder="New session...", label_visibility="collapsed", key="new_sess_input")
        with col2:
            new_clicked = st.button("➕", use_container_width=True, help="Create new session")
        
        # Session list
        if sessions:
            sorted_sessions = sorted(
                sessions.items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=True
            )[:10]
            
            for sess_name, sess_data in sorted_sessions:
                c1, c2, c3 = st.columns([6, 1, 1])
                display = sess_name[:18] + "..." if len(sess_name) > 18 else sess_name
                with c1:
                    if st.button(f"📁 {display}", use_container_width=True, key=f"sb_load_{sess_name}"):
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
                    if st.button("🗑️", key=f"sb_del_{sess_name}", help="Delete"):
                        if sess_name in sessions:
                            del sessions[sess_name]
                        st.rerun()
        
        st.divider()
        
        # Export
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Export</p>', unsafe_allow_html=True)
        
        if st.button("📥 Export Chat", use_container_width=True):
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
        
        # Upload
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Upload</p>', unsafe_allow_html=True)
        
        uploaded = st.file_uploader(
            "",
            type=["txt", "py", "js", "ts", "jsx", "tsx", "html", "css", "json", "md",
                  "csv", "xml", "yaml", "yml", "sh", "bash", "c", "cpp", "h", "hpp",
                  "java", "kt", "swift", "rs", "go", "rb", "php", "sql",
                  "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"],
            accept_multiple_files=False,
            label_visibility="collapsed",
            key=f"sb_uploader_{uploader_key}"
        )
        
        st.divider()
        st.caption(f"v4.0 · {st.session_state.get('current_session', 'main')}")
    
    return selected_model, new_clicked, uploaded


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
            st.caption("🎨 Generated image")
        elif msg_type == "audio":
            st.audio(content, format='audio/mp3')
        elif msg_type == "file":
            st.markdown(content)
            file_key = metadata.get("file_key")
            if file_key and file_key in st.session_state.get("uploaded_files", {}):
                with st.expander("📄 Preview"):
                    st.code(st.session_state.uploaded_files[file_key].get("content", "")[:3000])
        else:
            st.markdown(content)
        
        # Actions for assistant messages
        if role == "assistant" and msg_idx > 0:
            render_compact_actions(msg_idx, content, msg_type)


def render_welcome():
    """Render welcome screen."""
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 32px; margin-bottom: 12px;">🧪</div>
        <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">DenLab v4.0</div>
        <div style="font-size: 14px; color: #888; margin-bottom: 32px;">Beyond Conversational AI</div>
        <div style="font-size: 13px; color: #666; line-height: 2;">
            <div>/imagine [prompt] — Generate images</div>
            <div>/research [topic] — Deep web research</div>
            <div>/code [task] — Generate & execute Python</div>
            <div>/analyze — Analyze uploaded files</div>
            <div>/audio [text] — Text to speech</div>
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
        # Determine step status
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
        html += f'<span style="color: #ccc; font-size: 13px;">{thought}</span>'
        html += f'</div>'
        
        # Tool call details
        for tc in trace.tool_calls:
            tc_icon = "✓" if tc.status == "success" else "✗" if tc.status == "error" else "◐"
            tc_color = "#3fb950" if tc.status == "success" else "#f85149" if tc.status == "error" else "#4a9eff"
            html += f'<div style="margin-left: 30px; padding: 2px 0; font-size: 11px; color: {tc_color};">'
            html += f'{tc_icon} <code style="font-size: 11px;">{tc.name}</code>'
            if tc.duration_ms:
                html += f' <span style="color: #666;">({tc.duration_ms:.0f}ms)</span>'
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
        background: transparent; border: none; color: #666; 
        padding: 4px 8px; border-radius: 6px; cursor: pointer;
        font-size: 14px;
    " onmouseover="this.style.background='#222'" onmouseout="this.style.background='transparent'">
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
    <meta name="theme-color" content="#0d0d0d">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="DenLab">
    """
    st.markdown(pwa_html, unsafe_allow_html=True)
