"""DenLab v3.0 - Autonomous AI Research Assistant
GitHub: https://github.com/daktari-art/denlab-chat
Streamlit: https://denlab-chat.streamlit.app
"""
import streamlit as st
import asyncio
import json
from datetime import datetime

# Page config MUST be first
st.set_page_config(
    page_title="DenLab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import custom CSS
from assets.custom_css import DARK_THEME
st.markdown(DARK_THEME, unsafe_allow_html=True)

# Import components
from components.sidebar import Sidebar
from components.chat_interface import ChatInterface
from components.agent_interface import AgentInterface

# Import agents
from agents.base_agent import BaseAgent, AgentState
from agents.orchestrator import SwarmOrchestrator
from agents.tool_registry import registry
from agents.planner import TaskPlanner

# Import tools (registers them automatically)
from agents.tools import (
    web_search, deep_research, execute_code,
    fetch_url, read_file, write_file, analyze_image
)

# Import core
from core.api_client import PollinationsClient
from core.session_manager import SessionManager
from config.settings import MODELS, SYSTEM_PROMPT
from config.models import MessageRole, ContentType

# ============ AGENT SETUP ============

class DenLabAgent(BaseAgent):
    """Concrete agent implementation using Pollinations API."""
    
    def __init__(self, name: str = "DenLab-Agent", model: str = "openai"):
        super().__init__(name, model, max_steps=20)
        self.client = PollinationsClient()
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all available tools."""
        self.register_tool(
            "web_search", web_search,
            "Search the web for current information",
            {"query": {"type": "string", "description": "Search query"}}
        )
        self.register_tool(
            "deep_research", deep_research,
            "Conduct deep multi-source research on a topic",
            {"topic": {"type": "string", "description": "Research topic"}}
        )
        self.register_tool(
            "execute_code", execute_code,
            "Execute Python code in sandbox",
            {"code": {"type": "string", "description": "Python code to execute"}}
        )
        self.register_tool(
            "fetch_url", fetch_url,
            "Fetch and read content from a URL",
            {"url": {"type": "string", "description": "URL to fetch"}}
        )
        self.register_tool(
            "read_file", read_file,
            "Read contents of a file",
            {"path": {"type": "string", "description": "File path"}}
        )
        self.register_tool(
            "write_file", write_file,
            "Write content to a file",
            {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to write"}
            }
        )
    
    async def _llm_call(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Call Pollinations API."""
        return self.client.chat(
            messages=messages,
            model=self.model,
            tools=tools,
            temperature=0.7
        )

def get_agent(model: str = "openai") -> DenLabAgent:
    """Get or create agent."""
    if "agent" not in st.session_state:
        st.session_state.agent = DenLabAgent(model=model)
    return st.session_state.agent

# ============ SESSION STATE ============

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "🧪 **DenLab ready.**\n\n**Modes:**\n• Chat - Standard conversation\n• Agent - Autonomous task execution with tools\n\n**Commands:**\n• `/imagine [prompt]` - Generate images\n• `/research [topic]` - Deep research\n• `/code [task]` - Code generation & execution"}
        ],
        "model": "openai",
        "agent_mode": False,
        "swarm_mode": False,
        "show_agent_traces": True,
        "uploader_key": "0",
        "pending_upload": None,
        "processing_upload": False,
        "current_session": "Main",
        "sessions": {},
        "agent_traces": []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============ SIDEBAR ============

with st.sidebar:
    st.title("🧪 DenLab")
    st.caption("v3.0 · Beyond Conversational AI")
    st.divider()
    
    # Model Selection
    st.subheader("🤖 Model")
    model_names = list(MODELS.keys())
    current_idx = list(MODELS.values()).index(st.session_state.model) if st.session_state.model in MODELS.values() else 0
    model_choice = st.selectbox("Select", model_names, index=current_idx, label_visibility="collapsed")
    st.session_state.model = MODELS[model_choice]
    
    # Agent Mode Toggle
    st.divider()
    st.subheader("⚡ Agent Mode")
    
    agent_mode = st.toggle("Enable Agent", value=st.session_state.agent_mode, 
                          help="Autonomous AI with tool-use capabilities")
    st.session_state.agent_mode = agent_mode
    
    if agent_mode:
        swarm_mode = st.toggle("Swarm Mode", value=st.session_state.swarm_mode,
                              help="Parallel agent execution")
        st.session_state.swarm_mode = swarm_mode
        
        st.caption("Tools available: web_search, code_execution, file_ops, browser")
    
    # Session Management
    st.divider()
    st.subheader("💬 Sessions")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_name = st.text_input("New session", placeholder="Name...", label_visibility="collapsed")
    with col2:
        if st.button("➕", use_container_width=True):
            name = new_name or f"Session {len(st.session_state.sessions) + 1}"
            st.session_state.sessions[st.session_state.current_session] = st.session_state.messages.copy()
            st.session_state.current_session = name
            st.session_state.messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "assistant", "content": f"🧪 **{name}** started. How can I help?"}
            ]
            st.rerun()
    
    # List sessions
    if st.session_state.sessions:
        for sess_name, msgs in list(st.session_state.sessions.items())[-10:]:
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(f"📁 {sess_name[:20]}", use_container_width=True, key=f"load_{sess_name}"):
                    st.session_state.current_session = sess_name
                    st.session_state.messages = msgs
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{sess_name}"):
                    del st.session_state.sessions[sess_name]
                    st.rerun()
    
    # Export
    st.divider()
    if st.button("📥 Export Chat", use_container_width=True):
        export_text = "\n\n".join([
            f"**{m['role'].upper()}**: {m['content']}"
            for m in st.session_state.messages if m['role'] != 'system'
        ])
        st.download_button("Download .md", export_text, 
                          f"denlab_{st.session_state.current_session}.md",
                          use_container_width=True)
    
    # File Upload
    st.divider()
    st.subheader("📎 Upload")
    uploaded = st.file_uploader("File", 
                               type=["txt", "py", "js", "html", "json", "md", "csv", "png", "jpg"],
                               key=f"uploader_{st.session_state.uploader_key}",
                               label_visibility="collapsed")

# ============ HANDLE FILE UPLOAD ============

if uploaded and not st.session_state.processing_upload:
    st.session_state.pending_upload = uploaded
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(int(st.session_state.uploader_key) + 1)
    st.rerun()

if st.session_state.pending_upload and st.session_state.processing_upload:
    file_obj = st.session_state.pending_upload
    filename = file_obj.name
    
    if file_obj.type and file_obj.type.startswith("image/"):
        file_bytes = file_obj.read()
        st.session_state.messages.append({
            "role": "user", 
            "content": f"🖼️ Uploaded: {filename}",
            "metadata": {"type": "image_upload"}
        })
        
        with st.chat_message("user"):
            st.markdown(f"🖼️ **{filename}**")
            st.image(file_bytes, use_container_width=True)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing image..."):
                # Use vision if available, otherwise acknowledge
                response = f"I've received **{filename}**. In agent mode, I can analyze this image in detail. What would you like to know about it?"
            st.markdown(response)
    else:
        try:
            content = file_obj.read().decode('utf-8', errors='ignore')
        except:
            content = "[Could not read file]"
        
        st.session_state.messages.append({
            "role": "user",
            "content": f"📎 {filename}",
            "metadata": {"type": "file", "filename": filename, "content": content[:2000]}
        })
        
        with st.chat_message("user"):
            st.markdown(f"📎 **{filename}**")
            if content != "[Could not read file]":
                with st.expander("Preview"):
                    st.code(content[:1500], language=filename.split('.')[-1] if '.' in filename else 'text')
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                if st.session_state.agent_mode:
                    # Agent analyzes file
                    agent = get_agent(st.session_state.model)
                    agent.memory["uploaded_file"] = {"name": filename, "content": content}
                    response = f"📄 **{filename}** loaded into agent memory. I can now reference this file in our conversation. Use `/analyze` for deep analysis."
                else:
                    response = f"Received **{filename}**. Ask me to analyze its contents."
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# ============ MAIN CHAT DISPLAY ============

st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "system":
        continue
    
    with st.chat_message(msg["role"]):
        # Handle different content types
        if msg.get("metadata", {}).get("type") == "image":
            st.image(msg["content"], use_container_width=True)
            st.caption("🎨 Generated image")
        elif msg.get("metadata", {}).get("type") == "agent_trace":
            # Render agent trace
            with st.expander("🔍 Agent Execution Trace", expanded=False):
                traces = msg["metadata"].get("traces", [])
                for trace in traces:
                    st.markdown(f"**Step {trace.step}**")
                    st.markdown(f"💭 *{trace.thought[:200]}...*" if trace.thought else "💭 *Thinking...*")
                    for tc in trace.tool_calls:
                        icon = "✅" if tc.status == "success" else "❌"
                        st.markdown(f"{icon} **{tc.name}** ({tc.duration_ms:.0f}ms)")
                        with st.code(language="json"):
                            st.json({"args": tc.arguments, "result": str(tc.result)[:500]})
        else:
            st.markdown(msg["content"])

st.markdown('</div>', unsafe_allow_html=True)

# ============ AGENT TRACE DISPLAY (if active) ============

if st.session_state.agent_mode and st.session_state.get("current_agent_trace"):
    st.divider()
    with st.container():
        st.subheader("🤖 Agent Activity")
        trace_container = st.empty()
        # Real-time updates handled in callback

# ============ CHAT INPUT ============

placeholder = "Message DenLab..." 
if st.session_state.agent_mode:
    placeholder = "🤖 Agent mode: Describe a complex task to autonomously execute..."

if prompt := st.chat_input(placeholder):
    
    # Handle commands
    if prompt.lower().startswith("/imagine"):
        # Image generation
        desc = prompt[8:].strip()
        if desc:
            st.session_state.messages.append({
                "role": "user", 
                "content": f"🎨 {desc}",
                "metadata": {"type": "image_request"}
            })
            
            with st.chat_message("user"):
                st.markdown(f"🎨 **{desc}**")
            
            with st.chat_message("assistant"):
                with st.spinner("Creating..."):
                    client = PollinationsClient()
                    img_url = client.generate_image(desc)
                    st.image(img_url, caption=desc, use_container_width=True)
                    response = f"![Generated]({img_url})"
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": img_url,
                "metadata": {"type": "image"}
            })
            st.rerun()
    
    elif prompt.lower().startswith("/research"):
        # Direct research command
        topic = prompt[9:].strip()
        if topic:
            st.session_state.messages.append({
                "role": "user",
                "content": f"🔬 Research: {topic}"
            })
            
            with st.chat_message("assistant"):
                with st.status("🔬 Conducting deep research...", expanded=True) as status:
                    result = deep_research(topic, depth=2)
                    data = json.loads(result)
                    
                    st.markdown(f"**Topic:** {data['topic']}")
                    st.markdown(f"**Sources analyzed:** {data['total_sources']}")
                    
                    for finding in data['findings'][:3]:
                        with st.expander(f"📄 {finding['title'][:50]}..."):
                            st.markdown(f"**Source:** {finding['source']}")
                            st.markdown(finding['content'][:500] + "...")
                    
                    status.update(label="Research complete!", state="complete")
                    
                    synthesis = f"## Research: {topic}\n\nBased on {data['total_sources']} sources, here are the key findings:\n\n"
                    for i, f in enumerate(data['findings'][:3], 1):
                        synthesis += f"{i}. **{f['title']}**: {f['content'][:300]}...\n\n"
                    
                    st.markdown(synthesis)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": synthesis,
                        "metadata": {"type": "research_result", "data": data}
                    })
            st.rerun()
    
    elif prompt.lower().startswith("/code"):
        # Direct code execution
        task = prompt[5:].strip()
        if task:
            st.session_state.messages.append({
                "role": "user",
                "content": f"💻 Code: {task}"
            })
            
            with st.chat_message("assistant"):
                with st.status("💻 Generating and executing code...", expanded=True):
                    # Generate code via LLM
                    client = PollinationsClient()
                    code_prompt = f"Write Python code to: {task}\n\nReturn ONLY the code, no explanations."
                    code = client.chat([
                        {"role": "system", "content": "You are a Python expert. Return only code."},
                        {"role": "user", "content": code_prompt}
                    ], model=st.session_state.model)["content"]
                    
                    # Clean code blocks
                    code = code.replace("```python", "").replace("```", "").strip()
                    
                    st.code(code, language="python")
                    
                    # Execute
                    result = execute_code(code)
                    data = json.loads(result)
                    
                    if data.get("success"):
                        st.success("Execution successful!")
                        if data.get("stdout"):
                            st.text(data["stdout"])
                        response = f"**Generated Code:**\n```python\n{code}\n```\n\n**Output:**\n```\n{data.get('stdout', 'No output')}\n```"
                    else:
                        st.error(f"Error: {data.get('stderr', data.get('error'))}")
                        response = f"**Code:**\n```python\n{code}\n```\n\n**Error:** {data.get('stderr', data.get('error'))}"
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "metadata": {"type": "code_execution", "code": code, "result": data}
                    })
            st.rerun()
    
    elif st.session_state.agent_mode:
        # AGENT MODE - Autonomous execution
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            if st.session_state.swarm_mode:
                # SWARM MODE
                with st.status("🐝 Initializing Agent Swarm...", expanded=True) as status:
                    orchestrator = SwarmOrchestrator(max_parallel=3)
                    
                    # Register agent factories
                    def make_researcher():
                        a = DenLabAgent("Researcher", st.session_state.model)
                        a.max_steps = 10
                        return a
                    
                    def make_coder():
                        a = DenLabAgent("Coder", st.session_state.model)
                        a.max_steps = 8
                        return a
                    
                    orchestrator.register_agent("researcher", make_researcher)
                    orchestrator.register_agent("coder", make_coder)
                    orchestrator.register_agent("analyst", make_researcher)
                    orchestrator.register_agent("writer", make_researcher)
                    
                    # Progress callback
                    def on_progress(subtask):
                        status.write(f"🔄 {subtask.agent_type}: {subtask.description[:50]}...")
                    
                    orchestrator.on_progress = on_progress
                    
                    # Execute
                    import asyncio
                    result = asyncio.run(orchestrator.execute(prompt))
                    
                    status.update(label="✅ Swarm complete!", state="complete")
                    
                    # Display results
                    st.markdown("## 🐝 Swarm Results")
                    
                    cols = st.columns(len(result["subtasks"]))
                    for idx, (st_id, st_data) in enumerate(result["subtasks"].items()):
                        with cols[idx % len(cols)]:
                            icon = "✅" if st_data["status"] == "complete" else "❌"
                            st.metric(f"{icon} {st_id}", 
                                     f"{st_data['duration']:.1f}s",
                                     st_data["status"])
                    
                    st.markdown("### Synthesis")
                    st.markdown(result["synthesis"])
                    
                    # Store with traces
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["synthesis"],
                        "metadata": {
                            "type": "agent_trace",
                            "traces": [],  # Simplified for swarm
                            "subtasks": result["subtasks"]
                        }
                    })
            else:
                # SINGLE AGENT MODE
                agent = get_agent(st.session_state.model)
                agent.model = st.session_state.model
                
                # Trace collection
                traces = []
                def on_step(trace):
                    traces.append(trace)
                
                agent.on_step = on_step
                
                with st.status("🤖 Agent executing...", expanded=True) as status:
                    # Run agent
                    import asyncio
                    
                    # Update status with progress
                    async def run_with_updates():
                        task = asyncio.create_task(agent.run(prompt))
                        
                        while not task.done():
                            if agent.traces:
                                latest = agent.traces[-1]
                                status.write(f"Step {latest.step}: {latest.thought[:80]}...")
                            await asyncio.sleep(0.5)
                        
                        return await task
                    
                    response = asyncio.run(run_with_updates())
                    
                    status.update(label="✅ Complete!", state="complete")
                    
                    # Show trace if enabled
                    if st.session_state.show_agent_traces and traces:
                        with st.expander("🔍 Execution Trace", expanded=False):
                            for trace in traces:
                                st.markdown(f"**Step {trace.step}**")
                                if trace.thought:
                                    st.markdown(f"💭 {trace.thought[:200]}")
                                for tc in trace.tool_calls:
                                    icon = "✅" if tc.status == "success" else "❌"
                                    st.markdown(f"{icon} `{tc.name}` ({tc.duration_ms:.0f}ms)")
                                    st.json({"args": tc.arguments, "result": str(tc.result)[:300]})
                    
                    st.markdown(response)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "metadata": {
                            "type": "agent_trace",
                            "traces": [
                                {
                                    "step": t.step,
                                    "thought": t.thought,
                                    "tool_calls": [
                                        {
                                            "name": tc.name,
                                            "arguments": tc.arguments,
                                            "result": str(tc.result)[:500],
                                            "status": tc.status,
                                            "duration_ms": tc.duration_ms
                                        }
                                        for tc in t.tool_calls
                                    ]
                                }
                                for t in traces
                            ]
                        }
                    })
        
        st.rerun()
    
    else:
        # NORMAL CHAT MODE
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                client = PollinationsClient()
                api_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages if m["role"] != "system"
                ]
                api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                
                response_data = client.chat(api_messages, model=st.session_state.model)
                response = response_data["content"]
            
            st.markdown(response)
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
        
        st.rerun()
