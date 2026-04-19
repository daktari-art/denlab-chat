import streamlit as st
import requests
import json
import base64
import time
from typing import List, Dict, Optional
import os

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="DenLab Chat",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- CUSTOM CSS (DeepSeek Style) ----------
st.markdown("""
<style>
    .stApp {
        background-color: #0f1117;
    }
    .stChatMessage {
        background-color: transparent !important;
    }
    [data-testid="stChatMessage"] {
        background-color: #1a1d24;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
    }
    .stChatInput textarea {
        background-color: #1a1d24;
        border: 1px solid #2d3340;
        border-radius: 12px;
        color: #e8edf5;
    }
    .stButton button {
        background-color: #2d3340;
        color: #e8edf5;
        border: none;
        border-radius: 8px;
    }
    .stButton button:hover {
        background-color: #3d4455;
    }
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #e8edf5;
    }
    [data-testid="stSidebar"] {
        background-color: #0f1117;
        border-right: 1px solid #2d3340;
    }
    [data-testid="stSidebar"] * {
        color: #e8edf5 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- API CONFIG (Backend - Hidden) ----------
TEXT_API = "https://text.pollinations.ai/openai"
IMAGE_API = "https://image.pollinations.ai/prompt"
HEADERS = {"Content-Type": "application/json"}

MODELS = {
    "GPT-4o-mini (Fast)": "openai",
    "GPT-4o (Large)": "openai-large",
    "Llama 3.3 70B": "llama",
    "DeepSeek-V3": "deepseek",
    "Gemini 2.0 Flash": "gemini",
    "Qwen Coder 32B": "qwen-coder",
    "Claude 3.5 Haiku": "claude-haiku",
}

DEFAULT_SYSTEM = """You are DenLab Assistant, a professional AI research and development assistant. 
You specialize in code debugging, technical explanations, file analysis, and research assistance.
Be concise, accurate, and helpful. Use a professional but friendly tone."""

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": DEFAULT_SYSTEM},
        {"role": "assistant", "content": "🧪 DenLab Chat ready. How can I assist your research today?"}
    ]

if "conversations" not in st.session_state:
    st.session_state.conversations = {"Default": st.session_state.messages.copy()}

if "current_conv" not in st.session_state:
    st.session_state.current_conv = "Default"

if "selected_model" not in st.session_state:
    st.session_state.selected_model = "openai"

if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# ---------- API FUNCTIONS ----------
def get_ai_response(messages: List[Dict], model: str) -> str:
    payload = {"model": model, "messages": messages, "stream": False, "temperature": 0.7}
    try:
        response = requests.post(TEXT_API, headers=HEADERS, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Error: {e}"

def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> str:
    encoded = requests.utils.quote(prompt)
    return f"{IMAGE_API}/{encoded}?width={width}&height={height}&nologo=true"

def analyze_file_content(content: str, filename: str) -> str:
    analysis_prompt = f"""Analyze this file: {filename}
Content:
{content[:3000]}

Provide:
1. File type and purpose
2. Key insights or summary
3. Any issues or suggestions
"""
    messages = [
        {"role": "system", "content": "You are a file analysis expert. Be concise and technical."},
        {"role": "user", "content": analysis_prompt}
    ]
    return get_ai_response(messages, st.session_state.selected_model)

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🧪 DenLab")
    st.caption("AI Research Assistant")
    
    st.subheader("🤖 Model")
    model_display = st.selectbox("Select AI Model", options=list(MODELS.keys()), label_visibility="collapsed")
    st.session_state.selected_model = MODELS[model_display]
    
    if st.button("➕ New Session", use_container_width=True):
        new_conv = f"Session {len(st.session_state.conversations) + 1}"
        st.session_state.conversations[new_conv] = [
            {"role": "system", "content": DEFAULT_SYSTEM},
            {"role": "assistant", "content": "🧪 DenLab Chat ready. How can I assist your research today?"}
        ]
        st.session_state.current_conv = new_conv
        st.session_state.messages = st.session_state.conversations[new_conv].copy()
        st.rerun()
    
    st.divider()
    
    st.subheader("📎 File Analysis")
    uploaded_file = st.file_uploader("Upload for analysis", type=["txt", "py", "js", "html", "css", "json", "md"], label_visibility="collapsed")
    if uploaded_file:
        try:
            content = uploaded_file.read().decode('utf-8', errors='ignore')
            analysis = analyze_file_content(content, uploaded_file.name)
            st.session_state.messages.append({"role": "user", "content": f"[Uploaded: {uploaded_file.name}]"})
            st.session_state.messages.append({"role": "assistant", "content": analysis})
            st.rerun()
        except Exception as e:
            st.error(f"Could not read file: {e}")
    
    st.divider()
    
    st.subheader("🎨 Image Generation")
    image_prompt = st.text_area("Image prompt", placeholder="Describe the image...", label_visibility="collapsed")
    img_col1, img_col2 = st.columns(2)
    with img_col1:
        width = st.selectbox("Width", [512, 768, 1024], index=2)
    with img_col2:
        height = st.selectbox("Height", [512, 768, 1024], index=2)
    
    if st.button("🎨 Generate", use_container_width=True):
        if image_prompt:
            with st.spinner("Generating..."):
                img_url = generate_image(image_prompt, width, height)
                st.session_state.generated_images.append({"prompt": image_prompt, "url": img_url})
                st.session_state.messages.append({"role": "user", "content": f"🎨 /imagine {image_prompt}"})
                st.session_state.messages.append({"role": "assistant", "content": f"![Generated]({img_url})"})
                st.rerun()
        else:
            st.warning("Enter a prompt")
    
    if st.session_state.generated_images:
        st.caption("Recent:")
        for img in st.session_state.generated_images[-2:]:
            st.image(img["url"], caption=img["prompt"][:40] + "...", use_container_width=True)
    
    st.divider()
    
    st.subheader("📚 Sessions")
    for conv_name in st.session_state.conversations:
        if st.button(conv_name, use_container_width=True):
            st.session_state.current_conv = conv_name
            st.session_state.messages = st.session_state.conversations[conv_name].copy()
            st.rerun()
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Export", use_container_width=True):
            chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
            st.download_button("Download", chat_text, "denlab_chat.txt", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.conversations = {"Default": [
                {"role": "system", "content": DEFAULT_SYSTEM},
                {"role": "assistant", "content": "🧪 DenLab Chat ready. How can I assist your research today?"}
            ]}
            st.session_state.current_conv = "Default"
            st.session_state.messages = st.session_state.conversations["Default"].copy()
            st.rerun()

# ---------- MAIN CHAT ----------
st.title("🧪 DenLab Chat")
st.caption("AI Research & Development Assistant")

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Message DenLab Assistant..."):
    if prompt.lower().startswith("/imagine"):
        image_desc = prompt[8:].strip()
        if image_desc:
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                with st.spinner("🎨 Generating..."):
                    img_url = generate_image(image_desc)
                    st.markdown(f"![Generated]({img_url})")
                    st.session_state.generated_images.append({"prompt": image_desc, "url": img_url})
                    response = f"Generated: {img_url}"
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            st.warning("Provide an image description after /imagine")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                api_messages = [m for m in st.session_state.messages if m["role"] != "system"]
                api_messages.insert(0, {"role": "system", "content": DEFAULT_SYSTEM})
                response = get_ai_response(api_messages, st.session_state.selected_model)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.session_state.conversations[st.session_state.current_conv] = st.session_state.messages.copy()
    st.rerun()

st.divider()
st.caption("🧪 DenLab · AI Research Assistant")
