import streamlit as st
from backend import chat_api, generate_image, analyze_file, MODELS, SYSTEM_PROMPT, analyze_image_description
import uuid
import base64
from pathlib import Path
import time
import json

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="DenLab", page_icon="🧪", layout="wide")

# ---------- FIXED SIDEBAR + COPY CODE CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap');
    * { font-family: 'Inter', sans-serif; }
    
    .stApp { background-color: #ffffff; }
    
    /* Fixed Sidebar */
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #e0e0e0;
        position: fixed !important;
        height: 100vh !important;
        overflow-y: auto !important;
    }
    
    [data-testid="stSidebar"] * { color: #000000 !important; font-size: 13px !important; }
    
    /* Main content */
    .main > div {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px 20px 100px 20px;
    }
    
    /* Chat messages - smaller font */
    .stChatMessage { background: transparent !important; padding: 12px 0 !important; }
    
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: #f0f2f6 !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        margin: 10px 0 !important;
        color: #000000 !important;
        font-size: 14px !important;
    }
    
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: transparent !important;
        padding: 12px 0 !important;
        color: #000000 !important;
        font-size: 14px !important;
    }
    
    /* Chat input */
    .stChatInput {
        position: fixed !important;
        bottom: 20px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 40px) !important;
        max-width: 780px !important;
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 20px !important;
        padding: 4px 12px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        z-index: 100 !important;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        border: none !important;
        color: #000000 !important;
        font-size: 14px !important;
        padding: 10px 40px 10px 12px !important;
    }
    
    /* Buttons */
    .stButton button {
        background: #ffffff;
        color: #000000;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: 500;
    }
    
    .stButton button:hover {
        background: #f0f2f6;
        border-color: #667eea;
    }
    
    /* Headers */
    h1 { font-size: 24px !important; }
    h2 { font-size: 18px !important; }
    h3 { font-size: 15px !important; }
    h1, h2, h3, h4, p, span, div { color: #000000 !important; }
    
    /* Code blocks with copy button container */
    .code-block-wrapper {
        position: relative;
        margin: 12px 0;
    }
    
    .copy-btn {
        position: absolute;
        top: 8px;
        right: 8px;
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
        cursor: pointer;
        opacity: 0.7;
        transition: opacity 0.2s;
    }
    
    .copy-btn:hover {
        opacity: 1;
        background: #f0f2f6;
    }
    
    pre {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        padding-top: 32px;
        overflow-x: auto;
        font-size: 13px;
        position: relative;
    }
    
    code {
        background: #f0f2f6;
        padding: 2px 4px;
        border-radius: 4px;
        font-size: 13px;
    }
    
    .image-container {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 14px;
        margin: 12px 0;
        text-align: center;
    }
</style>

<!-- Copy Code Script -->
<script>
function copyCode(btn) {
    const pre = btn.parentElement.querySelector('pre');
    const code = pre ? pre.innerText : '';
    navigator.clipboard.writeText(code).then(() => {
        btn.innerText = '✓ Copied';
        setTimeout(() => btn.innerText = '📋 Copy', 2000);
    });
}
</script>
""", unsafe_allow_html=True)

# ---------- SESSION STATE WITH LOCALSTORAGE PERSISTENCE ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "🧪 **DenLab ready.**\n\n• `/imagine [description]` – Generate images\n• Upload files – Analyze code\n• Shift+Enter for new line"}
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

# ---------- SIDEBAR (Fixed/Static) ----------
with st.sidebar:
    st.title("🧪 DenLab")
    
    st.subheader("🤖 Model")
    model_names = list(MODELS.keys())
    current_idx = list(MODELS.keys()).index(st.session_state.model) if st.session_state.model in MODELS else 0
    model_choice = st.selectbox("Select model", model_names, index=current_idx, label_visibility="collapsed")
    st.session_state.model = MODELS[model_choice] if isinstance(MODELS[model_choice], str) else MODELS[model_choice]["name"]
    
    st.caption(f"✓ {model_choice} ready")
    
    st.divider()
    
    # Sessions
    st.subheader("💬 Sessions")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_name = st.text_input("New", placeholder="Name", label_visibility="collapsed")
    with col2:
        if st.button("➕", use_container_width=True):
            name = new_name if new_name else f"S{len(st.session_state.all_sessions)+1}"
            st.session_state.current_session_name = name
            st.session_state.messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "assistant", "content": "🧪 **New session.**"}
            ]
            st.session_state.all_sessions[name] = {
                "messages": st.session_state.messages.copy(),
                "model": st.session_state.model,
                "timestamp": time.time()
            }
            st.rerun()
    
    if st.session_state.all_sessions:
        for sess_name, sess_data in sorted(st.session_state.all_sessions.items(), key=lambda x: x[1].get("timestamp", 0), reverse=True)[:8]:
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(f"📁 {sess_name[:18]}", use_container_width=True, key=f"load_{sess_name}"):
                    st.session_state.current_session_name = sess_name
                    st.session_state.messages = sess_data["messages"].copy()
                    st.session_state.model = sess_data.get("model", "openai")
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{sess_name}"):
                    del st.session_state.all_sessions[sess_name]
                    st.rerun()
    
    st.divider()
    
    # Export
    if st.button("📥 Export", use_container_width=True):
        export_text = "\n\n".join([f"**{m['role'].upper()}**: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
        st.download_button("Download", export_text, f"denlab_{st.session_state.current_session_name}.md", use_container_width=True)
    
    st.divider()
    
    # File Upload
    st.subheader("📎 Upload")
    uploaded_file = st.file_uploader(
        "File",
        type=["txt", "py", "js", "html", "css", "json", "md", "csv", "php", "java", "c", "cpp", "png", "jpg", "jpeg"],
        key=f"up_{st.session_state.uploader_key}",
        label_visibility="collapsed"
    )
    
    st.caption(f"v2.4 · {st.session_state.current_session_name[:12]}")

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
            with st.spinner("..."):
                analysis = analyze_image_description(filename, st.session_state.model)
            st.markdown(analysis)
        
        st.session_state.messages.append({"role": "assistant", "content": analysis})
    else:
        try:
            content = file_obj.read().decode('utf-8', errors='ignore')
        except:
            content = "[Binary]"
        
        st.session_state.messages.append({"role": "user", "content": f"📎 {filename}"})
        
        with st.chat_message("user"):
            st.markdown(f"📎 **{filename}**")
            if content != "[Binary]":
                with st.expander("Preview"):
                    ext = Path(filename).suffix[1:] or "text"
                    st.code(content[:1200], language=ext)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
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
        content = msg["content"]
        if content.startswith("![Generated]"):
            img_url = content.split("](")[1].rstrip(")")
            st.markdown('<div class="image-container">', unsafe_allow_html=True)
            st.image(img_url, use_container_width=True)
            st.caption("🎨 Generated")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            # Add copy button wrapper for code blocks
            if "```" in content:
                parts = content.split("```")
                for i, part in enumerate(parts):
                    if i % 2 == 0:
                        st.markdown(part)
                    else:
                        st.markdown(f"""
                        <div class="code-block-wrapper">
                            <button class="copy-btn" onclick="copyCode(this)">📋 Copy</button>
                            <pre><code>{part.strip()}</code></pre>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown(content)

st.markdown('</div>', unsafe_allow_html=True)

# ---------- CHAT INPUT ----------
if prompt := st.chat_input("Message (Shift+Enter for new line) | /imagine for images"):
    
    if prompt.lower().startswith("/imagine"):
        image_desc = prompt[8:].strip()
        if image_desc:
            st.session_state.messages.append({"role": "user", "content": f"🎨 {prompt}"})
            with st.chat_message("user"):
                st.markdown(f"🎨 {prompt}")
            with st.chat_message("assistant"):
                with st.spinner("Creating..."):
                    img_url = generate_image(image_desc)
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    st.image(img_url, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    response = f"![Generated]({img_url})"
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("..."):
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
