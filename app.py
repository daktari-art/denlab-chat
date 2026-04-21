"""
DenLab Chat - Multi-Provider AI Chat with User Accounts & Persistent History
Streamlit application with guardrails, fallback providers, and styled UI.
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

# Add current directory to path for imports
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
        'About': 'DenLab Chat - Free AI with multi-provider fallback'
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

# ============ CUSTOM CSS ============
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main background */
    .stApp {
        background-color: #0d0d0d !important;
    }
    
    /* Chat message containers */
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        max-width: 85%;
    }
    
    .chat-message.user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: auto;
        margin-right: 0;
    }
    
    .chat-message.assistant {
        background: #1e1e2e;
        border: 1px solid #333;
        margin-left: 0;
        margin-right: auto;
    }
    
    .chat-message.system {
        background: #2d2d44;
        border: 1px solid #444;
        margin: 0 auto;
        text-align: center;
        font-size: 0.85em;
        color: #aaa;
    }
    
    /* Avatar circles */
    .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
    }
    
    .avatar-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .avatar-assistant {
        background: #f59e0b;
    }
    
    /* Code box styling */
    .code-box {
        background: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        position: relative !important;
        overflow-x: auto !important;
    }
    
    .code-box pre {
        margin: 0 !important;
        color: #c9d1d9 !important;
        font-family: 'Courier New', monospace !important;
        font-size: 13px !important;
        line-height: 1.5 !important;
    }
    
    .code-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #161b22;
        padding: 6px 12px;
        border-radius: 8px 8px 0 0;
        border-bottom: 1px solid #30363d;
        font-size: 12px;
        color: #8b949e;
    }
    
    .copy-btn {
        background: #21262d;
        border: 1px solid #30363d;
        border-radius: 6px;
        color: #c9d1d9;
        padding: 4px 10px;
        font-size: 11px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .copy-btn:hover {
        background: #30363d;
        border-color: #8b949e;
    }
    
    /* Instruction/note box */
    .instruction-box {
        background: linear-gradient(135deg, #1a1f2e 0%, #162032 100%);
        border-left: 4px solid #3b82f6;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
        color: #e2e8f0;
    }
    
    .instruction-box .title {
        color: #60a5fa;
        font-weight: 600;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Tip box */
    .tip-box {
        background: linear-gradient(135deg, #1a2e1a 0%, #162316 100%);
        border-left: 4px solid #22c55e;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
        color: #e2e8f0;
    }
    
    .tip-box .title {
        color: #4ade80;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    /* Warning box */
    .warning-box {
        background: linear-gradient(135deg, #2e1a1a 0%, #231616 100%);
        border-left: 4px solid #ef4444;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
        color: #e2e8f0;
    }
    
    .warning-box .title {
        color: #f87171;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    /* Provider badge */
    .provider-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 10px;
        font-weight: 500;
        margin-left: 8px;
    }
    
    .provider-pollinations {
        background: #7c3aed;
        color: #ddd6fe;
    }
    
    .provider-ails {
        background: #0891b2;
        color: #cffafe;
    }
    
    /* Status indicator */
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }
    
    .status-online {
        background: #22c55e;
        box-shadow: 0 0 6px #22c55e;
    }
    
    .status-offline {
        background: #ef4444;
    }
    
    /* Auth forms */
    .auth-container {
        max-width: 420px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    .auth-title {
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Sidebar conversation list */
    .conv-item {
        padding: 0.5rem 0.75rem;
        border-radius: 8px;
        margin-bottom: 4px;
        cursor: pointer;
        transition: background 0.2s;
        font-size: 13px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .conv-item:hover {
        background: #2d2d44;
    }
    
    .conv-item.active {
        background: #3b3b5c;
        border-left: 3px solid #667eea;
    }
    
    /* Progress steps */
    .progress-step {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 0.5rem 0;
        opacity: 0.6;
    }
    
    .progress-step.active {
        opacity: 1;
    }
    
    .progress-step.completed {
        opacity: 1;
    }
    
    .step-number {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #333;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        flex-shrink: 0;
    }
    
    .step-number.completed {
        background: #22c55e;
        color: white;
    }
    
    .step-number.active {
        background: #667eea;
        color: white;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1a2e;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #3b3b5c;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    /* Chat input styling */
    .stChatInput {
        background: #1a1a1a !important;
        border: 1px solid #333333 !important;
        border-radius: 24px !important;
    }
    
    .stChatInput textarea {
        color: #ffffff !important;
    }
    
    .stChatInput textarea::placeholder {
        color: #888888 !important;
    }
    
    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #111111 !important;
    }
    
    /* Chat messages */
    [data-testid="stChatMessageContent"] {
        color: #e6e6e6 !important;
        font-size: 15px;
        line-height: 1.6;
    }
    
    /* User message bubble */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #1a1a1a !important;
        border-radius: 12px !important;
    }
    
    /* Code blocks */
    pre {
        background-color: #161616 !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 8px !important;
    }
    
    code {
        background-color: #1a1a1a !important;
        color: #e8e8e8 !important;
    }
    
    /* Buttons */
    .stButton button {
        transition: all 0.2s ease !important;
    }
    
    /* Status colors for agent */
    .agent-step-success { color: #22c55e !important; }
    .agent-step-error { color: #ef4444 !important; }
    .agent-step-running { color: #3b82f6 !important; }
</style>
""", unsafe_allow_html=True)


# ============ PWA ============
st.markdown("""
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#0d0d0d">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    
    # Validate token if present
    if st.session_state.user_token:
        auth = get_auth_manager()
        user = auth.validate_token(st.session_state.user_token)
        if not user:
            st.session_state.user_token = None
            st.session_state.current_user = None

init_session()


# ============ UTILITY FUNCTIONS ============

def format_message_content(content: str) -> str:
    """Format message content with styled code boxes. Returns HTML string."""
    if not content:
        return ""
    
    content = html_module.escape(content)
    
    # Convert code blocks
    code_pattern = r'```(\w*)\n(.*?)```'
    def replace_code(match):
        lang = match.group(1) or "text"
        code = html_module.escape(html_module.unescape(match.group(2)))
        return f'<div class="code-box"><div class="code-header"><span>{lang}</span></div><pre><code>{code}</code></pre></div>'
    
    content = re.sub(code_pattern, replace_code, content, flags=re.DOTALL)
    content = re.sub(r'`([^`]+)`', r'<code style="background:#2d2d44;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:13px;color:#e2e8f0;">\1</code>', content)
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
    content = content.replace('\n', '<br>')
    
    return content


def get_or_create_client() -> MultiProviderClient:
    """Get or create the AI client from session state."""
    if "ai_client" not in st.session_state:
        st.session_state.ai_client = MultiProviderClient()
    return st.session_state.ai_client


def ensure_conversation() -> str:
    """Ensure user has a current conversation."""
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
    """Search the web using DuckDuckGo."""
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
    """Conduct deep multi-source research."""
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
    """Execute Python code safely."""
    try:
        import io, sys, traceback
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        try:
            exec(code, {"__builtins__": __builtins__})
            return json.dumps({
                "success": True,
                "stdout": sys.stdout.getvalue(),
                "stderr": sys.stderr.getvalue()
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        finally:
            sys.stdout, sys.stderr = old_out, old_err
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "DenLab/4.0"})
        if resp.status_code == 200:
            return json.dumps({"success": True, "content": resp.text[:5000]})
        return json.dumps({"success": False, "error": f"HTTP {resp.status_code}"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def read_file(path: str) -> str:
    """Read an uploaded file."""
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
    """Write content to file storage."""
    try:
        st.session_state.uploaded_files[path] = {
            "type": "text",
            "name": path,
            "content": content,
            "size": len(content),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps({"success": True, "path": path, "size": len(content)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# Tool registry for agent
TOOLS_REGISTRY = {
    "web_search": {"func": web_search, "description": "Search the web for current information", "params": {"query": {"type": "string", "description": "Search query"}}},
    "deep_research": {"func": deep_research, "description": "Deep research across multiple sources", "params": {"topic": {"type": "string", "description": "Research topic"}}},
    "execute_code": {"func": execute_code, "description": "Run Python code in sandboxed environment", "params": {"code": {"type": "string", "description": "Python code to execute"}}},
    "fetch_url": {"func": fetch_url, "description": "Fetch and read content from a URL", "params": {"url": {"type": "string", "description": "URL to fetch"}}},
    "read_file": {"func": read_file, "description": "Read uploaded file contents", "params": {"path": {"type": "string", "description": "File path or key"}}},
    "write_file": {"func": write_file, "description": "Write content to a file", "params": {"path": {"type": "string", "description": "File path"}, "content": {"type": "string", "description": "Content to write"}}},
}


def get_tool_schema() -> List[Dict]:
    """Get OpenAI-compatible tool schema."""
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
    """Execute a tool call and return result."""
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
    """Show login/register forms."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">🧪 DenLab Chat</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Sign In", "Create Account"])
        
        with tab1:
            with st.form("login_form"):
                st.markdown("**Welcome back!**")
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
                        result = auth.register(
                            new_username, 
                            new_password,
                            new_display or None
                        )
                        if result["success"]:
                            st.session_state.user_token = result["token"]
                            st.session_state.current_user = result["user"]
                            st.success("Account created successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(result["error"])
        
        st.markdown('<p style="text-align:center;color:#666;font-size:12px;margin-top:2rem;">No email required. Your data stays on this device.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def show_user_menu():
    """Show user menu in sidebar."""
    user = st.session_state.current_user
    
    with st.sidebar:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:10px;background:#1e1e2e;border-radius:10px;margin-bottom:10px;">
            <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;align-items:center;justify-content:center;font-weight:bold;color:white;">
                {user['display_name'][0].upper()}
            </div>
            <div>
                <div style="font-weight:600;color:#e2e8f0;">{html_module.escape(user['display_name'])}</div>
                <div style="font-size:11px;color:#888;">@{html_module.escape(user['username'])}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚙️ Settings", use_container_width=True):
                st.session_state.show_settings = True
                st.rerun()
        with col2:
            if st.button("🚪 Sign Out", use_container_width=True):
                auth = get_auth_manager()
                auth.logout(st.session_state.user_token)
                for key in ['user_token', 'current_user', 'current_conversation_id']:
                    if key in st.session_state:
                        st.session_state[key] = None
                st.rerun()
        
        st.divider()


def show_settings():
    """Show settings panel."""
    st.markdown("## ⚙️ Settings")
    
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
    
    if st.button("← Back to Chat"):
        st.session_state.show_settings = False
        st.rerun()


# ============ SIDEBAR ============

def show_sidebar():
    """Show the sidebar with conversation list and controls."""
    user = st.session_state.current_user
    db = get_chat_db(user["username"])
    
    with st.sidebar:
        # New chat button
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            conv_id = db.create_conversation(model=st.session_state.get("selected_model", "openai"))
            st.session_state.current_conversation_id = conv_id
            st.rerun()
        
        st.divider()
        
        # Model selector
        st.markdown("**🤖 Model**")
        model_names = list(MODELS.keys())
        model_values = list(MODELS.values())
        current_model = st.session_state.get("selected_model", "openai")
        idx = model_values.index(current_model) if current_model in model_values else 0
        choice = st.selectbox("Model", model_names, index=idx, label_visibility="collapsed")
        st.session_state.selected_model = MODELS[choice]
        
        st.divider()
        
        # Agent mode toggle
        st.session_state.agent_mode = st.toggle("🤖 Agent Mode", value=st.session_state.agent_mode)
        if st.session_state.agent_mode:
            st.caption("Agent can search, code, fetch URLs, and manage files autonomously.")
        
        st.divider()
        
        # Conversation list
        st.markdown("**💬 Conversations**")
        
        conversations = db.get_conversations()
        
        if not conversations:
            st.caption("No conversations yet. Start chatting!")
        else:
            for conv in conversations:
                conv_id = conv["id"]
                title = conv.get("title", "Untitled")
                msg_count = len(conv.get("messages", []))
                is_active = conv_id == st.session_state.get("current_conversation_id")
                
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    btn_type = "primary" if is_active else "secondary"
                    label = f"💬 {html_module.escape(title[:30])}{'...' if len(title) > 30 else ''} ({msg_count})"
                    if st.button(label, key=f"conv_{conv_id}", use_container_width=True, type=btn_type):
                        st.session_state.current_conversation_id = conv_id
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"del_{conv_id}", help="Delete conversation"):
                        db.delete_conversation(conv_id)
                        if st.session_state.get("current_conversation_id") == conv_id:
                            remaining = db.get_conversations()
                            st.session_state.current_conversation_id = remaining[0]["id"] if remaining else None
                        st.rerun()
        
        st.divider()
        
        # Export
        current_conv = st.session_state.get("current_conversation_id")
        if current_conv:
            if st.button("📥 Export Chat", use_container_width=True):
                export_data = db.export_conversation(current_conv)
                conv = db.get_conversation(current_conv)
                title = conv.get("title", "chat") if conv else "chat"
                st.download_button(
                    "Download",
                    export_data,
                    f"denlab_{title.replace(' ', '_')}.md",
                    use_container_width=True
                )
        
        st.divider()
        
        # Upload
        uploaded = st.file_uploader(
            "Upload file",
            type=["txt", "py", "js", "html", "css", "json", "md", "csv", "yaml", "yml",
                  "java", "c", "cpp", "go", "rs", "rb", "php", "sql", "sh",
                  "png", "jpg", "jpeg", "gif", "webp", "svg", "pdf"],
            key=f"up_{st.session_state.uploader_key}",
            label_visibility="collapsed"
        )
        
        st.caption(f"v4.1 · Multi-provider fallback enabled")
        
        return uploaded


# ============ AGENT EXECUTION ============

def run_agent_task(prompt: str, model: str, progress_placeholder) -> Dict[str, Any]:
    """Execute agent task with synchronous step-by-step execution.
    
    Returns dict with 'content', 'traces'.
    """
    client = get_or_create_client()
    traces = []
    max_steps = 10
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nYou have tools available. Use them when needed. Think step by step."},
        {"role": "user", "content": prompt}
    ]
    
    for step in range(1, max_steps + 1):
        # Update progress
        progress_placeholder.markdown(f"🤖 **Step {step}** — Thinking...")
        
        # Call LLM with tools
        response = client.chat(messages, model=model, tools=get_tool_schema())
        
        # Handle guardrail block
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
            # Execute each tool call
            tool_results = []
            for tc_raw in tool_calls_raw:
                tc_result = execute_tool_call(tc_raw)
                trace["tool_calls"].append(tc_result)
                
                # Add tool result to messages
                tool_msg = {
                    "role": "tool",
                    "content": str(tc_result["result"])[:4000],
                    "tool_call_id": tc_raw.get("id", f"call_{step}")
                }
                messages.append(tool_msg)
                tool_results.append(tool_msg)
            
            # Add assistant message with tool calls
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
            
            # Show progress
            tool_summary = " · ".join([
                f"{'✅' if t['status'] == 'success' else '❌'} {t['name']}"
                for t in trace["tool_calls"]
            ])
            progress_placeholder.markdown(f"🤖 **Step {step}** — {tool_summary}")
            
            # Get follow-up after tools
            follow_up = client.chat(messages, model=model)
            follow_content = follow_up.get("content") or ""
            
            # If follow-up has no tool calls, we're done
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
            # Final answer - no tool calls
            trace["response"] = content
            traces.append(trace)
            progress_placeholder.markdown(f"✅ **Done** — {content[:100]}..." if len(content) > 100 else f"✅ **Done** — {content}")
            return {"content": content or "I completed the task.", "traces": traces}
    
    # Max steps reached
    final_content = traces[-1].get("response", "") if traces else ""
    if not final_content:
        final_content = "I reached the maximum number of steps. Here's what I accomplished:\n\n" + \
            "\n".join([f"Step {t['step']}: {t['thought']}" for t in traces])
    
    return {"content": final_content, "traces": traces}


# ============ MAIN APP ============

# Check authentication
if not st.session_state.current_user:
    show_login_page()
    st.stop()

# Show settings if requested
if st.session_state.show_settings:
    show_user_menu()
    show_settings()
    st.stop()

# Show main UI
show_user_menu()

# Ensure conversation exists
conv_id = ensure_conversation()

# Get sidebar file upload
uploaded = show_sidebar()

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
            # Add to DB
            db = get_chat_db(st.session_state.current_user["username"])
            db.add_message(conv_id, "user", f"🖼️ {fname}", {"type": "image_upload", "file_key": fkey})
            db.add_message(conv_id, "assistant", f"🖼️ **{fname}** received. Use `/analyze` to describe it.")
        else:
            txt = fb.decode('utf-8', errors='ignore')
            st.session_state.uploaded_files[fkey] = {"type": "text", "name": fname, "content": txt, "size": len(txt)}
            db = get_chat_db(st.session_state.current_user["username"])
            db.add_message(conv_id, "user", f"📎 {fname}", {"type": "file", "file_key": fkey})
            db.add_message(conv_id, "assistant", f"📄 **{fname}** loaded ({len(txt)} chars). Use `/analyze`.")
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
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 32px; margin-bottom: 12px;">🧪</div>
        <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">DenLab Chat</div>
        <div style="font-size: 14px; color: #888; margin-bottom: 32px;">Multi-provider AI with persistent history & guardrails</div>
        <div style="font-size: 13px; color: #666; line-height: 2;">
            <div>/imagine [prompt] — Generate images</div>
            <div>/research [topic] — Deep web research</div>
            <div>/code [task] — Generate & execute Python</div>
            <div>/analyze — Analyze uploaded files</div>
            <div>/audio [text] — Text to speech</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
                st.download_button("⬇️ Download", img_data, f"image_{idx}.png", mime="image/png", key=f"dlimg_{idx}")
            except:
                pass
        elif mtype == "image_upload":
            fk = meta.get("file_key")
            if fk and fk in st.session_state.uploaded_files:
                st.image(st.session_state.uploaded_files[fk]["bytes"], use_container_width=True)
            else:
                st.markdown(content)
        elif mtype == "file":
            st.markdown(content)
            fk = meta.get("file_key")
            if fk and fk in st.session_state.uploaded_files:
                with st.expander("Preview"):
                    st.code(st.session_state.uploaded_files[fk]["content"][:3000])
        elif mtype == "agent_trace":
            st.markdown(content)
            if meta.get("traces"):
                with st.expander("📊 Agent Progress", expanded=False):
                    for t in meta["traces"]:
                        st.markdown(f"**Step {t['step']}** — {t.get('thought', '')[:60]}...")
                        for tc in t.get("tool_calls", []):
                            icon = "✅" if tc.get('status') == 'success' else "❌" if tc.get('status') == 'error' else "⏳"
                            st.markdown(f"{icon} `{tc.get('name')}` — {tc.get('duration_ms', 0):.0f}ms")
        elif mtype == "audio":
            st.audio(content, format='audio/mp3')
        elif mtype == "code":
            st.markdown(content)
        elif mtype == "research":
            st.markdown(content)
        else:
            st.markdown(content)


# ============ CHAT INPUT ============
placeholder = "Message DenLab..." if not st.session_state.agent_mode else "🤖 Describe your task..."

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
                        st.download_button("Download", data, f"img_{desc[:15].replace(' ','_')}.png", mime="image/png")
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
                with st.status("🔬 Researching...", expanded=True) as s:
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
                with st.status("💻 Coding...", expanded=True) as s:
                    client = get_or_create_client()
                    code_prompt = f"Write Python to: {task}\nReturn ONLY the code inside a markdown code block."
                    resp = client.chat([
                        {"role": "system", "content": "Expert Python programmer. Return only code in markdown blocks."},
                        {"role": "user", "content": code_prompt}
                    ], model=st.session_state.selected_model)
                    
                    raw_content = resp.get("content", "")
                    # Extract code from markdown
                    code_match = re.search(r'```python\n(.*?)```', raw_content, re.DOTALL)
                    if not code_match:
                        code_match = re.search(r'```\n(.*?)```', raw_content, re.DOTALL)
                    code = code_match.group(1).strip() if code_match else raw_content.strip()
                    
                    st.code(code, language="python")
                    result = execute_code(code)
                    data = json.loads(result)
                    
                    if data.get("success"):
                        s.update(label="✅ Success", state="complete")
                        out = f"```python\n{code}\n```\n**Output:**\n```\n{data.get('stdout', '')}\n```"
                    else:
                        s.update(label="❌ Error", state="error")
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
                    else:
                        st.markdown("Image analysis requires a vision model. Upload a text file or use the vision feature.")
                        db.add_message(conv_id, "assistant", "Image analysis requires a vision model.")
            st.rerun()
        else:
            db.add_message(conv_id, "user", "🔍 /analyze")
            db.add_message(conv_id, "assistant", "No file uploaded. Upload a file first using the sidebar.")
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
                with st.spinner("🤖 Agent working..."):
                    result = run_agent_task(prompt, st.session_state.selected_model, progress_ph)
                
                response = result.get("content", "")
                traces = result.get("traces", [])
                
                # Display final response
                if response:
                    st.markdown(response)
                else:
                    st.markdown("The agent completed the task but returned no output. This may happen if the AI service is temporarily unavailable.")
                
                # Show agent progress trace
                if traces:
                    with st.expander("📊 Agent Execution Trace", expanded=False):
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
                            thought_display = thought[:80] + "..." if len(thought) > 80 else thought
                            if not thought_display:
                                thought_display = f"Step {t['step']}"
                            
                            st.markdown(f"**Step {t['step']}** {icon}")
                            st.caption(thought_display)
                            
                            for tc in t.get("tool_calls", []):
                                tc_icon = "✅" if tc.get("status") == "success" else "❌" if tc.get("status") == "error" else "⏳"
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{tc_icon} `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
                
                # Save to DB
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
            
            # Build messages for API (system + conversation history)
            api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in messages:
                if m["role"] in ("user", "assistant"):
                    api_msgs.append({"role": m["role"], "content": m.get("content", "")})
            # Add current prompt (already added to DB, so it's in messages)
            api_msgs.append({"role": "user", "content": prompt})
            
            full = []
            def on_chunk(chunk):
                full.append(chunk)
                ph.markdown(''.join(full) + "▌")
            
            try:
                # Try streaming first
                result = client.chat(api_msgs, model=st.session_state.selected_model, stream=True, on_chunk=on_chunk)
                text = result.get("content", "")
                
                # Fallback: if streaming returned empty, try non-streaming
                if not text or not text.strip():
                    ph.empty()
                    with st.spinner("Retrying with non-streaming mode..."):
                        result2 = client.chat(api_msgs, model=st.session_state.selected_model, stream=False)
                        text = result2.get("content", "")
                
                if text and text.strip():
                    ph.markdown(text)
                    response = text
                else:
                    ph.markdown("I received an empty response. The AI service may be temporarily unavailable. Please try again.")
                    response = "Empty response from API."
                    
            except Exception as e:
                ph.markdown(f"❌ Error: {e}")
                response = f"Error: {e}"
        
        db.add_message(conv_id, "assistant", response)
        st.rerun()
