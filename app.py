import streamlit as st
from backend import chat_api, generate_image, analyze_file, MODELS, SYSTEM_PROMPT, analyze_image_description
import uuid
import base64
from pathlib import Path
import time

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="DenLab", page_icon="🧪", layout="wide")

# ---------- LIGHT THEME CSS (Refined) ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    * { font-family: 'Inter', sans-serif; }
    
    .stApp { background-color: #ffffff; }
    
    .main > div {
        max-width: 850px;
        margin: 0 auto;
        padding: 20px 20px 120px 20px;
    }
    
    .stChatMessage { background: transparent !important; padding: 16px 0 !important; }
    
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: #f0f2f6 !important;
        border-radius: 14px !important;
        padding: 14px 18px !important;
        margin: 12px 0 !important;
        color: #000000 !important;
        font-size: 15px !important;
    }
    
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: transparent !important;
        padding: 14px 0 !important;
        color: #000000 !important;
        font-size: 15px !important;
    }
    
    .stChatInput {
        position: fixed !important;
        bottom: 20px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 40px) !important;
        max-width: 810px !important;
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 24px !important;
        padding: 6px 14px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08) !important;
        z-index: 100 !important;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        border: none !important;
        color: #000000 !important;
        font-size: 15px !important;
        padding: 10px 45px 10px 14px !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #e0e0e0;
    }
    
    [data-testid="stSidebar"] * { color: #000000 !important; font-size: 14px !important; }
    
    .stButton button {
        background: #ffffff;
        color: #000000;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        background: #f0f2f6;
        border-color: #667eea;
    }
    
    h1 { font-size: 26px !important; }
    h2 { font-size: 20px !important; }
    h3 { font-size: 16px !important; }
    h1, h2, h3, h4, p, span, div { color: #000000 !important; }
    
    .image-container {
        background: #f8f9fa;
        border-radius: 14px;
        padding: 16px;
        margin: 14px 0;
        text-align: center;
    }
    
    /* Code blocks */
    pre {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        overflow-x: auto;
        font-size: 13px;
    }
    
    code {
        background: #f0f2f6;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "🧪 **DenLab ready.**\n\n• `/imagine [description]` – Generate images\n• Upload files – Analyze code\n• Ask me anything"}
    ]

if "model" not in st.session_state:
    st.session_state.model = "openai"

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())

if "pending_upload" not in st.session_state:
    st.session_state.pending_upload = None

if "processing_upload" not in st.session_state:
    st.session_state.processing_upload = False

if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {}

if "current_session_name" not in st.session_state:
    st.session_state.current_session_name = "Main"

# Save current session
if st.session_state.messages:
    st.session_state.all_sessions[st.session_state.current_session_name] = {
        "messages": st.session_state.messages.copy(),
        "model": st.session_state.model,
        "timestamp": time.time()
    }

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🧪 DenLab")
    
    st.subheader("🤖 Model")
    model_names = list(MODELS.keys())
    current_idx = list(MODELS.values()).index(st.session_state.model) if st.session_state.model in MODELS.values() else 0
    model_choice = st.selectbox("Select model", model_names, index=current_idx, label_visibility="collapsed")
    st.session_state.model = MODELS[model_choice]
    
    st.divider()
    
    # Session Management
    st.subheader("💬 Sessions")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_session_name = st.text_input("New session", placeholder="Name (optional)", label_visibility="collapsed")
    with col2:
        if st.button("➕", use_container_width=True, help="Create new session"):
            name = new_session_name if new_session_name else f"Session {len(st.session_state.all_sessions) + 1}"
            st.session_state.current_session_name = name
            st.session_state.messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "assistant", "content": "🧪 **New session.** How can I help?"}
            ]
            st.session_state.all_sessions[name] = {
                "messages": st.session_state.messages.copy(),
                "model": st.session_state.model,
                "timestamp": time.time()
            }
            st.rerun()
    
    # List saved sessions
    if st.session_state.all_sessions:
        for sess_name, sess_data in sorted(st.session_state.all_sessions.items(), key=lambda x: x[1].get("timestamp", 0), reverse=True)[:10]:
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(f"📁 {sess_name[:20]}", use_container_width=True, key=f"load_{sess_name}", help=f"Load {sess_name}"):
                    st.session_state.current_session_name = sess_name
                    st.session_state.messages = sess_data["messages"].copy()
                    st.session_state.model = sess_data.get("model", "openai")
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{sess_name}", help="Delete"):
                    del st.session_state.all_sessions[sess_name]
                    if st.session_state.current_session_name == sess_name:
                        st.session_state.current_session_name = "Main"
                        st.session_state.messages = [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "assistant", "content": "🧪 **DenLab ready.**"}
                        ]
                    st.rerun()
    
    st.divider()
    
    # Export
    if st.button("📥 Export Chat", use_container_width=True):
        export_text = "\n\n".join([
            f"**{m['role'].upper()}**: {m['content']}"
            for m in st.session_state.messages if m['role'] != 'system'
        ])
        st.download_button(
            "Download .md",
            export_text,
            f"denlab_{st.session_state.current_session_name}.md",
            use_container_width=True
        )
    
    st.divider()
    
    # File Upload
    st.subheader("📎 File Upload")
    uploaded_file = st.file_uploader(
        "Upload for analysis",
        type=["txt", "py", "js", "html", "css", "json", "md", "csv", "php", "java", "c", "cpp", "png", "jpg", "jpeg"],
        key=f"uploader_{st.session_state.uploader_key}",
        label_visibility="collapsed"
    )
    
    st.caption(f"v2.3 · {st.session_state.current_session_name}")

# ---------- HANDLE FILE UPLOAD ----------
if uploaded_file and not st.session_state.processing_upload:
    st.session_state.pending_upload = uploaded_file
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(uuid.uuid4())
    st.rerun()

if st.session_state.pending_upload and st.session_state.processing_upload:
    file_obj = st.session_state.pending_upload
    filename = file_obj.name
    mime_type = file_obj.type if hasattr(file_obj, 'type') else ""
    
    if mime_type and mime_type.startswith("image/"):
        file_bytes = file_obj.read()
        
        st.session_state.messages.append({"role": "user", "content": f"🖼️ {filename}"})
        
        with st.chat_message("user"):
            st.markdown(f"🖼️ **{filename}**")
            st.image(file_bytes, caption=filename, use_container_width=True)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing image..."):
                analysis = analyze_image_description(f"User uploaded: {filename}", st.session_state.model)
            st.markdown(analysis)
        
        st.session_state.messages.append({"role": "assistant", "content": analysis})
    else:
        try:
            content = file_obj.read().decode('utf-8', errors='ignore')
        except:
            content = "[Could not read file]"
        
        st.session_state.messages.append({"role": "user", "content": f"📎 {filename}"})
        
        with st.chat_message("user"):
            st.markdown(f"📎 **{filename}**")
            if content != "[Could not read file]":
                with st.expander("Preview (first 1500 chars)"):
                    ext = Path(filename).suffix[1:] if Path(filename).suffix else "text"
                    st.code(content[:1500], language=ext)
        
        with st.chat_message("assistant"):
            with st.spinner(f"Analyzing {filename}..."):
                analysis = analyze_file(content, filename, st.session_state.model)
            st.markdown(analysis)
        
        st.session_state.messages.append({"role": "assistant", "content": analysis})
    
    st.session_state.all_sessions[st.session_state.current_session_name] = {
        "messages": st.session_state.messages.copy(),
        "model": st.session_state.model,
        "timestamp": time.time()
    }
    
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# ---------- MAIN CHAT ----------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        if msg["content"].startswith("![Generated]"):
            img_url = msg["content"].split("](")[1].rstrip(")")
            st.markdown('<div class="image-container">', unsafe_allow_html=True)
            st.image(img_url, use_container_width=True)
            st.caption("🎨 Generated image")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

st.markdown('</div>', unsafe_allow_html=True)

# ---------- CHAT INPUT ----------
if prompt := st.chat_input("Message DenLab... (/imagine for images)"):
    
    if prompt.lower().startswith("/imagine"):
        image_desc = prompt[8:].strip()
        if image_desc:
            st.session_state.messages.append({"role": "user", "content": f"🎨 {prompt}"})
            
            with st.chat_message("user"):
                st.markdown(f"🎨 {prompt}")
            
            with st.chat_message("assistant"):
                with st.spinner("Creating image..."):
                    img_url = generate_image(image_desc)
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    st.image(img_url, caption=image_desc, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    response = f"![Generated]({img_url})"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                api_messages = [m for m in st.session_state.messages if m["role"] != "system"]
                api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                response = chat_api(api_messages, st.session_state.model)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.session_state.all_sessions[st.session_state.current_session_name] = {
        "messages": st.session_state.messages.copy(),
        "model": st.session_state.model,
        "timestamp": time.time()
    }
    
    st.rerun()
