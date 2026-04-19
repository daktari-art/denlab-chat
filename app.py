import streamlit as st
import requests
import json
import base64
from typing import List, Dict
from pathlib import Path
import mimetypes

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="DenLab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="auto"
)

# ---------- CLEAN LIGHT THEME CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #ffffff;
    }
    
    .main > div {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .stChatMessage {
        background: transparent !important;
        padding: 16px 0 !important;
    }
    
    [data-testid="stChatMessage"] {
        background: transparent !important;
    }
    
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: #f0f2f6 !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin: 16px 0 !important;
    }
    
    .stChatInput textarea {
        border: 1px solid #e0e0e0 !important;
        border-radius: 24px !important;
        padding: 12px 16px !important;
        color: #000000 !important;
        background: #ffffff !important;
    }
    
    .chat-container {
        margin-bottom: 100px;
    }
    
    .stButton button {
        background: #ffffff;
        color: #000000;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }
    
    .stButton button:hover {
        background: #f0f2f6;
        border-color: #667eea;
    }
    
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #e0e0e0;
    }
    
    [data-testid="stSidebar"] * {
        color: #000000 !important;
    }
    
    h1, h2, h3, h4, p, div, span, label {
        color: #000000 !important;
    }
    
    .file-attachment {
        background: #f0f2f6;
        border-radius: 12px;
        padding: 8px 16px;
        margin: 8px 0;
        display: inline-block;
        font-size: 14px;
    }
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
}

SYSTEM_PROMPT = """You are DenLab, a professional AI assistant. You can analyze files when asked.
When the user uploads a file, they will tell you what they want you to do with it.
Be helpful, concise, and accurate."""

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "🧪 Hello! I'm DenLab. Upload a file or ask me anything."}
    ]

if "model" not in st.session_state:
    st.session_state.model = "openai"

if "attached_file" not in st.session_state:
    st.session_state.attached_file = None

if "file_content" not in st.session_state:
    st.session_state.file_content = None

# ---------- API FUNCTION ----------
def chat_api(messages: List[Dict], model: str) -> str:
    try:
        resp = requests.post(API_URL, headers=HEADERS, 
                            json={"model": model, "messages": messages, "stream": False}, 
                            timeout=60)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"Error: API returned {resp.status_code}"
    except Exception as e:
        return f"Connection error: {str(e)}"

def generate_image(prompt: str) -> str:
    encoded = requests.utils.quote(prompt)
    return f"{IMAGE_API}/{encoded}?width=1024&height=1024&nologo=true"

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🧪 DenLab")
    
    st.subheader("Model")
    model_choice = st.selectbox("Select model", list(MODELS.keys()), label_visibility="collapsed")
    st.session_state.model = MODELS[model_choice]
    
    st.divider()
    
    if st.button("🔄 New Chat", use_container_width=True):
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "🧪 Hello! I'm DenLab. Upload a file or ask me anything."}
        ]
        st.session_state.attached_file = None
        st.session_state.file_content = None
        st.rerun()
    
    # Show attached file
    if st.session_state.attached_file:
        st.divider()
        st.subheader("📎 Attached")
        st.info(f"**{st.session_state.attached_file}**\n\nReady for analysis. Ask me about it.")
        if st.button("❌ Clear Attachment", use_container_width=True):
            st.session_state.attached_file = None
            st.session_state.file_content = None
            st.rerun()
    
    st.divider()
    st.caption("v1.0")

# ---------- MAIN CHAT ----------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.markdown('</div>', unsafe_allow_html=True)

# ---------- INPUT AREA ----------
col1, col2 = st.columns([10, 1])

with col1:
    prompt = st.chat_input("Message DenLab... (/imagine for images)")

with col2:
    uploaded_file = st.file_uploader(
        "📎",
        type=["txt", "py", "js", "html", "css", "json", "md", "csv", "php", "java", "c", "cpp", "png", "jpg", "jpeg", "pdf"],
        label_visibility="collapsed",
        key="file_uploader"
    )

# ---------- HANDLE UPLOAD (Silent - No Auto Analysis) ----------
if uploaded_file:
    try:
        content = uploaded_file.read().decode('utf-8', errors='ignore')
    except:
        content = "[Binary file - content stored]"
    
    st.session_state.attached_file = uploaded_file.name
    st.session_state.file_content = content
    
    # Add subtle system message
    st.session_state.messages.append({
        "role": "system",
        "content": f"[FILE_ATTACHED] {uploaded_file.name}"
    })
    
    st.rerun()

# ---------- HANDLE CHAT ----------
if prompt:
    # Check if there's an attached file to include
    file_context = ""
    if st.session_state.file_content and st.session_state.attached_file:
        file_context = f"\n\n[Attached file: {st.session_state.attached_file}]\nContent preview:\n{st.session_state.file_content[:3000]}"
    
    full_prompt = prompt + file_context
    
    if prompt.lower().startswith("/imagine"):
        image_desc = prompt[8:].strip()
        if image_desc:
            st.session_state.messages.append({"role": "user", "content": f"🎨 {prompt}"})
            with st.chat_message("user"):
                st.markdown(f"🎨 {prompt}")
            
            with st.chat_message("assistant"):
                with st.spinner("Creating image..."):
                    img_url = generate_image(image_desc)
                    st.image(img_url, caption=image_desc, use_container_width=True)
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
                
                # Add file context to the last user message
                if file_context:
                    api_messages[-1]["content"] = full_prompt
                
                response = chat_api(api_messages, st.session_state.model)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()
