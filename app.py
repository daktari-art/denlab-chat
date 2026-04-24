"""
DenLab Chat - Kimi-inspired Clean UI with Multi-Provider AI
Enhanced with Memory, Cache, Tool Routing, and Branching.
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

from client import MultiProviderClient, get_client, ContentGuardrails
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
        'About': 'DenLab Chat - Advanced AI Assistant with Memory'
    }
)

# ============ SAFE SYSTEM PROMPT ============
SYSTEM_PROMPT = """You are DenLab, an advanced AI research assistant with tool-use capabilities and persistent memory.

Guidelines:
1. Be helpful, accurate, and thorough in your responses
2. Use available tools when they would improve the answer
3. Remember previous conversations and reference them when relevant
4. Provide clear explanations with examples when helpful
5. Break down complex tasks into steps
6. Write clean, well-documented code when requested
7. Research topics thoroughly using search when current information is needed
8. Respect user autonomy and provide factual information

Available tools:
- web_search: Search the live web for current information
- deep_research: Multi-hop research across sources
- execute_code: Run Python code in sandboxed environment
- fetch_url: Scrape specific web pages
- read_file: Read uploaded file contents
- write_file: Save generated content to files
- analyze_image: Analyze and describe uploaded images in detail

You have memory of past conversations. Use this to provide personalized, context-aware responses."""

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
        "auto_route": True,  # New: auto-enable agent for complex queries
        "show_memory_context": False,  # New: show memory in UI
        "current_branch": None,  # New: conversation branching
        "cache_enabled": True,  # New: response caching
        "memory_enabled": True,  # New: memory system
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

# ============ CLIENT WITH FEATURES ============
def get_enhanced_client():
    """Get client with cache and memory enabled."""
    return get_client(
        enable_cache=st.session_state.get("cache_enabled", True),
        enable_memory=st.session_state.get("memory_enabled", True)
    )

# ============ UTILITY FUNCTIONS ============

def format_message_content(content: str) -> str:
    """Format message content with code blocks and markdown."""
    if not content:
        return ""
    
    content = html_module.escape(content)
    
    code_pattern = r'```(\w*)\n(.*?)```'
    def replace_code(match):
        lang = match.group(1) or "text"
        code = html_module.escape(html_module.unescape(match.group(2)))
        return f'<div style="background:#f6f8fa;border:1px solid #e1e4e8;border-radius:10px;margin:8px 0;overflow:hidden;"><div style="display:flex;justify-content:space-between;align-items:center;background:#f0f0f0;padding:6px 12px;border-bottom:1px solid #e1e4e8;font-size:11px;color:#666;"><span>{lang}</span><span style="cursor:pointer;" onclick="navigator.clipboard.writeText(document.getElementById(\'code_{id}\').innerText)">📋 Copy</span></div><pre style="margin:0;padding:14px;overflow-x:auto;"><code id="code_{id}" style="background:transparent;padding:0;font-size:13px;line-height:1.5;">{code}</code></pre></div>'
    
    import uuid
    content = re.sub(code_pattern, replace_code, content, flags=re.DOTALL)
    content = re.sub(r'`([^`]+)`', r'<code style="background:#f0f0f0;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:13px;color:#10a37f;">\1</code>', content)
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong style="font-weight:600;color:#222;">\1</strong>', content)
    content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
    content = content.replace('\n', '<br>')
    
    return content

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
    try:
        from features.vision import VisionAnalyzer
        analyzer = VisionAnalyzer()
        
        if file_key not in st.session_state.uploaded_files:
            return json.dumps({"success": False, "error": "Image not found"})
        
        img_data = st.session_state.uploaded_files[file_key]
        if img_data.get("type") != "image":
            return json.dumps({"success": False, "error": "File is not an image"})
        
        result = analyzer.analyze(img_data["bytes"], prompt=prompt, model="gemini")
        return json.dumps({"success": True, "analysis": result})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


TOOLS_REGISTRY = {
    "web_search": {"func": web_search, "description": "Search the web", "params": {"query": {"type": "string", "description": "Search query"}}},
    "deep_research": {"func": deep_research, "description": "Deep research", "params": {"topic": {"type": "string", "description": "Research topic"}}},
    "execute_code": {"func": execute_code, "description": "Run Python code", "params": {"code": {"type": "string", "description": "Python code"}}},
    "fetch_url": {"func": fetch_url, "description": "Fetch URL content", "params": {"url": {"type": "string", "description": "URL to fetch"}}},
    "read_file": {"func": read_file, "description": "Read file", "params": {"path": {"type": "string", "description": "File path"}}},
    "write_file": {"func": write_file, "description": "Write file", "params": {"path": {"type": "string", "description": "File path"}, "content": {"type": "string", "description": "Content"}}},
    "analyze_image": {"func": analyze_image, "description": "Analyze image", "params": {"file_key": {"type": "string", "description": "File key"}, "prompt": {"type": "string", "description": "Analysis prompt"}}},
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


# ============ AGENT EXECUTION ============

def run_agent_task(prompt: str, model: str, progress_placeholder, user_id: str = None) -> Dict[str, Any]:
    client = get_enhanced_client()
    traces = []
    max_steps = 12
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nYou have tools available. Use them when needed. Think step by step."},
        {"role": "user", "content": prompt}
    ]
    
    for step in range(1, max_steps + 1):
        progress_placeholder.markdown(f"""
        <div class="agent-progress-container">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <span>🤖</span>
                <span>Step {step}/{max_steps}</span>
                <span style="width:7px;height:7px;border-radius:50%;background:#f59e0b;display:inline-block;"></span>
            </div>
            <div style="height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden;margin-bottom:10px;">
                <div style="height:100%;width:{(step/max_steps)*100}%;background:linear-gradient(90deg,#10a37f,#34d399);border-radius:2px;"></div>
            </div>
            <div style="font-size:12px;color:#666;">Thinking...</div>
        </div>
        """, unsafe_allow_html=True)
        
        response = client.chat(messages, model=model, tools=get_tool_schema(), user_id=user_id)
        
        if response.get("guardrail_triggered"):
            return {"content": response["content"], "traces": traces}
        
        content = response.get("content") or ""
        tool_calls_raw = response.get("tool_calls") or []
        provider = response.get("provider", "unknown")
        
        trace = {
            "step": step,
            "thought": content[:200] if content else f"Step {step}",
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
            
            tool_summary = " ".join([f"{'✓' if t['status'] == 'success' else '✗'} {t['name']}" for t in trace["tool_calls"]])
            
            progress_placeholder.markdown(f"""
            <div class="agent-progress-container">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span>🤖</span>
                    <span>Step {step}/{max_steps}</span>
                    <span style="color:#10a37f;">{tool_summary}</span>
                </div>
                <div style="height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden;margin-bottom:10px;">
                    <div style="height:100%;width:{(step/max_steps)*100}%;background:linear-gradient(90deg,#10a37f,#34d399);border-radius:2px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            follow_up = client.chat(messages, model=model, user_id=user_id)
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
                return {"content": follow_content or "Task completed.", "traces": traces}
            else:
                messages.append({"role": "assistant", "content": follow_content or "Continuing..."})
        else:
            trace["response"] = content
            traces.append(trace)
            progress_placeholder.markdown(f"""
            <div class="agent-progress-container">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span>✓</span>
                    <span>Complete</span>
                </div>
                <div style="height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden;">
                    <div style="height:100%;width:100%;background:#10a37f;border-radius:2px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            return {"content": content or "Task completed.", "traces": traces}
    
    final_content = traces[-1].get("response", "") if traces else ""
    if not final_content:
        final_content = "Maximum steps reached.\n\n" + "\n".join([f"Step {t['step']}: {t['thought']}" for t in traces])
    
    return {"content": final_content, "traces": traces}


# ============ AUTHENTICATION UI ============

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div style="max-width:400px;margin:0 auto;padding:40px 24px;">', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;font-size:22px;font-weight:700;margin-bottom:24px;color:#111;">DenLab Chat</div>', unsafe_allow_html=True)
        
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
        
        # Advanced settings
        with st.expander("⚙️ Advanced Settings"):
            st.session_state.cache_enabled = st.toggle("Response Cache", value=st.session_state.cache_enabled)
            st.session_state.memory_enabled = st.toggle("Memory System", value=st.session_state.memory_enabled)
            st.session_state.auto_route = st.toggle("Auto Route Queries", value=st.session_state.auto_route)
            st.session_state.show_memory_context = st.toggle("Show Memory Context", value=st.session_state.show_memory_context)
            
            if st.button("Clear Cache", use_container_width=True):
                client = get_enhanced_client()
                client.clear_cache()
                st.success("Cache cleared!")
            
            if st.button("Clear Memory", use_container_width=True):
                client = get_enhanced_client()
                client.clear_memory(st.session_state.current_user["username"])
                st.success("Memory cleared!")
        
        # Cache stats
        try:
            client = get_enhanced_client()
            cache_stats = client.get_cache_stats()
            if cache_stats.get("enabled", True):
                st.caption(f"📦 Cache: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 100)} entries")
        except:
            pass


def show_settings():
    st.markdown("## Settings")
    
    user = st.session_state.current_user
    auth = get_auth_manager()
    
    tab1, tab2, tab3, tab4 = st.tabs(["Account", "Chat", "Memory", "Danger Zone"])
    
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
        
        model = st.selectbox("Default Model", ["openai", "claude", "gemini", "llama", "deepseek"], index=0)
        stream = st.toggle("Stream Responses", value=True)
        
        st.markdown("### Feature Toggles")
        st.session_state.cache_enabled = st.toggle("Enable Response Cache", value=st.session_state.cache_enabled)
        st.session_state.memory_enabled = st.toggle("Enable Memory System", value=st.session_state.memory_enabled)
        st.session_state.auto_route = st.toggle("Auto-enable Agent for Complex Queries", value=st.session_state.auto_route)
        
        if st.button("Save Settings", type="primary"):
            auth.update_settings(st.session_state.user_token, {
                "default_model": model,
                "stream_responses": stream,
                "cache_enabled": st.session_state.cache_enabled,
                "memory_enabled": st.session_state.memory_enabled,
                "auto_route": st.session_state.auto_route,
            })
            st.success("Settings saved!")
    
    with tab3:
        st.markdown("### Memory Management")
        st.info("DenLab remembers previous conversations to provide personalized responses.")
        
        if st.button("Clear Working Memory", type="secondary"):
            client = get_enhanced_client()
            client.clear_memory(st.session_state.current_user["username"])
            st.success("Working memory cleared!")
        
        if st.button("View Memory Stats", type="secondary"):
            st.info("Memory stats will appear here after some conversations.")
    
    with tab4:
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
    user = st.session_state.current_user
    db = get_chat_db(user["username"])
    
    with st.sidebar:
        st.markdown("""
        <div style="border-bottom: 1px solid #222; padding-bottom: 12px; margin-bottom: 12px;">
            <h1 style="font-size: 16px; margin: 0; color: #fff; font-weight: 700;">DenLab Chat</h1>
            <p style="font-size: 11px; color: #666; margin: 4px 0 0 0;">Enhanced AI with Memory</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("+ New Chat", use_container_width=True, type="primary"):
            conv_id = db.create_conversation(model=st.session_state.get("selected_model", "openai"))
            st.session_state.current_conversation_id = conv_id
            st.rerun()
        
        st.divider()
        
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Model</p>', unsafe_allow_html=True)
        
        model_names = list(MODELS.keys())
        model_values = list(MODELS.values())
        current_model = st.session_state.get("selected_model", "openai")
        idx = model_values.index(current_model) if current_model in model_values else 0
        choice = st.selectbox("Model", model_names, index=idx, label_visibility="collapsed")
        st.session_state.selected_model = MODELS[choice]
        
        st.divider()
        
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Agent Mode</p>', unsafe_allow_html=True)
        
        agent_col1, agent_col2 = st.columns([3, 1])
        with agent_col1:
            st.markdown("""
            <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:20px;font-size:12px;color:#166534;font-weight:500;margin-top:4px;">
                <div style="width:6px;height:6px;background:#10a37f;border-radius:50%;animation:pulse 1.5s infinite;"></div>
                <span>Agent</span>
            </div>
            """, unsafe_allow_html=True)
        with agent_col2:
            agent_mode = st.toggle("", value=st.session_state.agent_mode, label_visibility="collapsed", key="agent_toggle")
            st.session_state.agent_mode = agent_mode
        
        if st.session_state.agent_mode:
            st.caption("Autonomous tool-use enabled")
        
        st.divider()
        
        st.markdown('<p style="font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 6px;">Conversations</p>', unsafe_allow_html=True)
        
        conversations = db.get_conversations()
        
        if not conversations:
            st.caption("No conversations yet")
        else:
            for conv in conversations[:15]:
                conv_id = conv["id"]
                title = conv.get("title", "Untitled")
                is_active = conv_id == st.session_state.get("current_conversation_id")
                
                btn_label = f"{html_module.escape(title[:24])}{'...' if len(title) > 24 else ''}"
                
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    if st.button(btn_label, key=f"conv_{conv_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state.current_conversation_id = conv_id
                        st.rerun()
                with col2:
                    if st.button("🗑", key=f"del_{conv_id}", help="Delete"):
                        db.delete_conversation(conv_id)
                        if st.session_state.get("current_conversation_id") == conv_id:
                            remaining = db.get_conversations()
                            st.session_state.current_conversation_id = remaining[0]["id"] if remaining else None
                        st.rerun()
        
        st.divider()
        
        current_conv = st.session_state.get("current_conversation_id")
        if current_conv:
            if st.button("Export Chat", use_container_width=True):
                export_data = db.export_conversation(current_conv)
                conv = db.get_conversation(current_conv)
                title = conv.get("title", "chat") if conv else "chat"
                st.download_button("Download", export_data, f"denlab_{title.replace(' ', '_')}.md", use_container_width=True)
        
        st.divider()
        st.caption("🧠 Memory enabled • ⚡ Cache enabled")


# ============ MESSAGE ACTIONS ============

def render_message_actions(msg_idx: int, content: str, msg_type: str = "text"):
    cols = st.columns([1, 1, 1, 1, 1, 20])
    
    with cols[0]:
        if st.button("📋", key=f"act_copy_{msg_idx}", help="Copy"):
            st.toast("Copied!")
    
    with cols[1]:
        if st.button("🔊", key=f"act_speak_{msg_idx}", help="Text to speech"):
            try:
                audio_url = f"https://gen.pollinations.ai/audio/{requests.utils.quote(content[:500])}?voice=nova"
                st.audio(audio_url, format='audio/mp3')
            except:
                st.toast("Audio unavailable")
    
    with cols[2]:
        if st.button("🔄", key=f"act_regen_{msg_idx}", help="Regenerate"):
            st.session_state.messages = st.session_state.messages[:msg_idx]
            st.rerun()
    
    with cols[3]:
        if msg_type == "text":
            st.download_button("⬇️", content, f"msg_{msg_idx}.md", "text/markdown", key=f"act_dl_{msg_idx}", help="Download")
    
    with cols[4]:
        if st.button("👍", key=f"act_like_{msg_idx}", help="Helpful"):
            st.toast("Thanks for the feedback!")


# ============ MAIN APP ============

# Apply CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #f5f5f5 !important; }
    .main > div { max-width: 800px; margin: 0 auto; padding: 0 20px 160px 20px; }
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #222222 !important; }
    .stChatMessage { background: transparent !important; }
    [data-testid="stChatMessage"][data-testid*="user"] > div:first-child > div:first-child,
    [data-testid="stChatMessage"][data-testid*="assistant"] > div:first-child > div:first-child {
        background: #ffffff !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    }
    .stChatInput { position: fixed !important; bottom: 24px !important; left: 50% !important; transform: translateX(-50%) !important; width: calc(100% - 320px) !important; max-width: 760px !important; background: #ffffff !important; border: 1px solid #e0e0e0 !important; border-radius: 24px !important; box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important; z-index: 1000 !important; }
    .stChatInput button { background: #10a37f !important; border-radius: 50% !important; }
    h1 { font-size: 20px !important; font-weight: 700 !important; }
    p { color: #333 !important; font-size: 14px !important; line-height: 1.7 !important; }
    pre { background: #f6f8fa !important; border-radius: 10px !important; padding: 14px !important; }
    code { background: #f0f0f0 !important; padding: 2px 6px !important; border-radius: 4px !important; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .agent-progress-container { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 14px 16px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# Check authentication
if not st.session_state.current_user:
    show_login_page()
    st.stop()

if st.session_state.show_settings:
    show_user_menu()
    show_settings()
    st.stop()

show_user_menu()

conv_id = ensure_conversation()

# Show sidebar
show_sidebar()

# File upload
st.file_uploader(
    "Attach file",
    type=["txt", "py", "js", "ts", "html", "css", "json", "md", "csv", "xml", "yaml", "yml",
          "sh", "bash", "c", "cpp", "h", "hpp", "java", "kt", "swift", "rs", "go", "rb", "php", "sql",
          "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "pdf"],
    accept_multiple_files=False,
    label_visibility="collapsed",
    key=f"prompt_uploader_{st.session_state.uploader_key}"
)

# Handle file upload
if st.session_state.get("pending_upload") and st.session_state.get("processing_upload"):
    fobj = st.session_state.pending_upload
    fname = fobj.name
    fkey = f"{datetime.now().strftime('%H%M%S')}_{fname}"
    try:
        fb = fobj.read()
        if fobj.type and fobj.type.startswith("image/"):
            st.session_state.uploaded_files[fkey] = {"type": "image", "name": fname, "bytes": fb, "mime": fobj.type}
            db = get_chat_db(st.session_state.current_user["username"])
            db.add_message(conv_id, "user", f"📎 {fname}", {"type": "image_upload", "file_key": fkey})
            try:
                from features.vision import VisionAnalyzer
                analyzer = VisionAnalyzer()
                analysis = analyzer.analyze(fb, prompt="Describe this image in detail.", model="gemini")
                db.add_message(conv_id, "assistant", f"**📎 {fname}**\n\n{analysis}")
            except:
                db.add_message(conv_id, "assistant", f"**📎 {fname}** received.")
        else:
            txt = fb.decode('utf-8', errors='ignore')
            st.session_state.uploaded_files[fkey] = {"type": "text", "name": fname, "content": txt, "size": len(txt)}
            db = get_chat_db(st.session_state.current_user["username"])
            db.add_message(conv_id, "user", f"📎 {fname}", {"type": "file", "file_key": fkey})
            db.add_message(conv_id, "assistant", f"**📎 {fname}** loaded ({len(txt)} chars).")
    except Exception as e:
        st.error(f"Upload error: {e}")
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# Load and display messages
db = get_chat_db(st.session_state.current_user["username"])
conv = db.get_conversation(conv_id) if conv_id else None
messages = conv.get("messages", []) if conv else []

# Welcome screen
visible_messages = [m for m in messages if m.get("role") != "system"]
if not visible_messages:
    st.markdown("""
    <div style="text-align:center;padding:80px 20px 40px;">
        <div style="font-size:36px;margin-bottom:16px;">🧠</div>
        <div style="font-size:22px;font-weight:700;color:#111;margin-bottom:8px;">DenLab Chat</div>
        <div style="font-size:13px;color:#888;margin-bottom:40px;">Enhanced AI with Memory & Tools</div>
        <div style="font-size:13px;color:#666;line-height:2.2;">
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/imagine</code> — Generate images</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/research</code> — Deep web research</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/code</code> — Generate & execute Python</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/analyze</code> — Analyze uploaded files</div>
            <div><code style="background:#f0f0f0;padding:3px 8px;border-radius:4px;font-size:12px;color:#10a37f;">/audio</code> — Text to speech</div>
        </div>
        <div style="margin-top:40px;font-size:11px;color:#aaa;">
            🧠 Memory enabled • ⚡ Cache enabled • 🤖 Agent mode available
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
        elif mtype == "image_upload":
            fk = meta.get("file_key")
            if fk and fk in st.session_state.uploaded_files:
                st.image(st.session_state.uploaded_files[fk]["bytes"], use_container_width=True)
        elif mtype == "file":
            st.markdown(content)
            fk = meta.get("file_key")
            if fk and fk in st.session_state.uploaded_files:
                with st.expander("Preview"):
                    st.code(st.session_state.uploaded_files[fk]["content"][:3000])
        elif mtype == "agent_trace":
            st.markdown(content)
            if meta.get("traces"):
                with st.expander("Execution Trace", expanded=False):
                    for t in meta["traces"]:
                        st.markdown(f"**Step {t['step']}** {'✅' if all(tc.get('status') == 'success' for tc in t.get('tool_calls', [])) else '🔄'}")
                        for tc in t.get("tool_calls", []):
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{'✅' if tc.get('status') == 'success' else '❌'} `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
        else:
            st.markdown(content)
        
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
                    client = get_enhanced_client()
                    url = client.generate_image(desc, w, h)
                    st.image(url, caption=desc, use_container_width=True)
            
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
                    out = f"## Research: {topic}\n\n"
                    for i, f in enumerate(data['findings'][:5], 1):
                        out += f"{i}. **{f['title']}** — {f['content'][:150]}...\n\n"
                    st.markdown(out)
            
            db.add_message(conv_id, "assistant", out, {"type": "research"})
            st.rerun()
    
    # /code
    elif prompt.lower().startswith("/code"):
        task = prompt[5:].strip()
        if task:
            db.add_message(conv_id, "user", f"💻 {task}")
            
            with st.chat_message("assistant"):
                with st.status("Coding...", expanded=True) as s:
                    client = get_enhanced_client()
                    code_prompt = f"Write Python to: {task}\nReturn ONLY the code inside a markdown code block."
                    resp = client.chat([
                        {"role": "system", "content": "Expert Python programmer."},
                        {"role": "user", "content": code_prompt}
                    ], model=st.session_state.selected_model, user_id=st.session_state.current_user["username"])
                    
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
                        client = get_enhanced_client()
                        analysis = client.chat([
                            {"role": "system", "content": "Senior code reviewer."},
                            {"role": "user", "content": f"Analyze: {lf['name']}\n```\n{lf['content'][:4000]}\n```"}
                        ], model=st.session_state.selected_model, user_id=st.session_state.current_user["username"])
                        analysis_text = analysis.get("content", "Analysis failed.")
                        st.markdown(analysis_text)
                        db.add_message(conv_id, "assistant", analysis_text)
                    elif lf["type"] == "image":
                        try:
                            from features.vision import VisionAnalyzer
                            analyzer = VisionAnalyzer()
                            analysis = analyzer.analyze(lf["bytes"], model="gemini")
                            st.markdown(analysis)
                            db.add_message(conv_id, "assistant", analysis)
                        except Exception as e:
                            st.error(f"Vision error: {e}")
            st.rerun()
        else:
            db.add_message(conv_id, "user", "🔍 /analyze")
            db.add_message(conv_id, "assistant", "No file uploaded.")
            st.rerun()
    
    # /audio
    elif prompt.lower().startswith("/audio"):
        text = prompt[6:].strip()
        if text:
            db.add_message(conv_id, "user", f"🔊 {text[:50]}")
            with st.chat_message("assistant"):
                with st.spinner("Generating audio..."):
                    client = get_enhanced_client()
                    url = client.generate_audio(text)
                    st.audio(url, format='audio/mp3')
            db.add_message(conv_id, "assistant", url, {"type": "audio"})
            st.rerun()
    
    # Agent Mode
    elif st.session_state.agent_mode:
        db.add_message(conv_id, "user", prompt)
        
        with st.chat_message("assistant"):
            progress_ph = st.empty()
            
            try:
                result = run_agent_task(prompt, st.session_state.selected_model, progress_ph, st.session_state.current_user["username"])
                
                response = result.get("content", "")
                traces = result.get("traces", [])
                
                if response:
                    st.markdown(response)
                else:
                    st.markdown("The agent completed but returned no output.")
                
                if traces:
                    with st.expander("Execution Trace", expanded=False):
                        for t in traces:
                            st.markdown(f"**Step {t['step']}** {'✅' if all(tc.get('status') == 'success' for tc in t.get('tool_calls', [])) else '🔄'}")
                            for tc in t.get("tool_calls", []):
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{'✅' if tc.get('status') == 'success' else '❌'} `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
                
                db.add_message(conv_id, "assistant", response, {"type": "agent_trace", "traces": traces})
                st.rerun()
                
            except Exception as e:
                error_msg = f"Agent error: {str(e)}"
                st.error(error_msg)
                db.add_message(conv_id, "assistant", error_msg)
                st.rerun()
    
    # Normal Chat with Auto-Routing
    else:
        db.add_message(conv_id, "user", prompt)
        
        with st.chat_message("assistant"):
            ph = st.empty()
            client = get_enhanced_client()
            
            # Auto-route complex queries
            if st.session_state.auto_route:
                route_result = client.route_query(prompt, ["web_search", "execute_code", "read_file", "fetch_url", "analyze_image"])
                if route_result["needs_agent"] and route_result["confidence"] > 0.7:
                    st.info(f"🔄 Detected intent: {route_result['primary_intent']}. Switching to agent mode...")
                    st.session_state.agent_mode = True
                    time.sleep(0.5)
                    st.rerun()
            
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
                result = client.chat(api_msgs, model=st.session_state.selected_model, stream=True, on_chunk=on_chunk, user_id=st.session_state.current_user["username"])
                text = result.get("content", "")
                
                # Show memory indicator if context was used
                if st.session_state.show_memory_context and result.get("provider") == "cache":
                    st.caption("⚡ Response from cache")
                elif st.session_state.show_memory_context:
                    st.caption("🧠 Generated with memory")
                
                if not text or not text.strip():
                    result2 = client.chat(api_msgs, model=st.session_state.selected_model, stream=False, user_id=st.session_state.current_user["username"])
                    text = result2.get("content", "")
                
                if text and text.strip():
                    ph.markdown(text)
                    response = text
                else:
                    ph.markdown("I received an empty response. Please try again.")
                    response = "Empty response from API."
                    
            except Exception as e:
                ph.markdown(f"Error: {e}")
                response = f"Error: {e}"
        
        db.add_message(conv_id, "assistant", response)
        st.rerun()
