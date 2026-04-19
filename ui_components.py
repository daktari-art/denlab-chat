import streamlit as st
import base64

def apply_custom_css():
    """Apply DeepSeek-inspired dark theme."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        * { font-family: 'Inter', sans-serif; }
        
        .stApp { background-color: #0d1117; }
        
        .main > div {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px 20px 120px 20px;
        }
        
        .stChatMessage { background: transparent !important; padding: 20px 0 !important; }
        [data-testid="stChatMessage"] { background: transparent !important; }
        
        [data-testid="stChatMessage"][data-testid*="user"] {
            background: #1e242c !important;
            border-radius: 16px !important;
            padding: 16px 20px !important;
            margin: 16px 0 !important;
        }
        
        .stChatInput {
            position: fixed !important;
            bottom: 20px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: calc(100% - 40px) !important;
            max-width: 860px !important;
            background: #1e242c !important;
            border: 1px solid #30363d !important;
            border-radius: 30px !important;
            padding: 8px 16px !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
            z-index: 100 !important;
        }
        
        .stChatInput textarea {
            background: transparent !important;
            border: none !important;
            color: #e6edf3 !important;
            font-size: 16px !important;
            padding: 12px 50px 12px 16px !important;
        }
        
        .stChatInput textarea::placeholder { color: #7d8590 !important; }
        
        [data-testid="stSidebar"] {
            background-color: #0d1117;
            border-right: 1px solid #1e242c;
        }
        [data-testid="stSidebar"] * { color: #e6edf3 !important; }
        
        .stButton button {
            background: transparent;
            color: #e6edf3;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .stButton button:hover {
            background: #1e242c;
            border-color: #667eea;
            color: #667eea;
        }
        
        code { background: #1e242c; padding: 2px 8px; border-radius: 6px; color: #e6edf3; }
        pre {
            background: #1e242c;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            overflow-x: auto;
        }
        
        h1, h2, h3, h4, p, span, div, label { color: #e6edf3 !important; }
        
        .welcome-container { text-align: center; padding: 60px 20px; }
        .welcome-title { font-size: 32px; font-weight: 600; color: #e6edf3; margin-bottom: 16px; }
        .welcome-subtitle { font-size: 18px; color: #7d8590; margin-bottom: 40px; }
    </style>
    """, unsafe_allow_html=True)

def render_sidebar(current_model: str, sessions: dict, uploader_key: str):
    """Render sidebar with model selector, sessions, and file uploader."""
    from backend import MODELS
    
    with st.sidebar:
        st.title("🧪 DenLab")
        
        st.subheader("Model")
        model_names = list(MODELS.keys())
        current_idx = list(MODELS.values()).index(current_model) if current_model in MODELS.values() else 0
        model_choice = st.selectbox(
            "Select model",
            model_names,
            index=current_idx,
            label_visibility="collapsed"
        )
        selected_model = MODELS[model_choice]
        
        st.divider()
        st.subheader("Sessions")
        
        new_session = st.button("➕ New Session", use_container_width=True)
        
        for sess in list(sessions.keys()):
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(sess, use_container_width=True, key=f"btn_{sess}"):
                    st.session_state[f"switch_to_{sess}"] = True
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{sess}"):
                    st.session_state[f"delete_{sess}"] = True
                    st.rerun()
        
        st.divider()
        
        if st.button("📥 Export Session", use_container_width=True):
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
        
        uploaded_file = st.file_uploader(
            "📎 Upload file",
            type=[
                "txt", "py", "js", "ts", "jsx", "tsx", "html", "css", "json", "md",
                "csv", "xml", "yaml", "yml", "sh", "bash", "c", "cpp", "h", "hpp",
                "java", "kt", "swift", "rs", "go", "rb", "php", "sql",
                "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"
            ],
            accept_multiple_files=False,
            label_visibility="collapsed",
            key=f"uploader_{uploader_key}"
        )
        
        st.caption("v2.0 · Advanced")
        
    return selected_model, new_session, uploaded_file

def render_chat_message(msg: dict):
    """Render a single chat message."""
    with st.chat_message(msg["role"]):
        content = msg["content"]
        
        if content.startswith("![Generated]"):
            img_url = content.split("](")[1].rstrip(")")
            st.image(img_url, use_container_width=True)
            st.caption("🎨 Generated image")
        elif content.startswith("[FILE_UPLOAD]"):
            parts = content.split("|")
            filename = parts[1] if len(parts) > 1 else "unknown"
            st.markdown(f"📎 **Uploaded**: `{filename}`")
        elif content.startswith("[IMAGE_UPLOAD]"):
            parts = content.split("|")
            filename = parts[1] if len(parts) > 1 else "unknown"
            if len(parts) > 2:
                st.image(base64.b64decode(parts[2]), caption=filename, use_container_width=True)
            st.markdown(f"🖼️ **Uploaded**: `{filename}`")
        else:
            st.markdown(content)

def render_welcome():
    """Render welcome screen."""
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-title">🧪 DenLab</div>
        <div class="welcome-subtitle">AI Research Assistant</div>
    </div>
    """, unsafe_allow_html=True)
