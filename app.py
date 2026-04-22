"""
DenLab Chat - Kimi-inspired Clean UI with Multi-Provider AI
Streamlit application with guardrails, fallback providers, and clean design.
"""

import streamlit as st
import os
import sys
import re
import json
import time
import requests
import html as html_module
from datetime import datetime
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import MultiProviderClient, ContentGuardrails
from auth import get_auth_manager
from chat_db import get_chat_db, generate_id

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="DenLab Chat",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/daktari-art/denlab-chat',
        'Report a bug': 'https://github.com/daktari-art/denlab-chat/issues',
        'About': 'DenLab Chat - Kimi-inspired AI Assistant'
    }
)

# ============ SAFE SYSTEM PROMPT ============
SYSTEM_PROMPT = """You are DenLab, an advanced AI research assistant with tool-use capabilities.

Guidelines:
1. Be helpful, accurate, and thorough in your responses
2. Use available tools when they would improve the answer
3. Provide clear explanations with examples when helpful
4. Break down complex tasks into steps
5. Write clean, well-documented code when requested
6. Research topics thoroughly using search when current information is needed
7. Respect user autonomy and provide factual information
8. Decline requests that would cause harm, but remain helpful for legitimate uses

Available tools:
- web_search: Search the live web for current information
- deep_research: Multi-hop research across sources
- execute_code: Run Python code in sandboxed environment
- fetch_url: Scrape specific web pages
- read_file: Read uploaded file contents
- write_file: Save generated content to files
- analyze_image: Analyze and describe uploaded images in detail

When using tools, think step by step and explain your reasoning."""

# ============ MODELS ============
MODELS = {
    "GPT-4o": "openai",
    "GPT-4o mini": "openai-mini",
    "Claude 3.5 Sonnet": "claude",
    "Gemini 2.0 Flash": "gemini",
    "Llama 3.3 70B": "llama",
    "Mistral Large": "mistral",
    "DeepSeek V3": "deepseek",
    "Qwen 2.5 72B": "qwen",
    "Kimi K2.5": "kimi"
}

# ============ KIMI-INSPIRED CLEAN CSS ============
st.markdown("""
<style>
    /* ======== RESET & BASE ======== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important; }
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none !important;}
    
    /* ======== MAIN BACKGROUND - Clean light gray/white like Kimi ======== */
    .stApp {
        background-color: #f5f5f5 !important;
    }
    
    .main .block-container {
        max-width: 800px !important;
        margin: 0 auto !important;
        padding: 0 20px 200px 20px !important;
    }
    
    /* ======== SIDEBAR - Clean dark ======== */
    [data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #222222 !important;
        min-width: 260px !important;
        max-width: 260px !important;
    }
    
    [data-testid="stSidebar"] .block-container {
        padding: 16px 12px !important;
    }
    
    /* ======== CHAT MESSAGES ======== */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 4px 0 !important;
        margin: 2px 0 !important;
    }
    
    [data-testid="stChatMessageContent"] {
        color: #333333 !important;
        font-size: 14px !important;
        line-height: 1.7 !important;
        font-weight: 400 !important;
    }
    
    /* User message - subtle background */
    [data-testid="stChatMessage"][data-testid*="user"] > div:first-child > div:first-child {
        background: #ffffff !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    }
    
    /* Assistant message */
    [data-testid="stChatMessage"][data-testid*="assistant"] > div:first-child > div:first-child {
        background: #ffffff !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    }
    
    /* ======== CHAT INPUT - White/light like Kimi ======== */
    .stChatInput {
        position: fixed !important;
        bottom: 24px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 320px) !important;
        max-width: 760px !important;
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 24px !important;
        padding: 4px 12px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important;
        z-index: 1000 !important;
    }
    
    .stChatInput:focus-within {
        border-color: #10a37f !important;
        box-shadow: 0 4px 20px rgba(16, 163, 127, 0.12) !important;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        border: none !important;
        color: #333333 !important;
        font-size: 14px !important;
        padding: 12px 16px !important;
        min-height: 24px !important;
    }
    
    .stChatInput textarea::placeholder {
        color: #999999 !important;
        font-size: 14px !important;
    }
    
    /* Chat input send button */
    .stChatInput button {
        background: #10a37f !important;
        color: white !important;
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        min-width: 32px !important;
        padding: 0 !important;
        border: none !important;
    }
    
    .stChatInput button:hover {
        background: #0d8c6d !important;
    }
    
    /* ======== TYPOGRAPHY - Small, readable, bold topics ======== */
    h1 { font-size: 20px !important; font-weight: 700 !important; color: #111111 !important; }
    h2 { font-size: 16px !important; font-weight: 600 !important; color: #333333 !important; }
    h3 { font-size: 14px !important; font-weight: 600 !important; color: #444444 !important; }
    h4 { font-size: 13px !important; font-weight: 600 !important; color: #555555 !important; }
    
    p { color: #333333 !important; font-size: 14px !important; line-height: 1.7 !important; }
    
    strong { font-weight: 600 !important; color: #222222 !important; }
    
    /* ======== CODE BLOCKS ======== */
    pre {
        background: #f6f8fa !important;
        border: 1px solid #e1e4e8 !important;
        border-radius: 10px !important;
        padding: 14px !important;
        font-size: 13px !important;
    }
    
    code {
        background: #f0f0f0 !important;
        color: #333333 !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 13px !important;
        font-family: 'SF Mono', 'Fira Code', monospace !important;
    }
    
    pre code {
        background: transparent !important;
        padding: 0 !important;
    }
    
    /* ======== COMPACT ACTION ICONS ======== */
    .action-icons-row {
        display: flex;
        gap: 4px;
        margin-top: 8px;
        padding-top: 4px;
        border-top: 1px solid #f0f0f0;
    }
    
    .action-icon-btn {
        background: transparent;
        border: none;
        color: #999;
        padding: 4px 6px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        transition: all 0.15s;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
    }
    
    .action-icon-btn:hover {
        background: #f0f0f0;
        color: #555;
    }
    
    /* ======== FILE UPLOAD ATTACHMENTS ======== */
    .file-attachment {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        margin: 4px 4px 4px 0;
        font-size: 13px;
        color: #555;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    
    .file-attachment .file-icon {
        font-size: 18px;
    }
    
    .file-attachment .file-name {
        font-weight: 500;
        color: #333;
    }
    
    .file-attachment .file-size {
        font-size: 11px;
        color: #999;
    }
    
    /* ======== AGENT PROGRESS - Kimi style ======== */
    .agent-progress-container {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 14px 16px;
        margin: 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    
    .agent-progress-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        color: #555;
        margin-bottom: 8px;
    }
    
    .agent-progress-bar {
        height: 4px;
        background: #f0f0f0;
        border-radius: 2px;
        overflow: hidden;
        margin-bottom: 10px;
    }
    
    .agent-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #10a37f, #34d399);
        border-radius: 2px;
        transition: width 0.3s ease;
    }
    
    .agent-step-row {
        display: flex;
        align-items: center;
        padding: 4px 0;
        font-size: 12px;
        color: #666;
    }
    
    .step-indicator {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        margin-right: 10px;
        flex-shrink: 0;
    }
    
    .step-pending { background: #f0f0f0; color: #aaa; }
    .step-running { background: #dbeafe; color: #3b82f6; }
    .step-success { background: #d1fae5; color: #10a37f; }
    .step-error { background: #fee2e2; color: #ef4444; }
    
    /* ======== AGENT MODE BADGE ======== */
    .agent-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 20px;
        font-size: 12px;
        color: #166534;
        font-weight: 500;
    }
    
    .agent-badge .agent-dot {
        width: 6px;
        height: 6px;
        background: #10a37f;
        border-radius: 50%;
        animation: agent-pulse 1.5s infinite;
    }
    
    @keyframes agent-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    
    /* ======== SCROLLBAR ======== */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #d0d0d0; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #aaa; }
    
    /* ======== BUTTONS ======== */
    .stButton button {
        background: transparent !important;
        color: #666 !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        font-size: 12px !important;
        transition: all 0.15s !important;
    }
    
    .stButton button:hover {
        background: #f5f5f5 !important;
        border-color: #ccc !important;
        color: #333 !important;
    }
    
    .stButton button[kind="primary"] {
        background: #111111 !important;
        color: #ffffff !important;
        border-color: #111111 !important;
    }
    
    .stButton button[kind="primary"]:hover {
        background: #333333 !important;
        border-color: #333333 !important;
    }
    
    /* ======== INPUT FIELDS ======== */
    .stTextInput input {
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        color: #333 !important;
        font-size: 13px !important;
    }
    
    .stTextInput input:focus {
        border-color: #10a37f !important;
    }
    
    /* ======== SELECT BOX ======== */
    .stSelectbox > div > div {
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        color: #333 !important;
        font-size: 13px !important;
    }
    
    /* ======== TOGGLE ======== */
    .stToggle > div > div > div {
        background-color: #e0e0e0 !important;
    }
    
    .stToggle > div > div > div[data-checked="true"] {
        background-color: #10a37f !important;
    }
    
    /* ======== DIVIDER ======== */
    hr { border-color: #e8e8e8 !important; margin: 10px 0 !important; }
    
    /* ======== CAPTION ======== */
    .stCaption { color: #999 !important; font-size: 11px !important; }
    
    /* ======== SPINNER ======== */
    .stSpinner > div { border-color: #10a37f !important; }
    
    /* ======== EXPANDER ======== */
    .stExpander {
        border: 1px solid #e8e8e8 !important;
        border-radius: 10px !important;
        background: #ffffff !important;
    }
    
    /* ======== SIDEBAR ELEMENTS ======== */
    [data-testid="stSidebar"] h1 {
        color: #ffffff !important;
        font-size: 16px !important;
    }
    
    [data-testid="stSidebar"] p {
        color: #888888 !important;
        font-size: 12px !important;
    }
    
    [data-testid="stSidebar"] .stButton button {
        background: #1a1a1a !important;
        color: #e0e0e0 !important;
        border: 1px solid #2a2a2a !important;
        font-size: 12px !important;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        background: #2a2a2a !important;
        border-color: #444 !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: #1a1a1a !important;
        border-color: #2a2a2a !important;
        color: #e0e0e0 !important;
    }
    
    /* ======== TOP HEADER BAR ======== */
    .top-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 16px;
        background: #ffffff;
        border-bottom: 1px solid #e8e8e8;
        margin: -16px -20px 16px -20px;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    
    .model-selector {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        background: #f5f5f5;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
        color: #333;
        cursor: pointer;
        transition: background 0.15s;
    }
    
    .model-selector:hover {
        background: #eeeeee;
    }
    
    /* ======== STATUS DOT ======== */
    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
    }
    
    .status-online { background: #10a37f; }
    .status-busy { background: #f59e0b; }
    .status-offline { background: #ef4444; }
    
    /* ======== IMAGE IN CHAT ======== */
    [data-testid="stChatMessageContent"] img {
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        max-width: 100% !important;
    }
    
    /* ======== TOAST/ALERT ======== */
    .stAlert {
        border-radius: 10px !important;
        font-size: 13px !important;
    }
    
    /* ======== AUTH CONTAINER ======== */
    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 40px 24px;
    }
    
    .auth-title {
        text-align: center;
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 24px;
        color: #111;
    }
    
    /* ======== WELCOME SCREEN ======== */
    .welcome-container {
        text-align: center;
        padding: 80px 20px 40px;
    }
    
    .welcome-icon {
        font-size: 36px;
        margin-bottom: 16px;
    }
    
    .welcome-title {
        font-size: 22px;
        font-weight: 700;
        color: #111;
        margin-bottom: 8px;
    }
    
    .welcome-subtitle {
        font-size: 13px;
        color: #888;
        margin-bottom: 40px;
    }
    
    .welcome-cmd {
        font-size: 13px;
        color: #666;
        line-height: 2.2;
    }
    
    .welcome-cmd code {
        background: #f0f0f0;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        color: #10a37f;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# ============ PWA ============
st.markdown("""
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#f5f5f5">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="mobile-web-app-capable" content="yes">
<meta name="application-name" content="DenLab">
<meta name="apple-mobile-web-app-title" content="DenLab">
<script>
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('service-worker.js')
        .then(function(reg) { console.log('SW registered:', reg.scope); })
        .catch(function(err) { console.log('SW failed:', err); });
}
</script>
""", unsafe_allow_html=True)


# ============ SESSION STATE INIT ============
def init_session():
    defaults = {
        "user_token": None,
        "current_user": None,
        "current_conversation_id": None,
        "selected_model": "openai",
        "agent_mode": False,
        "swarm_mode": False,
        "uploader_key": "0",
        "pending_upload": None,
        "processing_upload": False,
        "show_settings": False,
        "uploaded_files": {},
        "messages_cache": [],
        "sidebar_collapsed": False,
        "agent_progress": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    
    if st.session_state.user_token:
        auth = get_auth_manager()
        user = auth.validate_token(st.session_state.user_token)
        if not user:
            st.session_state.user_token = None
            st.session_state.current_user = None

init_session()


# ============ UTILITY FUNCTIONS ============

def format_message_content(content: str) -> str:
    """Format message content. Returns HTML string."""
    if not content:
        return ""
    
    content = html_module.escape(content)
    
    code_pattern = r'```(\w*)\n(.*?)```'
    def replace_code(match):
        lang = match.group(1) or "text"
        code = html_module.escape(html_module.unescape(match.group(2)))
        return f'<div style="background:#f6f8fa;border:1px solid #e1e4e8;border-radius:10px;margin:8px 0;overflow:hidden;"><div style="display:flex;justify-content:space-between;align-items:center;background:#f0f0f0;padding:6px 12px;border-bottom:1px solid #e1e4e8;font-size:11px;color:#666;"><span>{lang}</span></div><pre style="margin:0;padding:14px;overflow-x:auto;"><code style="background:transparent;padding:0;font-size:13px;line-height:1.5;">{code}</code></pre></div>'
    
    content = re.sub(code_pattern, replace_code, content, flags=re.DOTALL)
    content = re.sub(r'`([^`]+)`', r'<code style="background:#f0f0f0;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:13px;color:#10a37f;">\1</code>', content)
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong style="font-weight:600;color:#222;">\1</strong>', content)
    content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
    content = content.replace('\n', '<br>')
    
    return content


def get_or_create_client() -> MultiProviderClient:
    if "ai_client" not in st.session_state:
        st.session_state.ai_client = MultiProviderClient()
    return st.session_state.ai_client


def ensure_conversation() -> str:
    user = st.session_state.current_user
    if not user:
        return None
    
    if not st.session_state.current_conversation_id:
        db = get_chat_db(user["username"])
        conv_id = db.get_or_create_default(model=st.session_state.selected_model)
        st.session_state.current_conversation_id = conv_id
    
    return st.session_state.current_conversation_id


# ============ TOOL FUNCTIONS ============
def web_search(query: str) -> str:
    try:
        url = f"https://ddg-api.herokuapp.com/search?query={requests.utils.quote(query)}&limit=5"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            results = []
            for item in resp.json()[:5]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", "")
                })
            return json.dumps({"success": True, "results": results})
        return json.dumps({"success": False, "error": f"Status {resp.status_code}"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def deep_research(topic: str, depth: int = 2) -> str:
    try:
        findings, sources = [], []
        result = json.loads(web_search(topic))
        if result.get("success"):
            for item in result["results"][:3]:
                sources.append(item["url"])
                findings.append({
                    "title": item["title"],
                    "source": item["url"],
                    "content": item["snippet"]
                })
        if depth > 1:
            for f in findings[:2]:
                sub = json.loads(web_search(f["title"]))
                if sub.get("success"):
                    for item in sub["results"][:2]:
                        if item["url"] not in sources:
                            sources.append(item["url"])
                            findings.append({
                                "title": item["title"],
                                "source": item["url"],
                                "content": item["snippet"]
                            })
        return json.dumps({
            "success": True,
            "topic": topic,
            "total_sources": len(set(sources)),
            "findings": findings
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def execute_code(code: str) -> str:
    try:
        import io, sys, traceback
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        try:
            exec(code, {"__builtins__": __builtins__})
            return json.dumps({"success": True, "stdout": sys.stdout.getvalue(), "stderr": sys.stderr.getvalue()})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e), "traceback": traceback.format_exc()})
        finally:
            sys.stdout, sys.stderr = old_out, old_err
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def fetch_url(url: str) -> str:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "DenLab/4.0"})
        if resp.status_code == 200:
            return json.dumps({"success": True, "content": resp.text[:5000]})
        return json.dumps({"success": False, "error": f"HTTP {resp.status_code}"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def read_file(path: str) -> str:
    try:
        if path in st.session_state.uploaded_files:
            f = st.session_state.uploaded_files[path]
            return json.dumps({
                "success": True,
                "content": f.get("content", "")[:10000],
                "name": f.get("name")
            })
        return json.dumps({"success": False, "error": "File not found"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def write_file(path: str, content: str) -> str:
    try:
        st.session_state.uploaded_files[path] = {
            "type": "text", "name": path, "content": content,
            "size": len(content), "timestamp": datetime.now().isoformat()
        }
        return json.dumps({"success": True, "path": path, "size": len(content)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def analyze_image(file_key: str, prompt: str = "Describe this image in detail.") -> str:
    """Analyze uploaded image using vision capabilities."""
    try:
        from features.vision import VisionAnalyzer
        analyzer = VisionAnalyzer()
        
        if file_key not in st.session_state.uploaded_files:
            return json.dumps({"success": False, "error": "Image not found in uploaded files"})
        
        img_data = st.session_state.uploaded_files[file_key]
        if img_data.get("type") != "image":
            return json.dumps({"success": False, "error": "File is not an image"})
        
        result = analyzer.analyze(img_data["bytes"], prompt=prompt, model="gemini")
        return json.dumps({"success": True, "analysis": result})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


TOOLS_REGISTRY = {
    "web_search": {"func": web_search, "description": "Search the web for current information", "params": {"query": {"type": "string", "description": "Search query"}}},
    "deep_research": {"func": deep_research, "description": "Deep research across multiple sources", "params": {"topic": {"type": "string", "description": "Research topic"}}},
    "execute_code": {"func": execute_code, "description": "Run Python code in sandboxed environment", "params": {"code": {"type": "string", "description": "Python code to execute"}}},
    "fetch_url": {"func": fetch_url, "description": "Fetch and read content from a URL", "params": {"url": {"type": "string", "description": "URL to fetch"}}},
    "read_file": {"func": read_file, "description": "Read uploaded file contents", "params": {"path": {"type": "string", "description": "File path or key"}}},
    "write_file": {"func": write_file, "description": "Write content to a file", "params": {"path": {"type": "string", "description": "File path"}, "content": {"type": "string", "description": "Content to write"}}},
    "analyze_image": {"func": analyze_image, "description": "Analyze uploaded images using vision AI", "params": {"file_key": {"type": "string", "description": "File key of uploaded image"}, "prompt": {"type": "string", "description": "Analysis prompt"}}},
}


def get_tool_schema() -> List[Dict]:
    tools = []
    for name, meta in TOOLS_REGISTRY.items():
        props = {}
        required = []
        for param_name, param_info in meta["params"].items():
            props[param_name] = {
                "type": param_info.get("type", "string"),
                "description": param_info.get("description", "")
            }
            required.append(param_name)
        
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required
                }
            }
        })
    return tools


def execute_tool_call(tc_data: Dict) -> Dict:
    fn = tc_data.get("function", {})
    name = fn.get("name", "unknown")
    args_str = fn.get("arguments", "{}")
    
    try:
        args = json.loads(args_str) if isinstance(args_str, str) else args_str
    except json.JSONDecodeError:
        return {"name": name, "status": "error", "result": "Invalid arguments JSON", "duration_ms": 0}
    
    if name not in TOOLS_REGISTRY:
        return {"name": name, "status": "error", "result": f"Tool '{name}' not available", "duration_ms": 0}
    
    start = time.time()
    try:
        result = TOOLS_REGISTRY[name]["func"](**args)
        status = "success"
    except Exception as e:
        result = f"Error: {str(e)}"
        status = "error"
    
    duration_ms = (time.time() - start) * 1000
    return {"name": name, "status": status, "result": str(result)[:4000], "duration_ms": duration_ms}


# ============ AUTHENTICATION UI ============

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">DenLab Chat</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Sign In", "Create Account"])
        
        with tab1:
            with st.form("login_form"):
                st.markdown("**Welcome back**")
                username = st.text_input("Username", placeholder="your_username")
                password = st.text_input("Password", type="password", placeholder="••••••")
                submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                
                if submit:
                    if not username or not password:
                        st.error("Please fill in all fields")
                    else:
                        auth = get_auth_manager()
                        result = auth.login(username, password)
                        if result["success"]:
                            st.session_state.user_token = result["token"]
                            st.session_state.current_user = result["user"]
                            st.success(f"Welcome back, {result['user']['display_name']}!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(result["error"])
        
        with tab2:
            with st.form("register_form"):
                st.markdown("**Create your account**")
                new_username = st.text_input("Choose Username", placeholder="e.g., johndoe")
                new_display = st.text_input("Display Name (optional)", placeholder="John Doe")
                new_password = st.text_input("Password", type="password", placeholder="Min 6 characters")
                confirm_password = st.text_input("Confirm Password", type="password")
                submit_reg = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                
                if submit_reg:
                    if not new_username or not new_password:
                        st.error("Username and password are required")
                    elif new_password != confirm_password:
                        st.error("Passwords don't match")
                    else:
                        auth = get_auth_manager()
                        result = auth.register(new_username, new_password, new_display or None)
                        if result["success"]:
                            st.session_state.user_token = result["token"]
                            st.session_state.current_user = result["user"]
                            st.success("Account created successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(result["error"])
        
        st.markdown('<p style="text-align:center;color:#999;font-size:11px;margin-top:2rem;">No email required. Your data stays on this device.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def show_user_menu():
    user = st.session_state.current_user
    
    with st.sidebar:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:10px;background:#1a1a1a;border-radius:10px;margin-bottom:10px;">
            <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#10a37f,#34d399);display:flex;align-items:center;justify-content:center;font-weight:600;color:white;font-size:14px;">
                {user['display_name'][0].upper()}
            </div>
            <div>
                <div style="font-weight:600;color:#e8e8e8;font-size:13px;">{html_module.escape(user['display_name'])}</div>
                <div style="font-size:11px;color:#888;">@{html_module.escape(user['username'])}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Settings", use_container_width=True):
                st.session_state.show_settings = True
                st.rerun()
        with col2:
            if st.button("Sign Out", use_container_width=True):
                auth = get_auth_manager()
                auth.logout(st.session_state.user_token)
                for key in ['user_token', 'current_user', 'current_conversation_id']:
                    if key in st.session_state:
                        st.session_state[key] = None
                st.rerun()
        
        st.divider()


def show_settings():
    st.markdown("## Settings")
    
    user = st.session_state.current_user
    auth = get_auth_manager()
    
    tab1, tab2, tab3 = st.tabs(["Account", "Chat", "Danger Zone"])
    
    with tab1:
        st.markdown("### Profile")
        st.write(f"**Username:** @{user['username']}")
        
        with st.form("change_password"):
            st.markdown("**Change Password**")
            old_pass = st.text_input("Current Password", type="password")
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password", type="primary"):
                if new_pass != confirm_pass:
                    st.error("New passwords don't match")
                else:
                    result = auth.change_password(st.session_state.user_token, old_pass, new_pass)
                    if result["success"]:
                        st.success("Password updated!")
                    else:
                        st.error(result["error"])
    
    with tab2:
        st.markdown("### Chat Settings")
        
        model = st.selectbox(
            "Default Model",
            ["openai", "claude", "gemini", "llama", "deepseek"],
            index=0
        )
        
        stream = st.toggle("Stream Responses", value=True)
        
        if st.button("Save Settings", type="primary"):
            auth.update_settings(st.session_state.user_token, {
                "default_model": model,
                "stream_responses": stream,
            })
            st.success("Settings saved!")
    
    with tab3:
        st.markdown("### Delete Account")
        st.warning("This will permanently delete your account and all chat history!")
        
        with st.form("delete_account"):
            confirm_pass = st.text_input("Enter Password to Confirm", type="password")
            if st.form_submit_button("Delete My Account", type="secondary"):
                result = auth.delete_account(st.session_state.user_token, confirm_pass)
                if result["success"]:
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.success("Account deleted. Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(result["error"])
    
    if st.button("Back to Chat"):
        st.session_state.show_settings = False
        st.rerun()


# ============ SIDEBAR ============

def show_sidebar():
    """Show the sidebar with conversation list and controls."""
    user = st.session_state.current_user
    db = get_chat_db(user["username"])
    
    with st.sidebar:
        # Header
        st.markdown("""
        <div style="border-bottom: 1px solid #222; padding-bottom: 12px; margin-bottom: 12px;">
            <h1 style="font-size: 16px; margin: 0; color: #fff; font-weight: 700;">DenLab Chat</h1>
            <p style="font-size: 11px; color: #666; margin: 4px 0 0 0;">Kimi-inspired AI</p>
        </div>
        """, unsafe_allow_html=True)
        
        # New chat button
        if st.button("+ New Chat", use_container_width=True, type="primary"):
            conv_id = db.create_conversation(model=st.session_state.get("selected_model", "openai"))
            st.session_state.current_conversation_id = conv_id
            st.rerun()
        
        st.divider()
        
        # Model selector - Kimi style
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Model</p>', unsafe_allow_html=True)
        
        model_names = list(MODELS.keys())
        model_values = list(MODELS.values())
        current_model = st.session_state.get("selected_model", "openai")
        idx = model_values.index(current_model) if current_model in model_values else 0
        choice = st.selectbox("Model", model_names, index=idx, label_visibility="collapsed")
        st.session_state.selected_model = MODELS[choice]
        
        # Model badge
        caps = []
        if "vision" in str(MODELS[choice]):
            caps.append("vision")
        if "tools" in str(MODELS[choice]):
            caps.append("tools")
        if caps:
            st.caption(" " + " ".join([f"{c}" for c in caps]))
        
        st.divider()
        
        # Agent mode toggle - Kimi style
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Agent Mode</p>', unsafe_allow_html=True)
        
        agent_col1, agent_col2 = st.columns([3, 1])
        with agent_col1:
            st.markdown("""
            <div class="agent-badge" style="margin-top:4px;">
                <div class="agent-dot"></div>
                <span>Agent</span>
            </div>
            """, unsafe_allow_html=True)
        with agent_col2:
            agent_mode = st.toggle("", value=st.session_state.agent_mode, label_visibility="collapsed", key="agent_toggle")
            st.session_state.agent_mode = agent_mode
        
        if st.session_state.agent_mode:
            st.caption("Autonomous tool-use enabled")
        
        st.divider()
        
        # Conversation list
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Conversations</p>', unsafe_allow_html=True)
        
        conversations = db.get_conversations()
        
        if not conversations:
            st.caption("No conversations yet")
        else:
            for conv in conversations[:15]:
                conv_id = conv["id"]
                title = conv.get("title", "Untitled")
                msg_count = len(conv.get("messages", []))
                is_active = conv_id == st.session_state.get("current_conversation_id")
                
                btn_label = f"{html_module.escape(title[:24])}{'...' if len(title) > 24 else ''}"
                btn_type = "primary" if is_active else "secondary"
                
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    if st.button(btn_label, key=f"conv_{conv_id}", use_container_width=True, type=btn_type):
                        st.session_state.current_conversation_id = conv_id
                        st.rerun()
                with col2:
                    if st.button("", key=f"del_{conv_id}", help="Delete", icon="🗑"):
                        db.delete_conversation(conv_id)
                        if st.session_state.get("current_conversation_id") == conv_id:
                            remaining = db.get_conversations()
                            st.session_state.current_conversation_id = remaining[0]["id"] if remaining else None
                        st.rerun()
        
        st.divider()
        
        # Export
        current_conv = st.session_state.get("current_conversation_id")
        if current_conv:
            if st.button("Export Chat", use_container_width=True):
                export_data = db.export_conversation(current_conv)
                conv = db.get_conversation(current_conv)
                title = conv.get("title", "chat") if conv else "chat"
                st.download_button("Download", export_data, f"denlab_{title.replace(' ', '_')}.md", use_container_width=True)
        
        st.divider()
        st.caption(f"v4.2 · Multi-provider fallback")


# ============ COMPACT ACTION ICONS ============

def render_message_actions(msg_idx: int, content: str, msg_type: str = "text"):
    """Render compact icon-only action buttons below a message."""
    cols = st.columns([1, 1, 1, 1, 1, 20])
    
    with cols[0]:
        if st.button("📋", key=f"act_copy_{msg_idx}", help="Copy to clipboard"):
            st.toast("Copied!")
    
    with cols[1]:
        if st.button("🔊", key=f"act_speak_{msg_idx}", help="Text to speech"):
            try:
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
            st.download_button("⬇️", content, f"msg_{msg_idx}.md", "text/markdown", key=f"act_dl_{msg_idx}", help="Download")
    
    with cols[4]:
        if st.button("👍", key=f"act_like_{msg_idx}", help="Helpful"):
            st.toast("Thanks!")


# ============ AGENT EXECUTION ============

def run_agent_task(prompt: str, model: str, progress_placeholder) -> Dict[str, Any]:
    """Execute agent task with synchronous step-by-step execution."""
    client = get_or_create_client()
    traces = []
    max_steps = 12
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nYou have tools available. Use them when needed. Think step by step."},
        {"role": "user", "content": prompt}
    ]
    
    for step in range(1, max_steps + 1):
        progress_placeholder.markdown(f"""
        <div class="agent-progress-container">
            <div class="agent-progress-header">
                <span>🤖</span>
                <span>Step {step}/{max_steps}</span>
                <span class="status-dot status-busy"></span>
            </div>
            <div class="agent-progress-bar">
                <div class="agent-progress-fill" style="width: {(step/max_steps)*100}%"></div>
            </div>
            <div style="font-size: 12px; color: #666;">Thinking...</div>
        </div>
        """, unsafe_allow_html=True)
        
        response = client.chat(messages, model=model, tools=get_tool_schema())
        
        if response.get("guardrail_triggered"):
            return {"content": response["content"], "traces": traces}
        
        content = response.get("content") or ""
        tool_calls_raw = response.get("tool_calls") or []
        provider = response.get("provider", "unknown")
        
        trace = {
            "step": step,
            "thought": content[:200] if content else f"Step {step}: processing...",
            "tool_calls": [],
            "provider": provider
        }
        
        if tool_calls_raw:
            tool_results = []
            for tc_raw in tool_calls_raw:
                tc_result = execute_tool_call(tc_raw)
                trace["tool_calls"].append(tc_result)
                
                tool_msg = {
                    "role": "tool",
                    "content": str(tc_result["result"])[:4000],
                    "tool_call_id": tc_raw.get("id", f"call_{step}")
                }
                messages.append(tool_msg)
                tool_results.append(tool_msg)
            
            assistant_msg = {
                "role": "assistant",
                "content": content or "Using tools...",
                "tool_calls": [
                    {"id": tc_raw.get("id", ""), "type": "function", "function": tc_raw.get("function", {})}
                    for tc_raw in tool_calls_raw
                ]
            }
            messages.append(assistant_msg)
            traces.append(trace)
            
            tool_summary = " ".join([
                f"{'✓' if t['status'] == 'success' else '✗'} {t['name']}"
                for t in trace["tool_calls"]
            ])
            
            progress_placeholder.markdown(f"""
            <div class="agent-progress-container">
                <div class="agent-progress-header">
                    <span>🤖</span>
                    <span>Step {step}/{max_steps}</span>
                    <span style="color: #10a37f;">{tool_summary}</span>
                </div>
                <div class="agent-progress-bar">
                    <div class="agent-progress-fill" style="width: {(step/max_steps)*100}%"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            follow_up = client.chat(messages, model=model)
            follow_content = follow_up.get("content") or ""
            
            if not follow_up.get("tool_calls"):
                messages.append({"role": "assistant", "content": follow_content or "Task complete."})
                if follow_content:
                    traces.append({
                        "step": step + 0.5,
                        "thought": follow_content[:200],
                        "tool_calls": [],
                        "provider": follow_up.get("provider", provider)
                    })
                return {"content": follow_content or "Task completed successfully.", "traces": traces}
            else:
                messages.append({"role": "assistant", "content": follow_content or "Continuing..."})
        else:
            trace["response"] = content
            traces.append(trace)
            progress_placeholder.markdown(f"""
            <div class="agent-progress-container">
                <div class="agent-progress-header">
                    <span>✓</span>
                    <span>Complete</span>
                </div>
                <div class="agent-progress-bar">
                    <div class="agent-progress-fill" style="width: 100%"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            return {"content": content or "Task completed.", "traces": traces}
    
    final_content = traces[-1].get("response", "") if traces else ""
    if not final_content:
        final_content = "Maximum steps reached. Here's what I accomplished:\n\n" + \
            "\n".join([f"Step {t['step']}: {t['thought']}" for t in traces])
    
    return {"content": final_content, "traces": traces}


# ============ MAIN APP ============

if not st.session_state.current_user:
    show_login_page()
    st.stop()

if st.session_state.show_settings:
    show_user_menu()
    show_settings()
    st.stop()

show_user_menu()

conv_id = ensure_conversation()

# Top header bar with model selector
model_display = [k for k, v in MODELS.items() if v == st.session_state.selected_model]
model_display_name = model_display[0] if model_display else "GPT-4o"

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0 16px 0;border-bottom:1px solid #e8e8e8;margin-bottom:16px;">
    <div style="display:flex;align-items:center;gap:8px;">
        <div class="model-selector" onclick="">
            <span style="font-size:16px;">🧪</span>
            <span>{model_display_name}</span>
            <span style="color:#999;font-size:11px;">{'● Agent' if st.session_state.agent_mode else ''}</span>
            <span style="color:#ccc;">›</span>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
        <span class="status-dot status-online" title="Online"></span>
    </div>
</div>
""", unsafe_allow_html=True)

# Show sidebar
show_sidebar()

# ============ FILE UPLOAD AREA (near prompt) ============
uploaded = st.file_uploader(
    "Attach file",
    type=["txt", "py", "js", "ts", "jsx", "tsx", "html", "css", "json", "md",
          "csv", "xml", "yaml", "yml", "sh", "bash", "c", "cpp", "h", "hpp",
          "java", "kt", "swift", "rs", "go", "rb", "php", "sql",
          "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "pdf"],
    accept_multiple_files=False,
    label_visibility="collapsed",
    key=f"prompt_uploader_{st.session_state.uploader_key}"
)

# Handle file upload
if uploaded and not st.session_state.processing_upload:
    st.session_state.pending_upload = uploaded
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(int(st.session_state.uploader_key) + 1)
    st.rerun()

if st.session_state.pending_upload and st.session_state.processing_upload:
    fobj = st.session_state.pending_upload
    fname = fobj.name
    fkey = f"{datetime.now().strftime('%H%M%S')}_{fname}"
    try:
        fb = fobj.read()
        if fobj.type and fobj.type.startswith("image/"):
            st.session_state.uploaded_files[fkey] = {"type": "image", "name": fname, "bytes": fb, "mime": fobj.type}
            db = get_chat_db(st.session_state.current_user["username"])
            db.add_message(conv_id, "user", f"📎 {fname}", {"type": "image_upload", "file_key": fkey})
            # Auto-analyze image with enhanced vision
            try:
                from features.vision import VisionAnalyzer
                analyzer = VisionAnalyzer()
                analysis = analyzer.analyze(fb, prompt="Describe this image in detail. Identify all objects, text, people, and context.", model="gemini")
                db.add_message(conv_id, "assistant", f"**📎 {fname}**\n\n{analysis}")
            except Exception as e:
                db.add_message(conv_id, "assistant", f"**📎 {fname}** received. Image loaded successfully.")
        else:
            txt = fb.decode('utf-8', errors='ignore')
            st.session_state.uploaded_files[fkey] = {"type": "text", "name": fname, "content": txt, "size": len(txt)}
            db = get_chat_db(st.session_state.current_user["username"])
            db.add_message(conv_id, "user", f"📎 {fname}", {"type": "file", "file_key": fkey})
            db.add_message(conv_id, "assistant", f"**📎 {fname}** loaded ({len(txt)} chars). Ask me to analyze it.")
    except Exception as e:
        st.error(f"Upload error: {e}")
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# Display messages from database
db = get_chat_db(st.session_state.current_user["username"])
conv = db.get_conversation(conv_id) if conv_id else None
messages = conv.get("messages", []) if conv else []

# Show welcome if no visible messages
visible_messages = [m for m in messages if m.get("role") != "system"]
if not visible_messages:
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-icon">🧪</div>
        <div class="welcome-title">DenLab Chat</div>
        <div class="welcome-subtitle">Kimi-inspired AI with multi-provider fallback</div>
        <div class="welcome-cmd">
            <div><code>/imagine</code> — Generate images</div>
            <div><code>/research</code> — Deep web research</div>
            <div><code>/code</code> — Generate & execute Python</div>
            <div><code>/analyze</code> — Analyze uploaded files</div>
            <div><code>/audio</code> — Text to speech</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Render messages
for idx, msg in enumerate(messages):
    if msg["role"] == "system":
        continue
    
    meta = msg.get("metadata", {})
    mtype = meta.get("type", "text")
    content = msg.get("content", "")
    
    with st.chat_message(msg["role"]):
        if mtype == "image":
            st.image(content, use_container_width=True)
            try:
                img_data = requests.get(content, timeout=15).content
                cols = st.columns([1, 1, 20])
                with cols[0]:
                    st.download_button("⬇️", img_data, f"image_{idx}.png", mime="image/png", key=f"dlimg_{idx}", help="Download")
                with cols[1]:
                    if st.button("🔗", key=f"imglink_{idx}", help="Copy URL"):
                        st.toast("URL copied!")
            except:
                pass
        elif mtype == "image_upload":
            fk = meta.get("file_key")
            if fk and fk in st.session_state.uploaded_files:
                st.image(st.session_state.uploaded_files[fk]["bytes"], use_container_width=True)
                # Show file info as attachment card
                fname = st.session_state.uploaded_files[fk]["name"]
                st.markdown(f'<div class="file-attachment"><span class="file-icon">📎</span><span class="file-name">{fname}</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(content)
        elif mtype == "file":
            st.markdown(content)
            fk = meta.get("file_key")
            if fk and fk in st.session_state.uploaded_files:
                fname = st.session_state.uploaded_files[fk]["name"]
                st.markdown(f'<div class="file-attachment"><span class="file-icon">📎</span><span class="file-name">{fname}</span></div>', unsafe_allow_html=True)
                with st.expander("Preview"):
                    st.code(st.session_state.uploaded_files[fk]["content"][:3000])
        elif mtype == "agent_trace":
            st.markdown(content)
            if meta.get("traces"):
                with st.expander("Execution Trace", expanded=False):
                    for t in meta["traces"]:
                        has_tools = bool(t.get("tool_calls"))
                        all_success = has_tools and all(tc.get("status") == "success" for tc in t.get("tool_calls", []))
                        has_error = has_tools and any(tc.get("status") == "error" for tc in t.get("tool_calls", []))
                        
                        if has_error:
                            icon = "❌"
                        elif all_success:
                            icon = "✅"
                        else:
                            icon = "🔄"
                        
                        thought = t.get("thought", "")
                        thought_display = thought[:60] + "..." if len(thought) > 60 else thought
                        if not thought_display:
                            thought_display = f"Step {t['step']}"
                        
                        st.markdown(f"**Step {t['step']}** {icon}")
                        st.caption(thought_display)
                        
                        for tc in t.get("tool_calls", []):
                            tc_icon = "✅" if tc.get("status") == "success" else "❌" if tc.get("status") == "error" else "⏳"
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{tc_icon} `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
        elif mtype == "audio":
            st.audio(content, format='audio/mp3')
        elif mtype == "code":
            st.markdown(content)
        elif mtype == "research":
            st.markdown(content)
        else:
            st.markdown(content)
        
        # Action icons for assistant messages
        if msg["role"] == "assistant" and idx > 0 and mtype not in ["image", "audio"]:
            render_message_actions(idx, content, mtype)


# ============ CHAT INPUT ============
placeholder = "Message DenLab..." if not st.session_state.agent_mode else "Describe your task for the agent..."

if prompt := st.chat_input(placeholder):
    
    # /imagine
    if prompt.lower().startswith("/imagine"):
        desc = prompt[8:].strip()
        if desc:
            w, h = 1024, 1024
            ar = re.search(r'--ar\s+(\d+:\d+)', desc)
            if ar:
                ratios = {"1:1": (1024,1024), "16:9": (1024,576), "9:16": (576,1024), "4:3": (1024,768), "3:4": (768,1024)}
                w, h = ratios.get(ar.group(1), (1024, 1024))
                desc = re.sub(r'--ar\s+\d+:\d+', '', desc).strip()
            
            db.add_message(conv_id, "user", f"🎨 {prompt}")
            
            with st.chat_message("assistant"):
                with st.spinner("Generating..."):
                    client = get_or_create_client()
                    url = client.generate_image(desc, w, h)
                    st.image(url, caption=desc, use_container_width=True)
                    try:
                        data = requests.get(url, timeout=15).content
                        cols = st.columns([1, 1, 20])
                        with cols[0]:
                            st.download_button("⬇️", data, f"img_{desc[:15].replace(' ','_')}.png", mime="image/png")
                    except:
                        pass
            
            db.add_message(conv_id, "assistant", url, {"type": "image"})
            st.rerun()
    
    # /research
    elif prompt.lower().startswith("/research"):
        topic = prompt[9:].strip()
        if topic:
            db.add_message(conv_id, "user", f"🔬 {topic}")
            
            with st.chat_message("assistant"):
                with st.status("Researching...", expanded=True) as s:
                    result = deep_research(topic, depth=2)
                    data = json.loads(result)
                    s.update(label="Done!", state="complete")
                    
                    st.markdown(f"**{data['topic']}** — {data['total_sources']} sources")
                    for f in data['findings'][:5]:
                        with st.expander(f["title"][:50]):
                            st.markdown(f"Source: {f['source']}")
                            st.markdown(f['content'][:400])
                    
                    out = f"## Research: {topic}\n\n"
                    for i, f in enumerate(data['findings'][:5], 1):
                        out += f"{i}. **{f['title']}** — {f['content'][:150]}...\n\n"
                    st.markdown(out)
            
            db.add_message(conv_id, "assistant", out, {"type": "research", "data": data})
            st.rerun()
    
    # /code
    elif prompt.lower().startswith("/code"):
        task = prompt[5:].strip()
        if task:
            db.add_message(conv_id, "user", f"💻 {task}")
            
            with st.chat_message("assistant"):
                with st.status("Coding...", expanded=True) as s:
                    client = get_or_create_client()
                    code_prompt = f"Write Python to: {task}\nReturn ONLY the code inside a markdown code block."
                    resp = client.chat([
                        {"role": "system", "content": "Expert Python programmer. Return only code in markdown blocks."},
                        {"role": "user", "content": code_prompt}
                    ], model=st.session_state.selected_model)
                    
                    raw_content = resp.get("content", "")
                    code_match = re.search(r'```python\n(.*?)```', raw_content, re.DOTALL)
                    if not code_match:
                        code_match = re.search(r'```\n(.*?)```', raw_content, re.DOTALL)
                    code = code_match.group(1).strip() if code_match else raw_content.strip()
                    
                    st.code(code, language="python")
                    result = execute_code(code)
                    data = json.loads(result)
                    
                    if data.get("success"):
                        s.update(label="Success", state="complete")
                        out = f"```python\n{code}\n```\n**Output:**\n```\n{data.get('stdout', '')}\n```"
                    else:
                        s.update(label="Error", state="error")
                        out = f"```python\n{code}\n```\n**Error:**\n```\n{data.get('error', '')}\n```"
            
            db.add_message(conv_id, "assistant", out, {"type": "code"})
            st.rerun()
    
    # /analyze
    elif prompt.lower().startswith("/analyze"):
        if st.session_state.uploaded_files:
            lk = list(st.session_state.uploaded_files.keys())[-1]
            lf = st.session_state.uploaded_files[lk]
            db.add_message(conv_id, "user", f"🔍 {lf['name']}")
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    if lf["type"] == "text":
                        client = get_or_create_client()
                        analysis = client.chat([
                            {"role": "system", "content": "Senior code reviewer and analyst."},
                            {"role": "user", "content": f"Analyze this file: {lf['name']}\n```\n{lf['content'][:4000]}\n```\n\nProvide: Purpose, Structure, Dependencies, Quality, Issues, Documentation."}
                        ], model=st.session_state.selected_model)
                        analysis_text = analysis.get("content", "Analysis failed.")
                        st.markdown(analysis_text)
                        db.add_message(conv_id, "assistant", analysis_text)
                    elif lf["type"] == "image":
                        # Use enhanced vision for image analysis
                        try:
                            from features.vision import VisionAnalyzer
                            analyzer = VisionAnalyzer()
                            analysis = analyzer.analyze(lf["bytes"], prompt="Analyze this image in detail. Describe all visible elements, text, objects, people, and context.", model="gemini")
                            st.markdown(analysis)
                            db.add_message(conv_id, "assistant", analysis)
                        except Exception as e:
                            st.error(f"Vision analysis error: {e}")
                    else:
                        st.markdown("File type not supported for analysis.")
            st.rerun()
        else:
            db.add_message(conv_id, "user", "🔍 /analyze")
            db.add_message(conv_id, "assistant", "No file uploaded. Upload a file first.")
            st.rerun()
    
    # /audio
    elif prompt.lower().startswith("/audio"):
        text = prompt[6:].strip()
        if text:
            db.add_message(conv_id, "user", f"🔊 {text[:50]}")
            with st.chat_message("assistant"):
                with st.spinner("Generating audio..."):
                    client = get_or_create_client()
                    url = client.generate_audio(text)
                    st.audio(url, format='audio/mp3')
            db.add_message(conv_id, "assistant", url, {"type": "audio", "text": text})
            st.rerun()
    
    # Agent Mode
    elif st.session_state.agent_mode:
        db.add_message(conv_id, "user", prompt)
        
        with st.chat_message("assistant"):
            progress_ph = st.empty()
            
            try:
                with st.spinner("Agent working..."):
                    result = run_agent_task(prompt, st.session_state.selected_model, progress_ph)
                
                response = result.get("content", "")
                traces = result.get("traces", [])
                
                if response:
                    st.markdown(response)
                else:
                    st.markdown("The agent completed but returned no output. The AI service may be temporarily unavailable.")
                
                # Show agent execution trace
                if traces:
                    with st.expander("Execution Trace", expanded=False):
                        for t in traces:
                            has_tools = bool(t.get("tool_calls"))
                            all_success = has_tools and all(tc.get("status") == "success" for tc in t.get("tool_calls", []))
                            has_error = has_tools and any(tc.get("status") == "error" for tc in t.get("tool_calls", []))
                            
                            if has_error:
                                icon = "❌"
                            elif all_success:
                                icon = "✅"
                            else:
                                icon = "🔄"
                            
                            thought = t.get("thought", "")
                            thought_display = thought[:60] + "..." if len(thought) > 60 else thought
                            if not thought_display:
                                thought_display = f"Step {t['step']}"
                            
                            st.markdown(f"**Step {t['step']}** {icon}")
                            st.caption(thought_display)
                            
                            for tc in t.get("tool_calls", []):
                                tc_icon = "✅" if tc.get("status") == "success" else "❌" if tc.get("status") == "error" else "⏳"
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{tc_icon} `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
                
                db.add_message(conv_id, "assistant", response, {"type": "agent_trace", "traces": traces})
                st.rerun()
                
            except Exception as e:
                error_msg = f"Agent error: {str(e)}"
                st.error(error_msg)
                db.add_message(conv_id, "assistant", error_msg)
                st.rerun()
    
    # Normal Chat
    else:
        db.add_message(conv_id, "user", prompt)
        
        with st.chat_message("assistant"):
            ph = st.empty()
            client = get_or_create_client()
            
            api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in messages:
                if m["role"] in ("user", "assistant"):
                    api_msgs.append({"role": m["role"], "content": m.get("content", "")})
            api_msgs.append({"role": "user", "content": prompt})
            
            full = []
            def on_chunk(chunk):
                full.append(chunk)
                ph.markdown(''.join(full) + "▌")
            
            try:
                result = client.chat(api_msgs, model=st.session_state.selected_model, stream=True, on_chunk=on_chunk)
                text = result.get("content", "")
                
                if not text or not text.strip():
                    ph.empty()
                    with st.spinner("Retrying..."):
                        result2 = client.chat(api_msgs, model=st.session_state.selected_model, stream=False)
                        text = result2.get("content", "")
                
                if text and text.strip():
                    ph.markdown(text)
                    response = text
                else:
                    ph.markdown("I received an empty response. The AI service may be temporarily unavailable. Please try again.")
                    response = "Empty response from API."
                    
            except Exception as e:
                ph.markdown(f"Error: {e}")
                response = f"Error: {e}"
        
        db.add_message(conv_id, "assistant", response)
        st.rerun()
