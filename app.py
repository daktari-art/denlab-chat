import streamlit as st
import requests
import base64
import mimetypes
from pathlib import Path
from typing import List, Dict
import uuid
import time

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="DenLab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------- CUSTOM CSS (Polished Dark Theme) ----------
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
    
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: transparent !important;
        padding: 16px 0 !important;
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
    
    h1, h2, h3, h4 { color: #e6edf3 !important; font-weight: 600 !important; }
    a { color: #667eea !important; text-decoration: none !important; }
    a:hover { text-decoration: underline !important; }
    
    .welcome-container { text-align: center; padding: 60px 20px; }
    .welcome-title { font-size: 32px; font-weight: 600; color: #e6edf3; margin-bottom: 16px; }
    .welcome-subtitle { font-size: 18px; color: #7d8590; margin-bottom: 40px; }
    
    .stFileUploader > div { width: 100%; }
    .stFileUploader button { border: 1px dashed #30363d !important; }
</style>
""", unsafe_allow_html=True)

# ---------- API CONFIG ----------
API_URL = "https://text.pollinations.ai/openai"
IMAGE_API = "https://image.pollinations.ai/prompt"
HEADERS = {"Content-Type": "application/json"}

MODELS = {
    "GPT-4o mini": "openai",
    "GPT-4o": "openai-large",
    "Llama 3.3 70B": "llama",
    "DeepSeek-V3": "deepseek",
    "Gemini 2.0 Flash": "gemini",
    "Qwen Coder 32B": "qwen-coder",
}

SYSTEM_PROMPT = """You are DenLab, a professional AI research assistant. You help with code analysis, debugging, technical writing, and research. Be concise, accurate, and helpful."""

# ---------- SESSION STATE INIT ----------
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

if "model" not in st.session_state:
    st.session_state.model = "openai"

if "sessions" not in st.session_state:
    st.session_state.sessions = {}

if "current_session" not in st.session_state:
    st.session_state.current_session = "Main"

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())

if "pending_upload" not in st.session_state:
    st.session_state.pending_upload = None

if "processing_upload" not in st.session_state:
    st.session_state.processing_upload = False

# ---------- API FUNCTIONS (with retry) ----------
def chat_api(messages: List[Dict], model: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                API_URL,
                headers=HEADERS,
                json={"model": model, "messages": messages, "stream": False},
                timeout=45
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(1)
                continue
            return "⚠️ Request timed out. The file may be too large. Try a smaller portion."
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return f"⚠️ Connection error: {str(e)}"
        except KeyError:
            return "⚠️ Unexpected API response. Please try again."
    return "⚠️ Failed after multiple attempts."

def generate_image(prompt: str) -> str:
    encoded = requests.utils.quote(prompt)
    return f"{IMAGE_API}/{encoded}?width=1024&height=1024&nologo=true"

def analyze_file(content: str, filename: str, model: str) -> str:
    ext = Path(filename).suffix
    max_chars = 6000
    truncated = len(content) > max_chars
    display = content[:max_chars]
    
    prompt = f"""Analyze this file: {filename}
File type: {ext}
{f'⚠️ Truncated to {max_chars} chars' if truncated else ''}

Content:
\`\`\`
{display}
\`\`\`

Provide:
1. Purpose & structure
2. Key components
3. Potential issues
4. Summary"""
    
    messages = [
        {"role": "system", "content": "You are a code analysis expert. Be technical and precise."},
        {"role": "user", "content": prompt}
    ]
    return chat_api(messages, model)

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🧪 DenLab")
    
    st.subheader("Model")
    model_choice = st.selectbox(
        "Select model",
        list(MODELS.keys()),
        label_visibility="collapsed"
    )
    st.session_state.model = MODELS[model_choice]
    
    st.divider()
    st.subheader("Sessions")
    
    if st.button("➕ New Session", use_container_width=True):
        new_name = f"Session {len(st.session_state.sessions) + 1}"
        st.session_state.sessions[new_name] = []
        st.session_state.current_session = new_name
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()
    
    for sess in list(st.session_state.sessions.keys()):
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(sess, use_container_width=True, key=f"load_{sess}"):
                st.session_state.current_session = sess
                loaded = st.session_state.sessions.get(sess, [])
                st.session_state.messages = loaded if loaded else [{"role": "system", "content": SYSTEM_PROMPT}]
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{sess}"):
                del st.session_state.sessions[sess]
                if st.session_state.current_session == sess:
                    st.session_state.current_session = "Main"
                    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                st.rerun()
    
    st.divider()
    
    if st.button("📥 Export Session", use_container_width=True):
        export_text = "\n\n".join([
            f"**{m['role'].upper()}**: {m['content']}"
            for m in st.session_state.messages if m['role'] != 'system'
        ])
        st.download_button(
            "Download",
            export_text,
            f"denlab_{st.session_state.current_session}.md",
            use_container_width=True
        )
    
    st.divider()
    st.caption("v2.0 · Advanced")

# ---------- MAIN CHAT AREA ----------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

if len(st.session_state.messages) <= 1:
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-title">🧪 DenLab</div>
        <div class="welcome-subtitle">AI Research Assistant</div>
    </div>
    """, unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        if msg["content"].startswith("![Generated]"):
            img_url = msg["content"].split("](")[1].rstrip(")")
            st.image(img_url, use_container_width=True)
            st.caption("🎨 Generated image")
        elif msg["content"].startswith("[FILE_UPLOAD]"):
            parts = msg["content"].split("|")
            filename = parts[1]
            st.markdown(f"📎 **Uploaded**: `{filename}`")
        elif msg["content"].startswith("[IMAGE_UPLOAD]"):
            parts = msg["content"].split("|")
            filename = parts[1]
            if len(parts) > 2:
                st.image(base64.b64decode(parts[2]), caption=filename, use_container_width=True)
            st.markdown(f"🖼️ **Uploaded**: `{filename}`")
        else:
            st.markdown(msg["content"])

st.markdown('</div>', unsafe_allow_html=True)

# ---------- INPUT AREA ----------
col1, col2 = st.columns([8, 1])

with col1:
    prompt = st.chat_input("Message DenLab... (Use /imagine for images)")

with col2:
    uploaded_file = st.file_uploader(
        "📎",
        type=[
            "txt", "py", "js", "ts", "jsx", "tsx", "html", "css", "json", "md",
            "csv", "xml", "yaml", "yml", "sh", "bash", "c", "cpp", "h", "hpp",
            "java", "kt", "swift", "rs", "go", "rb", "php", "sql",
            "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"
        ],
        accept_multiple_files=False,
        label_visibility="collapsed",
        key=f"uploader_{st.session_state.uploader_key}"
    )

# ---------- HANDLE FILE UPLOAD (once per file) ----------
if uploaded_file is not None and not st.session_state.processing_upload:
    st.session_state.pending_upload = {
        "file": uploaded_file,
        "name": uploaded_file.name,
        "type": uploaded_file.type
    }
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(uuid.uuid4())
    st.rerun()

if st.session_state.pending_upload is not None and st.session_state.processing_upload:
    pending = st.session_state.pending_upload
    file_obj = pending["file"]
    filename = pending["name"]
    mime_type = pending["type"]
    
    file_bytes = file_obj.getvalue()
    
    if mime_type.startswith("image/"):
        st.session_state.messages.append({
            "role": "user",
            "content": f"[IMAGE_UPLOAD]|{filename}|{base64.b64encode(file_bytes).decode()}"
        })
        with st.chat_message("user"):
            st.image(file_bytes, caption=filename, use_container_width=True)
        
        with st.chat_message("assistant"):
            with st.spinner("📸 Processing image..."):
                size_mb = len(file_bytes) / (1024 * 1024)
                analysis = f"📸 Image received: **{filename}** ({size_mb:.2f} MB)\n\nI cannot directly see images, but you can describe it and I'll help. Or use `/imagine` to generate similar images."
            st.markdown(analysis)
        st.session_state.messages.append({"role": "assistant", "content": analysis})
    else:
        try:
            content = file_bytes.decode('utf-8', errors='ignore')
        except:
            content = "[Binary file - cannot display]"
        
        st.session_state.messages.append({
            "role": "user",
            "content": f"[FILE_UPLOAD]|{filename}"
        })
        with st.chat_message("user"):
            st.markdown(f"📎 **Uploaded**: `{filename}`")
            if content != "[Binary file - cannot display]":
                with st.expander("View file content"):
                    st.code(content[:2000], language=Path(filename).suffix[1:] or "text")
        
        with st.chat_message("assistant"):
            with st.spinner(f"📄 Analyzing {filename}..."):
                analysis = analyze_file(content, filename, st.session_state.model)
            st.markdown(analysis)
        st.session_state.messages.append({"role": "assistant", "content": analysis})
    
    st.session_state.sessions[st.session_state.current_session] = st.session_state.messages.copy()
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# ---------- HANDLE CHAT INPUT ----------
if prompt:
    if prompt.lower().startswith("/imagine"):
        image_desc = prompt[8:].strip()
        if image_desc:
            st.session_state.messages.append({"role": "user", "content": f"🎨 /imagine {image_desc}"})
            with st.chat_message("user"):
                st.markdown(f"🎨 /imagine {image_desc}")
            
            with st.chat_message("assistant"):
                with st.spinner("🎨 Creating image..."):
                    img_url = generate_image(image_desc)
                    st.image(img_url, caption=image_desc, use_container_width=True)
                    response = f"![Generated]({img_url})"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("💭 Thinking..."):
                api_messages = [m for m in st.session_state.messages if m["role"] != "system"]
                api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                response = chat_api(api_messages, st.session_state.model)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.session_state.sessions[st.session_state.current_session] = st.session_state.messages.copy()
    st.rerun()
