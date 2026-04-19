import streamlit as st
import requests
from typing import List, Dict
import time

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="DenLab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------- CLEAN CUSTOM CSS ----------
st.markdown("""
<style>
    /* Clean light theme */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Chat container */
    .main-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }
    
    /* Chat messages */
    .stChatMessage {
        background: white !important;
        border-radius: 20px !important;
        padding: 16px 20px !important;
        margin: 12px 0 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
    }
    
    [data-testid="stChatMessage"] {
        background: white !important;
    }
    
    /* User message specific */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
    }
    
    /* Chat input */
    .stChatInput {
        background: white !important;
        border-radius: 30px !important;
        padding: 12px 20px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15) !important;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        border: none !important;
        color: #333 !important;
        font-size: 16px !important;
    }
    
    .stChatInput textarea::placeholder {
        color: #999 !important;
    }
    
    /* Buttons */
    .stButton button {
        background: white !important;
        color: #667eea !important;
        border: 2px solid #667eea !important;
        border-radius: 30px !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }
    
    .stButton button:hover {
        background: #667eea !important;
        color: white !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(102,126,234,0.3) !important;
    }
    
    /* File uploader */
    .stFileUploader {
        background: white !important;
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: white !important;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2) !important;
    }
    
    /* Action bar */
    .action-bar {
        display: flex;
        gap: 10px;
        padding: 15px 0;
        flex-wrap: wrap;
    }
    
    /* Model selector */
    .stSelectbox {
        background: white !important;
        border-radius: 30px !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- API CONFIG ----------
API_URL = "https://text.pollinations.ai/openai"
IMAGE_API = "https://image.pollinations.ai/prompt"
HEADERS = {"Content-Type": "application/json"}

MODELS = {
    "🧠 GPT-4o-mini": "openai",
    "🚀 GPT-4o": "openai-large",
    "🦙 Llama 3.3 70B": "llama",
    "🔍 DeepSeek-V3": "deepseek",
    "💎 Gemini 2.0": "gemini",
    "💻 Qwen Coder": "qwen-coder",
}

SYSTEM_PROMPT = """You are DenLab Assistant, an AI research companion. 
You help with coding, debugging, file analysis, and technical questions.
Be professional, concise, and helpful. Use a friendly tone."""

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "👋 Welcome to DenLab! I'm your AI research assistant. How can I help you today?"}
    ]

if "model" not in st.session_state:
    st.session_state.model = "openai"

# ---------- API FUNCTIONS ----------
def chat(messages: List[Dict], model: str) -> str:
    try:
        resp = requests.post(API_URL, headers=HEADERS, 
                            json={"model": model, "messages": messages, "stream": False}, 
                            timeout=60)
        return resp.json()["choices"][0]["message"]["content"]
    except:
        return "⚠️ Connection error. Please try again."

def generate_image(prompt: str) -> str:
    encoded = requests.utils.quote(prompt)
    return f"{IMAGE_API}/{encoded}?width=1024&height=1024&nologo=true"

# ---------- HEADER ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.title("🧪 DenLab")
    st.caption("AI Research Assistant")

# ---------- ACTION BAR ----------
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])

with col1:
    # Model selector
    model_choice = st.selectbox("Model", list(MODELS.keys()), label_visibility="collapsed")
    st.session_state.model = MODELS[model_choice]

with col2:
    # New chat button
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "👋 Fresh session! What would you like to explore?"}
        ]
        st.rerun()

with col3:
    # Clear chat
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()

with col4:
    # Export chat
    chat_text = "\n\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
    st.download_button("💾 Export", chat_text, "denlab_chat.txt", use_container_width=True)

st.markdown("---")

# ---------- MAIN CHAT AREA ----------
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ---------- CHAT INPUT ----------
prompt = st.chat_input("Message DenLab...")

if prompt:
    # Check for image command
    if prompt.lower().startswith("/imagine"):
        image_prompt = prompt[8:].strip()
        if image_prompt:
            st.session_state.messages.append({"role": "user", "content": f"🎨 {prompt}"})
            with st.chat_message("user"):
                st.markdown(f"🎨 {prompt}")
            
            with st.chat_message("assistant"):
                with st.spinner("🎨 Creating image..."):
                    img_url = generate_image(image_prompt)
                    st.image(img_url, caption=image_prompt, use_container_width=True)
                    response = f"✨ Here's your image: {image_prompt}"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    # File upload detection (user can paste file content)
    elif prompt.startswith("[FILE]"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown("📎 File uploaded for analysis")
        
        with st.chat_message("assistant"):
            with st.spinner("📄 Analyzing file..."):
                analysis = chat([
                    {"role": "system", "content": "Analyze this file content. Provide summary and key insights."},
                    {"role": "user", "content": prompt}
                ], st.session_state.model)
            st.markdown(analysis)
        
        st.session_state.messages.append({"role": "assistant", "content": analysis})
    
    # Normal chat
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("💭 Thinking..."):
                response = chat([m for m in st.session_state.messages if m["role"] != "system"], st.session_state.model)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()

# ---------- SIDEBAR (Additional Tools) ----------
with st.sidebar:
    st.header("🛠️ Tools")
    
    # Image Generation
    with st.expander("🎨 Image Generator", expanded=False):
        img_prompt = st.text_input("Description", placeholder="A futuristic city...")
        if st.button("Generate Image", use_container_width=True):
            if img_prompt:
                with st.spinner("Creating..."):
                    st.image(generate_image(img_prompt), caption=img_prompt, use_container_width=True)
    
    # File Upload
    with st.expander("📎 File Analysis", expanded=False):
        uploaded = st.file_uploader("Upload file", type=["txt", "py", "js", "json", "md", "csv"])
        if uploaded:
            content = uploaded.read().decode('utf-8', errors='ignore')
            if st.button("Analyze File", use_container_width=True):
                analysis = chat([
                    {"role": "system", "content": "Analyze this file. Be concise."},
                    {"role": "user", "content": f"File: {uploaded.name}\n\n{content[:2000]}"}
                ], st.session_state.model)
                st.markdown(analysis)
    
    st.divider()
    st.caption("🧪 DenLab v1.0")
