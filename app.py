"""
DenLab Chat v5.3 - Clean UI with Multi-Provider AI
Enhanced with Memory, Cache, Tool Routing, Swarm Agents, and GitHub Integration.
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
import asyncio

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
        'About': 'DenLab Chat - Advanced AI Assistant with Memory & Tools'
    }
)

# ============ FIXED CSS - No overlapping chat input ============
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    
    /* Main background */
    .stApp { background-color: #f5f5f5 !important; }
    
    /* Main content area - proper padding to prevent overlap */
    .main .block-container {
        max-width: 800px !important;
        margin: 0 auto !important;
        padding: 1rem 1rem 100px 1rem !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #222222 !important;
        min-width: 260px !important;
        width: 260px !important;
    }
    
    [data-testid="stSidebar"] .block-container {
        padding: 1rem !important;
    }
    
    /* Chat messages */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
    }
    
    /* Message bubbles */
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
        background: #ffffff !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        margin: 4px 0 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    
    /* Chat input - fixed position with proper bottom spacing */
    .stChatInput {
        position: fixed !important;
        bottom: 20px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 300px) !important;
        max-width: 760px !important;
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 28px !important;
        padding: 4px 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        z-index: 999 !important;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        border: none !important;
        color: #333 !important;
        font-size: 14px !important;
        padding: 10px 0 !important;
    }
    
    .stChatInput button {
        background: #10a37f !important;
        border-radius: 50% !important;
        color: white !important;
    }
    
    /* Typography */
    h1 { font-size: 20px !important; font-weight: 700 !important; color: #111 !important; }
    p { color: #333 !important; font-size: 14px !important; line-height: 1.6 !important; }
    
    /* Code blocks */
    pre { background: #f6f8fa !important; border-radius: 10px !important; padding: 14px !important; overflow-x: auto !important; }
    code { background: #f0f0f0 !important; padding: 2px 6px !important; border-radius: 4px !important; font-size: 13px !important; }
    
    /* Agent progress */
    .agent-progress-container {
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        margin: 8px 0 !important;
    }
    
    /* Swarm progress */
    .swarm-progress-container {
        background: #f0fdf4 !important;
        border: 1px solid #bbf7d0 !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        margin: 8px 0 !important;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    header { visibility: hidden !important; }
    
    /* Animations */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
</style>
""", unsafe_allow_html=True)

# ============ SAFE SYSTEM PROMPT (No Pollinations.ai mention) ============
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
- github_get_files: List all files in a GitHub repository
- deep_research: Multi-hop research across sources
- execute_code: Run Python code in sandboxed environment
- fetch_url: Scrape specific web pages
- read_file: Read uploaded file contents
- write_file: Save generated content to files
- analyze_image: Analyze and describe uploaded images

You have memory of past conversations. Use this to provide personalized, context-aware responses."""

# ============ SWARM AGENT SYSTEM PROMPT ============
MASTER_AGENT_PROMPT = """You are the Master Agent of DenLab's Swarm system. Your role is to:
1. Analyze the user's task and break it into sub-tasks
2. Delegate each sub-task to specialized agents (Researcher, Coder, Analyst, Writer)
3. Collect results from all agents
4. Synthesize them into a coherent final response

Available sub-agents:
- Researcher: Best for web search, fact-finding, and information gathering
- Coder: Best for writing, executing, and debugging code
- Analyst: Best for data analysis, comparisons, and evaluations
- Writer: Best for composing final responses, summaries, and reports

When given a task, respond with a JSON plan like:
{"subtasks": [{"id": "1", "type": "researcher", "description": "..."}, ...]}

Then after receiving results, synthesize the final answer."""

SUB_AGENT_PROMPTS = {
    "researcher": "You are a Research Agent. Find accurate, current information. Be thorough and cite sources.",
    "coder": "You are a Code Agent. Write clean, working code. Explain your approach and show output.",
    "analyst": "You are an Analyst Agent. Compare, evaluate, and draw insights from data. Be objective.",
    "writer": "You are a Writer Agent. Synthesize information into clear, well-structured responses."
}

# ============ MODELS ============
MODELS = {
    "GPT-4o": "openai",
    "GPT-4o mini": "openai-mini",
    "Claude 3.5 Sonnet": "claude",
    "Gemini 2.0 Flash": "gemini",
    "Llama 3.3 70B": "llama",
    "Mistral Large": "mistral",
    "DeepSeek V3": "deepseek",
    "Qwen 2.5 72B": "qwen"
}

# ============ DEVELOPER CONFIGURATION (Protected) ============
DEVELOPER_USERNAME = "dennis"
DEVELOPER_PASSWORD = "yessyess"

def is_developer(username: str, password: str = None) -> bool:
    """Check if user is the developer (protected by password)."""
    if password is not None:
        return username.lower() == DEVELOPER_USERNAME and password == DEVELOPER_PASSWORD
    return username.lower() == DEVELOPER_USERNAME

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
        "auto_route": True,
        "show_memory_context": False,
        "current_branch": None,
        "cache_enabled": True,
        "memory_enabled": True,
        "agent_max_steps": 25,
        "is_developer": False,
        "swarm_results": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ============ CLIENT WITH FEATURES ============
def get_enhanced_client():
    return get_client(
        enable_cache=st.session_state.get("cache_enabled", True),
        enable_memory=st.session_state.get("memory_enabled", True)
    )

# ============ UTILITY FUNCTIONS ============

def ensure_conversation() -> str:
    user = st.session_state.current_user
    if not user:
        return None
    
    if not st.session_state.current_conversation_id:
        db = get_chat_db(user["username"])
        conv_id = db.get_or_create_default(model=st.session_state.selected_model)
        st.session_state.current_conversation_id = conv_id
    
    return st.session_state.current_conversation_id

# ============ TOOL FUNCTIONS (Same as before) ============

def web_search(query: str) -> str:
    try:
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_html=1&skip_disambig=1"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "DenLab/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            results = []
            if data.get("RelatedTopics"):
                for item in data["RelatedTopics"][:5]:
                    if isinstance(item, dict):
                        text = item.get("Text", "")
                        if text:
                            results.append({
                                "title": text[:100],
                                "snippet": text[:300],
                                "url": item.get("FirstURL", "")
                            })
            if not results:
                fallback_url = f"https://ddg-api.herokuapp.com/search?query={requests.utils.quote(query)}&limit=5"
                fb_resp = requests.get(fallback_url, timeout=10)
                if fb_resp.status_code == 200:
                    for item in fb_resp.json()[:5]:
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "url": item.get("link", "")
                        })
            return json.dumps({"success": True, "results": results, "query": query})
        return json.dumps({"success": False, "error": f"Search returned {resp.status_code}"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

def github_get_files(repo: str) -> str:
    try:
        parts = repo.replace("github.com/", "").split("/")
        if len(parts) >= 2:
            owner = parts[-2]
            repo_name = parts[-1].replace(".git", "")
        else:
            return json.dumps({"success": False, "error": "Invalid repo format"})
        
        for branch in ["main", "master"]:
            url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}?recursive=1"
            resp = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github.v3+json"})
            if resp.status_code == 200:
                data = resp.json()
                files = [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]
                return json.dumps({
                    "success": True,
                    "files": files[:100],
                    "count": len(files),
                    "repo": f"{owner}/{repo_name}",
                    "branch": branch
                })
        return json.dumps({"success": False, "error": "Could not access repo"})
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
    import io
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        safe_globals = {"__builtins__": __builtins__}
        exec(code, safe_globals)
        return json.dumps({
            "success": True,
            "stdout": sys.stdout.getvalue(),
            "stderr": sys.stderr.getvalue()
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

def fetch_url(url: str) -> str:
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "DenLab/1.0"})
        if resp.status_code == 200:
            clean = re.sub(r'<[^>]+>', ' ', resp.text[:8000])
            clean = re.sub(r'\s+', ' ', clean).strip()
            return json.dumps({"success": True, "content": clean[:5000]})
        return json.dumps({"success": False, "error": f"HTTP {resp.status_code}"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

def read_file(path: str) -> str:
    if path in st.session_state.uploaded_files:
        f = st.session_state.uploaded_files[path]
        content = f.get("content", "")
        return json.dumps({"success": True, "content": content[:10000], "name": f.get("name")})
    return json.dumps({"success": False, "error": "File not found"})

def write_file(path: str, content: str) -> str:
    st.session_state.uploaded_files[path] = {
        "type": "text", "name": path, "content": content,
        "size": len(content), "timestamp": datetime.now().isoformat()
    }
    return json.dumps({"success": True, "path": path, "size": len(content)})

def analyze_image(file_key: str, prompt: str = "Describe this image") -> str:
    try:
        from features.vision import VisionAnalyzer
        analyzer = VisionAnalyzer()
        if file_key not in st.session_state.uploaded_files:
            return json.dumps({"success": False, "error": "Image not found"})
        img_data = st.session_state.uploaded_files[file_key]
        result = analyzer.analyze(img_data["bytes"], prompt=prompt, model="gemini")
        return json.dumps({"success": True, "analysis": result})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

TOOLS_REGISTRY = {
    "web_search": {"func": web_search, "description": "Search the web", "params": {"query": {"type": "string"}}},
    "github_get_files": {"func": github_get_files, "description": "List GitHub repo files", "params": {"repo": {"type": "string"}}},
    "deep_research": {"func": deep_research, "description": "Deep research", "params": {"topic": {"type": "string"}, "depth": {"type": "integer"}}},
    "execute_code": {"func": execute_code, "description": "Run Python code", "params": {"code": {"type": "string"}}},
    "fetch_url": {"func": fetch_url, "description": "Fetch URL content", "params": {"url": {"type": "string"}}},
    "read_file": {"func": read_file, "description": "Read file", "params": {"path": {"type": "string"}}},
    "write_file": {"func": write_file, "description": "Write file", "params": {"path": {"type": "string"}, "content": {"type": "string"}}},
    "analyze_image": {"func": analyze_image, "description": "Analyze image", "params": {"file_key": {"type": "string"}, "prompt": {"type": "string"}}},
}

def get_tool_schema() -> List[Dict]:
    tools = []
    for name, meta in TOOLS_REGISTRY.items():
        props = {p: {"type": t["type"]} for p, t in meta["params"].items()}
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": {"type": "object", "properties": props, "required": list(meta["params"].keys())}
            }
        })
    return tools

def execute_tool_call(tc_data: Dict) -> Dict:
    fn = tc_data.get("function", {})
    name = fn.get("name", "unknown")
    try:
        args = json.loads(fn.get("arguments", "{}"))
    except:
        args = {}
    
    if name not in TOOLS_REGISTRY:
        return {"name": name, "status": "error", "result": f"Tool '{name}' not available", "duration_ms": 0}
    
    start = time.time()
    try:
        result = TOOLS_REGISTRY[name]["func"](**args)
        status = "success"
    except Exception as e:
        result = f"Error: {str(e)}"
        status = "error"
    
    return {
        "name": name,
        "status": status,
        "result": str(result)[:4000],
        "duration_ms": (time.time() - start) * 1000
    }


# ============ SWARM AGENT SYSTEM ============

def run_swarm_task(prompt: str, model: str, progress_placeholder, user_id: str = None) -> Dict[str, Any]:
    """Execute task using swarm of specialized agents."""
    client = get_enhanced_client()
    
    # Step 1: Master agent creates plan
    progress_placeholder.markdown("""
    <div class="swarm-progress-container">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span>👑</span>
            <span>Master Agent</span>
            <span style="color:#10a37f;">Analyzing task...</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    planning_messages = [
        {"role": "system", "content": MASTER_AGENT_PROMPT},
        {"role": "user", "content": f"Create a plan for this task: {prompt}"}
    ]
    
    plan_response = client.chat(planning_messages, model=model, user_id=user_id)
    plan_text = plan_response.get("content", "")
    
    # Parse JSON plan
    subtasks = []
    try:
        json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
        if json_match:
            plan_data = json.loads(json_match.group())
            subtasks = plan_data.get("subtasks", [])
    except:
        # Fallback: create default subtasks
        subtasks = [
            {"id": "1", "type": "researcher", "description": f"Research: {prompt}"},
            {"id": "2", "type": "writer", "description": "Synthesize findings into final answer"}
        ]
    
    # Step 2: Execute each subtask in parallel (simulated)
    results = {}
    total = len(subtasks)
    
    for i, subtask in enumerate(subtasks):
        agent_type = subtask.get("type", "researcher")
        description = subtask.get("description", "")
        
        progress_placeholder.markdown(f"""
        <div class="swarm-progress-container">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <span>{'🔍' if agent_type == 'researcher' else '💻' if agent_type == 'coder' else '📊' if agent_type == 'analyst' else '✍️'}</span>
                <span>{agent_type.upper()} Agent</span>
                <span style="color:#3b82f6;">Working on subtask {i+1}/{total}...</span>
            </div>
            <div style="height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden;">
                <div style="height:100%;width:{((i+1)/total)*100}%;background:#10a37f;border-radius:2px;"></div>
            </div>
            <div style="font-size:11px;color:#666;margin-top:8px;">{description[:100]}</div>
        </div>
        """, unsafe_allow_html=True)
        
        agent_messages = [
            {"role": "system", "content": SUB_AGENT_PROMPTS.get(agent_type, "You are a helpful assistant.")},
            {"role": "user", "content": description}
        ]
        
        agent_response = client.chat(agent_messages, model=model, user_id=user_id)
        results[subtask.get("id", str(i))] = {
            "type": agent_type,
            "description": description,
            "result": agent_response.get("content", "No response")
        }
        
        time.sleep(0.3)  # Brief pause for visual effect
    
    # Step 3: Synthesize results
    progress_placeholder.markdown("""
    <div class="swarm-progress-container">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span>🎯</span>
            <span>Master Agent</span>
            <span style="color:#10a37f;">Synthesizing results...</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    synthesis_prompt = f"""Original task: {prompt}

Results from sub-agents:
{json.dumps(results, indent=2)}

Please synthesize these results into a clear, comprehensive final response that directly addresses the original task."""
    
    synthesis_messages = [
        {"role": "system", "content": "You are a synthesis expert. Combine multiple agent results into a coherent response."},
        {"role": "user", "content": synthesis_prompt}
    ]
    
    final_response = client.chat(synthesis_messages, model=model, user_id=user_id)
    
    progress_placeholder.markdown("""
    <div class="swarm-progress-container">
        <div style="display:flex;align-items:center;gap:8px;">
            <span>✅</span>
            <span>Swarm Complete</span>
            <span style="color:#10a37f;">All agents finished</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    return {
        "content": final_response.get("content", "Task completed."),
        "subtasks": subtasks,
        "results": results,
        "type": "swarm"
    }


# ============ STANDARD AGENT EXECUTION ============

def run_agent_task(prompt: str, model: str, progress_placeholder, user_id: str = None) -> Dict[str, Any]:
    """Execute standard agent task with tool use."""
    client = get_enhanced_client()
    traces = []
    max_steps = st.session_state.get("agent_max_steps", 25)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nYou have tools available. Use them when needed."},
        {"role": "user", "content": prompt}
    ]
    
    for step in range(1, max_steps + 1):
        progress_placeholder.markdown(f"""
        <div class="agent-progress-container">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <span>🤖</span>
                <span>Agent Step {step}/{max_steps}</span>
                <span style="width:7px;height:7px;border-radius:50%;background:#f59e0b;display:inline-block;"></span>
            </div>
            <div style="height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden;">
                <div style="height:100%;width:{(step/max_steps)*100}%;background:linear-gradient(90deg,#10a37f,#34d399);border-radius:2px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        response = client.chat(messages, model=model, tools=get_tool_schema(), user_id=user_id)
        
        if response.get("guardrail_triggered"):
            return {"content": response["content"], "traces": traces}
        
        content = response.get("content") or ""
        tool_calls_raw = response.get("tool_calls") or []
        
        if not tool_calls_raw:
            return {"content": content or "Task completed.", "traces": traces}
        
        trace = {"step": step, "thought": content[:200], "tool_calls": []}
        
        assistant_msg = {
            "role": "assistant",
            "content": content or "Using tools...",
            "tool_calls": [
                {"id": tc.get("id", f"call_{step}"), "type": "function", "function": tc.get("function", {})}
                for tc in tool_calls_raw
            ]
        }
        messages.append(assistant_msg)
        
        for tc_raw in tool_calls_raw:
            tc_result = execute_tool_call(tc_raw)
            trace["tool_calls"].append(tc_result)
            
            tool_msg = {
                "role": "tool",
                "content": tc_result["result"][:4000],
                "tool_call_id": tc_raw.get("id", f"call_{step}")
            }
            messages.append(tool_msg)
        
        traces.append(trace)
        
        # Follow up after tools
        follow_up = client.chat(messages, model=model, user_id=user_id)
        follow_content = follow_up.get("content") or ""
        
        if follow_content:
            messages.append({"role": "assistant", "content": follow_content})
            return {"content": follow_content, "traces": traces}
    
    final_content = f"⚠️ Maximum steps ({max_steps}) reached.\n\n" + "\n".join([f"Step {t['step']}: {t['thought']}" for t in traces])
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
                        # Check for developer account first
                        if is_developer(username, password):
                            # Create developer session without needing stored auth
                            st.session_state.user_token = "dev_token"
                            st.session_state.current_user = {
                                "username": DEVELOPER_USERNAME,
                                "display_name": "Dennis"
                            }
                            st.session_state.is_developer = True
                            st.success(f"Welcome back, Dennis! 👑")
                            time.sleep(0.5)
                            st.rerun()
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
                    elif new_username.lower() == DEVELOPER_USERNAME:
                        st.error("This username is reserved. Please choose another.")
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
        if st.session_state.is_developer:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px;background:#1a1a1a;border-radius:10px;margin-bottom:10px;border:1px solid #10a37f;">
                <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#10a37f,#34d399);display:flex;align-items:center;justify-content:center;font-weight:600;color:white;font-size:14px;">
                    {user['display_name'][0].upper()}
                </div>
                <div>
                    <div style="font-weight:600;color:#e8e8e8;font-size:13px;">{html_module.escape(user['display_name'])}</div>
                    <div style="font-size:11px;color:#10a37f;">👑 Developer / Creator</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
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
            if st.button("⚙️ Settings", use_container_width=True):
                st.session_state.show_settings = True
                st.rerun()
        with col2:
            if st.button("🚪 Sign Out", use_container_width=True):
                auth = get_auth_manager()
                auth.logout(st.session_state.user_token)
                for key in ['user_token', 'current_user', 'current_conversation_id', 'is_developer']:
                    st.session_state[key] = None
                st.rerun()
        
        st.divider()
        
        with st.expander("⚙️ Advanced Settings"):
            st.session_state.cache_enabled = st.toggle("💾 Response Cache", value=st.session_state.cache_enabled)
            st.session_state.memory_enabled = st.toggle("🧠 Memory System", value=st.session_state.memory_enabled)
            st.session_state.auto_route = st.toggle("🔄 Auto Route Queries", value=st.session_state.auto_route)
            
            st.session_state.agent_max_steps = st.slider(
                "📊 Agent Max Steps",
                min_value=5,
                max_value=50,
                value=st.session_state.agent_max_steps,
                help="More steps = better for complex tasks"
            )
            
            if st.button("🗑️ Clear Cache", use_container_width=True):
                client = get_enhanced_client()
                client.clear_cache()
                st.success("Cache cleared!")
            
            if st.button("🧹 Clear Memory", use_container_width=True):
                client = get_enhanced_client()
                client.clear_memory(user["username"])
                st.success("Memory cleared!")
        
        st.divider()
        st.caption("DenLab v5.3 | 🧠 Memory • ⚡ Cache • 🤖 Agent • 👑 Dev")


def show_settings():
    st.markdown("## Settings")
    user = st.session_state.current_user
    auth = get_auth_manager()
    
    tab1, tab2 = st.tabs(["Account", "Advanced"])
    
    with tab1:
        st.markdown("### Profile")
        st.write(f"**Username:** @{user['username']}")
        if st.session_state.is_developer:
            st.info("👑 **Developer Mode** - You have full access to all features.")
        
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
        st.session_state.cache_enabled = st.toggle("Response Cache", value=st.session_state.cache_enabled)
        st.session_state.memory_enabled = st.toggle("Memory System", value=st.session_state.memory_enabled)
        st.session_state.auto_route = st.toggle("Auto-route to Agent", value=st.session_state.auto_route)
        st.session_state.agent_max_steps = st.slider("Agent Max Steps", 5, 50, st.session_state.agent_max_steps)
        
        if st.button("Save Settings", type="primary"):
            st.success("Settings saved!")
    
    if st.button("← Back to Chat"):
        st.session_state.show_settings = False
        st.rerun()


def show_sidebar():
    user = st.session_state.current_user
    db = get_chat_db(user["username"])
    
    with st.sidebar:
        st.markdown("""
        <div style="border-bottom: 1px solid #222; padding-bottom: 12px; margin-bottom: 12px;">
            <h1 style="font-size: 16px; margin: 0; color: #fff; font-weight: 700;">DenLab Chat</h1>
            <p style="font-size: 11px; color: #666; margin: 4px 0 0 0;">Advanced AI with Swarm Agents</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("+ New Chat", use_container_width=True, type="primary"):
            conv_id = db.create_conversation(model=st.session_state.get("selected_model", "openai"))
            st.session_state.current_conversation_id = conv_id
            st.rerun()
        
        st.divider()
        
        st.markdown('<p style="font-size: 10px; color: #666;">MODEL</p>', unsafe_allow_html=True)
        model_names = list(MODELS.keys())
        current_model = st.session_state.get("selected_model", "openai")
        model_values = list(MODELS.values())
        idx = model_values.index(current_model) if current_model in model_values else 0
        choice = st.selectbox("", model_names, index=idx, label_visibility="collapsed")
        st.session_state.selected_model = MODELS[choice]
        
        st.divider()
        
        st.markdown('<p style="font-size: 10px; color: #666;">AGENT MODE</p>', unsafe_allow_html=True)
        
        mode_col1, mode_col2 = st.columns(2)
        with mode_col1:
            standard_mode = st.button("🤖 Standard", use_container_width=True, 
                                      type="primary" if not st.session_state.get("swarm_mode", False) else "secondary")
            if standard_mode:
                st.session_state.swarm_mode = False
                st.session_state.agent_mode = True
                st.rerun()
        with mode_col2:
            swarm_mode = st.button("🐝 Swarm", use_container_width=True,
                                   type="primary" if st.session_state.get("swarm_mode", False) else "secondary")
            if swarm_mode:
                st.session_state.swarm_mode = True
                st.session_state.agent_mode = True
                st.rerun()
        
        if st.session_state.get("swarm_mode", False):
            st.caption("🐝 Swarm mode: Master + sub-agents")
        else:
            st.caption("🤖 Standard agent with tools")
        
        st.divider()
        
        st.markdown('<p style="font-size: 10px; color: #666;">CONVERSATIONS</p>', unsafe_allow_html=True)
        conversations = db.get_conversations()
        
        if not conversations:
            st.caption("No conversations yet")
        else:
            for conv in conversations[:15]:
                conv_id = conv["id"]
                title = conv.get("title", "Untitled")
                is_active = conv_id == st.session_state.get("current_conversation_id")
                
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    if st.button(title[:24], key=f"conv_{conv_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state.current_conversation_id = conv_id
                        st.rerun()
                with col2:
                    if st.button("🗑", key=f"del_{conv_id}"):
                        db.delete_conversation(conv_id)
                        if st.session_state.get("current_conversation_id") == conv_id:
                            remaining = db.get_conversations()
                            st.session_state.current_conversation_id = remaining[0]["id"] if remaining else None
                        st.rerun()
        
        st.divider()
        
        current_conv = st.session_state.get("current_conversation_id")
        if current_conv:
            if st.button("📥 Export Chat", use_container_width=True):
                export_data = db.export_conversation(current_conv)
                conv = db.get_conversation(current_conv)
                title = conv.get("title", "chat") if conv else "chat"
                st.download_button("Download", export_data, f"denlab_{title.replace(' ', '_')}.md", use_container_width=True)
        
        st.divider()
        if st.session_state.is_developer:
            st.caption("👑 Developer Mode Active")
        st.caption("DenLab v5.3")


def render_message_actions(msg_idx: int, content: str, msg_type: str = "text"):
    cols = st.columns([1, 1, 1, 1, 1, 20])
    with cols[0]:
        if st.button("📋", key=f"copy_{msg_idx}"):
            st.toast("Copied!")
    with cols[1]:
        if st.button("🔊", key=f"speak_{msg_idx}"):
            try:
                audio_url = f"https://gen.pollinations.ai/audio/{requests.utils.quote(content[:500])}?voice=nova"
                st.audio(audio_url, format='audio/mp3')
            except:
                st.toast("Audio unavailable")
    with cols[2]:
        if st.button("🔄", key=f"regen_{msg_idx}"):
            if "messages" in st.session_state:
                st.session_state.messages = st.session_state.messages[:msg_idx]
            st.rerun()
    with cols[3]:
        if msg_type == "text":
            st.download_button("⬇️", content, f"message_{msg_idx}.md", key=f"dl_{msg_idx}")
    with cols[4]:
        if st.button("👍", key=f"like_{msg_idx}"):
            st.toast("Thanks!")


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
show_sidebar()

# File upload
uploaded = st.file_uploader(
    "📎 Attach file",
    type=["txt", "py", "js", "ts", "html", "css", "json", "md", "csv", "xml", "yaml", "yml",
          "sh", "c", "cpp", "h", "java", "kt", "swift", "rs", "go", "rb", "php", "sql",
          "png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "pdf"],
    accept_multiple_files=False,
    label_visibility="collapsed",
    key=f"uploader_{st.session_state.uploader_key}"
)

if uploaded and not st.session_state.processing_upload:
    st.session_state.pending_upload = uploaded
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(int(st.session_state.uploader_key) + 1)
    st.rerun()

if st.session_state.get("pending_upload") and st.session_state.get("processing_upload"):
    fobj = st.session_state.pending_upload
    fname = fobj.name
    fkey = f"{datetime.now().strftime('%H%M%S')}_{fname}"
    try:
        fb = fobj.read()
        if fobj.type and fobj.type.startswith("image/"):
            st.session_state.uploaded_files[fkey] = {"type": "image", "name": fname, "bytes": fb}
            db = get_chat_db(st.session_state.current_user["username"])
            db.add_message(conv_id, "user", f"📎 {fname}", {"type": "image_upload", "file_key": fkey})
            try:
                from features.vision import VisionAnalyzer
                analyzer = VisionAnalyzer()
                analysis = analyzer.analyze(fb, model="gemini")
                db.add_message(conv_id, "assistant", f"**📎 {fname}**\n\n{analysis}")
            except:
                db.add_message(conv_id, "assistant", f"**📎 {fname}** received.")
        else:
            txt = fb.decode('utf-8', errors='ignore')
            st.session_state.uploaded_files[fkey] = {"type": "text", "name": fname, "content": txt}
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
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:48px;margin-bottom:16px;">🧠</div>
        <div style="font-size:24px;font-weight:700;color:#111;margin-bottom:8px;">DenLab Chat</div>
        <div style="font-size:14px;color:#666;margin-bottom:32px;">Advanced AI with Swarm Agents</div>
        <div style="font-size:13px;color:#888;line-height:2;">
            <code>/imagine</code> — Generate images<br>
            <code>/research</code> — Deep web research<br>
            <code>/code</code> — Execute Python<br>
            <code>/analyze</code> — Analyze files<br>
            <code>/agent</code> — Use Swarm or Standard agent
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
        elif mtype == "image_upload":
            fk = meta.get("file_key")
            if fk and fk in st.session_state.uploaded_files:
                st.image(st.session_state.uploaded_files[fk]["bytes"], use_container_width=True)
        elif mtype == "file":
            st.markdown(content)
        elif mtype == "agent_trace":
            st.markdown(content)
            if meta.get("traces"):
                with st.expander("📋 Execution Trace"):
                    for t in meta["traces"]:
                        st.markdown(f"**Step {t['step']}**")
                        for tc in t.get("tool_calls", []):
                            st.markdown(f"- `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
        elif mtype == "swarm":
            st.markdown(content)
            if meta.get("subtasks"):
                with st.expander("🐝 Swarm Execution Details"):
                    for subtask in meta.get("subtasks", []):
                        st.markdown(f"**{subtask.get('type', 'unknown')}**: {subtask.get('description', '')[:100]}")
        else:
            st.markdown(content)
        
        if msg["role"] == "assistant" and idx > 0 and mtype not in ["image", "audio"]:
            render_message_actions(idx, content, mtype)

# Chat input
placeholder = "Message DenLab..." if not st.session_state.agent_mode else "Describe your task for the agent..."

if prompt := st.chat_input(placeholder):
    
    # Command handlers
    if prompt.lower().startswith("/imagine"):
        desc = prompt[8:].strip()
        if desc:
            db.add_message(conv_id, "user", f"🎨 {prompt}")
            with st.chat_message("assistant"):
                with st.spinner("Generating..."):
                    client = get_enhanced_client()
                    url = client.generate_image(desc)
                    st.image(url, caption=desc, use_container_width=True)
            db.add_message(conv_id, "assistant", url, {"type": "image"})
            st.rerun()
    
    elif prompt.lower().startswith("/research"):
        topic = prompt[9:].strip()
        if topic:
            db.add_message(conv_id, "user", f"🔬 {topic}")
            with st.chat_message("assistant"):
                with st.spinner("Researching..."):
                    result = deep_research(topic)
                    data = json.loads(result)
                    if data.get("success"):
                        out = f"## Research: {topic}\n\n"
                        for i, f in enumerate(data['findings'][:5], 1):
                            out += f"{i}. **{f['title']}**\n   {f['content'][:200]}...\n\n"
                        st.markdown(out)
                    else:
                        st.error(data.get("error", "Research failed"))
            db.add_message(conv_id, "assistant", out if data.get("success") else data.get("error"), {"type": "research"})
            st.rerun()
    
    elif prompt.lower().startswith("/code"):
        task = prompt[5:].strip()
        if task:
            db.add_message(conv_id, "user", f"💻 {task}")
            with st.chat_message("assistant"):
                with st.spinner("Coding..."):
                    client = get_enhanced_client()
                    code_prompt = f"Write Python to: {task}\nReturn ONLY the code inside a markdown code block."
                    resp = client.chat([
                        {"role": "system", "content": "Expert Python programmer."},
                        {"role": "user", "content": code_prompt}
                    ], model=st.session_state.selected_model)
                    
                    raw = resp.get("content", "")
                    code_match = re.search(r'```python\n(.*?)```', raw, re.DOTALL)
                    if not code_match:
                        code_match = re.search(r'```\n(.*?)```', raw, re.DOTALL)
                    code = code_match.group(1).strip() if code_match else raw.strip()
                    
                    st.code(code, language="python")
                    result = execute_code(code)
                    data = json.loads(result)
                    
                    if data.get("success"):
                        out = f"```python\n{code}\n```\n**Output:**\n```\n{data.get('stdout', '')}\n```"
                        st.markdown(out)
                    else:
                        st.error(data.get("error", "Execution failed"))
            db.add_message(conv_id, "assistant", out if data.get("success") else data.get("error"), {"type": "code"})
            st.rerun()
    
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
                            {"role": "system", "content": "Code reviewer."},
                            {"role": "user", "content": f"Analyze: {lf['name']}\n```\n{lf['content'][:4000]}\n```"}
                        ], model=st.session_state.selected_model)
                        st.markdown(analysis.get("content", "Analysis failed."))
                        db.add_message(conv_id, "assistant", analysis.get("content", ""))
                    elif lf["type"] == "image":
                        try:
                            from features.vision import VisionAnalyzer
                            analyzer = VisionAnalyzer()
                            analysis = analyzer.analyze(lf["bytes"])
                            st.markdown(analysis)
                            db.add_message(conv_id, "assistant", analysis)
                        except Exception as e:
                            st.error(f"Vision error: {e}")
            st.rerun()
        else:
            db.add_message(conv_id, "assistant", "No file uploaded.")
            st.rerun()
    
    elif prompt.lower().startswith("/audio"):
        text = prompt[6:].strip()
        if text:
            db.add_message(conv_id, "user", f"🔊 {text[:50]}")
            with st.chat_message("assistant"):
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
                if st.session_state.get("swarm_mode", False):
                    # Use Swarm mode
                    result = run_swarm_task(prompt, st.session_state.selected_model, progress_ph, st.session_state.current_user["username"])
                    db.add_message(conv_id, "assistant", result.get("content", ""), {
                        "type": "swarm",
                        "subtasks": result.get("subtasks", []),
                        "results": result.get("results", {})
                    })
                else:
                    # Use Standard agent mode
                    result = run_agent_task(prompt, st.session_state.selected_model, progress_ph, st.session_state.current_user["username"])
                    db.add_message(conv_id, "assistant", result.get("content", ""), {
                        "type": "agent_trace",
                        "traces": result.get("traces", [])
                    })
                
                st.markdown(result.get("content", "Task completed."))
                st.rerun()
                
            except Exception as e:
                st.error(f"Agent error: {str(e)}")
                db.add_message(conv_id, "assistant", f"Error: {str(e)}")
                st.rerun()
    
    # Normal Chat
    else:
        db.add_message(conv_id, "user", prompt)
        
        with st.chat_message("assistant"):
            ph = st.empty()
            client = get_enhanced_client()
            
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
                
                if not text or not text.strip():
                    result2 = client.chat(api_msgs, model=st.session_state.selected_model, stream=False)
                    text = result2.get("content", "")
                
                if text and text.strip():
                    ph.markdown(text)
                    response = text
                else:
                    ph.markdown("No response. Please try again.")
                    response = "Empty response."
                    
            except Exception as e:
                ph.markdown(f"Error: {str(e)}")
                response = f"Error: {str(e)}"
        
        db.add_message(conv_id, "assistant", response)
        st.rerun()