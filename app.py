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
    
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: transparent !important;
        padding: 16px 0 !important;
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
        color: #667eea;
    }
    
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #e0e0e0;
    }
    
    [data-testid="stSidebar"] * {
        color: #000000 !important;
    }
    
    code {
        background: #f0f2f6;
        padding: 2px 8px;
        border-radius: 6px;
        color: #000000;
    }
    
    pre {
        background: #f0f2f6;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        overflow-x: auto;
        color: #000000;
    }
    
    h1, h2, h3, h4, p, div, span, label {
        color: #000000 !important;
    }
    
    .welcome-container {
        text-align: center;
        padding: 60px 20px;
    }
    
    .welcome-title {
        font-size: 32px;
        font-weight: 600;
        color: #000000;
        margin-bottom: 16px;
    }
    
    .welcome-subtitle {
        font-size: 18px;
        color: #666666;
        margin-bottom: 40px;
    }
    
    .stFileUploader div {
        color: #000000 !important;
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

SYSTEM_PROMPT = """You are DenLab, a professional AI assistant. Be helpful, concise, and accurate."""

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "🧪 Hello! I'm DenLab. How can I help you today?"}
    ]

if "model" not in st.session_state:
    st.session_state.model = "openai"

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

def analyze_file_content(content: str, filename: str, model: str) -> str:
    prompt = f"""Analyze this file: {filename}

Content:
{content[:4000]}

Provide a brief summary of what this file does."""
    
    messages = [
        {"role": "system", "content": "You are a technical analyst. Be concise."},
        {"role": "user", "content": prompt}
    ]
    return chat_api(messages, model)

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
            {"role": "assistant", "content": "🧪 Hello! I'm DenLab. How can I help you today?"}
        ]
        st.rerun()
    
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        st.rerun()
    
    st.divider()
    st.caption("v1.0")

# ---------- MAIN CHAT ----------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

if len(st.session_state.messages) <= 2:
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
        st.markdown(msg["content"])

st.markdown('</div>', unsafe_allow_html=True)

# ---------- INPUT AREA ----------
col1, col2 = st.columns([10, 1])

with col1:
    prompt = st.chat_input("Message DenLab... (/imagine for images)")

with col2:
    uploaded_file = st.file_uploader(
        "📎",
        type=["txt", "py", "js", "html", "css", "json", "md", "csv", "php", "java", "c", "cpp", "png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )

# ---------- HANDLE UPLOAD ----------
if uploaded_file:
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name
    
    try:
        content = file_bytes.decode('utf-8', errors='ignore')
    except:
        content = "[Binary file - preview not available]"
    
    st.session_state.messages.append({
        "role": "user",
        "content": f"📎 Uploaded: {filename}"
    })
    
    with st.chat_message("user"):
        st.markdown(f"📎 **Uploaded**: `{filename}`")
        with st.expander("Preview"):
            st.code(content[:2000], language=Path(filename).suffix[1:] or "text")
    
    with st.chat_message("assistant"):
        with st.spinner(f"Analyzing {filename}..."):
            analysis = analyze_file_content(content, filename, st.session_state.model)
        st.markdown(analysis)
    
    st.session_state.messages.append({"role": "assistant", "content": analysis})
    st.rerun()

# ---------- HANDLE CHAT ----------
if prompt:
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
                response = chat_api(api_messages, st.session_state.model)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()
