import streamlit as st
import requests
import base64
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional
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
    
    /* Chat messages */
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
    
    /* Fixed chat input at bottom */
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
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid #1e242c;
    }
    [data-testid="stSidebar"] * { color: #e6edf3 !important; }
    
    /* Buttons */
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
    
    /* Code blocks */
    code { background: #1e242c; padding: 2px 8px; border-radius: 6px; color: #e6edf3; }
    pre {
        background: #1e242c;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        overflow-x: auto;
    }
    
    /* Headers */
    h1, h2, h3, h4 { color: #e6edf3 !important; font-weight: 600 !important; }
    a { color: #667eea !important; text-decoration: none !important; }
    a:hover { text-decoration: underline !important; }
    
    /* Welcome screen */
    .welcome-container { text-align: center; padding: 60px 20px; }
    .welcome-title { font-size: 32px; font-weight: 600; color: #e6edf3; margin-bottom: 16px; }
    .welcome-subtitle { font-size: 18px; color: #7d8590; margin-bottom: 40px; }
    
    /* File uploader */
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

# Upload handling state (prevents infinite loops)
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())

if "pending_upload" not in st.session_state:
    st.session_state.pending_upload = None

if "processing_upload" not in st.session_state:
    st.session_state.processing_upload = False

# ---------- API FUNCTIONS (with retry) ----------
def chat_api(messages: List[Dict], model: str, retries: int = 2) -> str:
    """Send request with basic retry logic."""
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
