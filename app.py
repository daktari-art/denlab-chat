"""DenLab v3.0 - Kimi-inspired Interface"""
import streamlit as st
import asyncio
import json
import base64
from datetime import datetime

st.set_page_config(page_title="DenLab", page_icon="🧪", layout="wide")

# Inject CSS
from assets.custom_css import DARK_THEME
st.markdown(DARK_THEME, unsafe_allow_html=True)

from core.api_client import PollinationsClient
from core.session_manager import SessionManager
from config.settings import MODELS, SYSTEM_PROMPT

from agents.base_agent import BaseAgent
from agents.orchestrator import SwarmOrchestrator
from agents.planner import TaskPlanner
from agents.tools import web_search, deep_research, execute_code, fetch_url, read_file, write_file

# ============ AGENT SETUP ============

class DenLabAgent(BaseAgent):
    def __init__(self, name="DenLab-Agent", model="openai"):
        super().__init__(name, model, max_steps=20)
        self.client = PollinationsClient()
        self._register_all_tools()
    
    def _register_all_tools(self):
        self.register_tool("web_search", web_search, "Search the web", {"query": {"type": "string", "description": "Search query"}})
        self.register_tool("deep_research", deep_research, "Deep research", {"topic": {"type": "string", "description": "Topic"}})
        self.register_tool("execute_code", execute_code, "Execute Python", {"code": {"type": "string", "description": "Code"}})
        self.register_tool("fetch_url", fetch_url, "Fetch URL", {"url": {"type": "string", "description": "URL"}})
        self.register_tool("read_file", read_file, "Read file", {"path": {"type": "string", "description": "Path"}})
        self.register_tool("write_file", write_file, "Write file", {"path": {"type": "string"}, "content": {"type": "string"}})
    
    async def _llm_call(self, messages, tools=None):
        return self.client.chat(messages=messages, model=self.model, tools=tools, temperature=0.7)

def get_agent(model="openai"):
    if "agent" not in st.session_state:
        st.session_state.agent = DenLabAgent(model=model)
    return st.session_state.agent

# ============ SESSION STATE ============

def init_session_state():
    defaults = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "🧪 **DenLab ready.**\n\n**Commands:** `/imagine`, `/research`, `/code`, `/analyze`\n\nToggle **Agent Mode** for autonomous task execution."}
        ],
        "model": "openai",
        "agent_mode": False,
        "swarm_mode": False,
        "uploader_key": "0",
        "pending_upload": None,
        "processing_upload": False,
        "current_session": "Main",
        "sessions": {},
        "uploaded_files": {},
        "show_traces": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============ SIDEBAR - FIXED HEADER ============

with st.sidebar:
    # Sticky header section
    st.markdown("""
        <div style="position: sticky; top: 0; background: #0f0f15; z-index: 100; padding-bottom: 10px; border-bottom: 1px solid #1a1a2e;">
            <h1 style="font-size: 20px; margin: 0; padding: 10px 0;">🧪 DenLab</h1>
            <p style="font-size: 12px; color: #666; margin: 0;">v3.0 · Agentic AI</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Scrollable content
    with st.container():
        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
        
        # Model
        st.markdown('<p style="font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Model</p>', unsafe_allow_html=True)
        model_names = list(MODELS.keys())
        current_idx = list(MODELS.values()).index(st.session_state.model) if st.session_state.model in MODELS.values() else 0
        model_choice = st.selectbox("", model_names, index=current_idx, label_visibility="collapsed")
        st.session_state.model = MODELS[model_choice]
        
        # Agent toggles
        st.markdown('<p style="font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 8px;">Mode</p>', unsafe_allow_html=True)
        
        agent_mode = st.toggle("🤖 Agent Mode", value=st.session_state.agent_mode, help="Autonomous execution with tools")
        st.session_state.agent_mode = agent_mode
        
        if agent_mode:
            swarm_mode = st.toggle("🐝 Swarm Mode", value=st.session_state.swarm_mode, help="Parallel agents")
            st.session_state.swarm_mode = swarm_mode
        
        # Sessions
        st.markdown('<p style="font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 8px;">Sessions</p>', unsafe_allow_html=True)
        
        cols = st.columns([3, 1])
        with cols[0]:
            new_name = st.text_input("", placeholder="New session...", label_visibility="collapsed")
        with cols[1]:
            if st.button("➕", use_container_width=True):
                name = new_name or f"Session {len(st.session_state.sessions) + 1}"
                st.session_state.sessions[st.session_state.current_session] = st.session_state.messages.copy()
                st.session_state.current_session = name
                st.session_state.messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "assistant", "content": f"🧪 **{name}** started."}
                ]
                st.rerun()
        
        if st.session_state.sessions:
            for sess_name in list(st.session_state.sessions.keys())[-8:]:
                c1, c2 = st.columns([5, 1])
                with c1:
                    if st.button(f"📁 {sess_name[:22]}", use_container_width=True, key=f"load_{sess_name}"):
                        st.session_state.current_session = sess_name
                        st.session_state.messages = st.session_state.sessions[sess_name]
                        st.rerun()
                with c2:
                    if st.button("🗑️", key=f"del_{sess_name}"):
                        del st.session_state.sessions[sess_name]
                        st.rerun()
        
        # Export
        st.markdown('<p style="font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 8px;">Export</p>', unsafe_allow_html=True)
        if st.button("📥 Export Chat", use_container_width=True):
            export_text = "\n\n".join([f"**{m['role'].upper()}**: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
            st.download_button("Download .md", export_text, f"denlab_{st.session_state.current_session}.md", use_container_width=True)
        
        # Upload - EXPANDED FILE TYPES
        st.markdown('<p style="font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 8px;">Upload</p>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "",
            type=[
                # Text & Code
                "txt", "py", "js", "html", "css", "json", "md", "csv", "xml", "yaml", "yml",
                # Programming
                "java", "c", "cpp", "h", "hpp", "cs", "go", "rs", "rb", "php", "swift", "kt",
                # Config & Data
                "sql", "sh", "bash", "ps1", "dockerfile", "ini", "toml", "cfg", "conf",
                # Images
                "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp",
                # Documents
                "pdf", "doc", "docx", "rtf"
            ],
            key=f"uploader_{st.session_state.uploader_key}",
            label_visibility="collapsed"
        )

# ============ FILE UPLOAD HANDLER ============

if uploaded and not st.session_state.processing_upload:
    st.session_state.pending_upload = uploaded
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(int(st.session_state.uploader_key) + 1)
    st.rerun()

if st.session_state.pending_upload and st.session_state.processing_upload:
    file_obj = st.session_state.pending_upload
    filename = file_obj.name
    file_key = f"{datetime.now().strftime('%H%M%S')}_{filename}"
    
    try:
        file_bytes = file_obj.read()
        
        if file_obj.type and file_obj.type.startswith("image/"):
            st.session_state.uploaded_files[file_key] = {
                "type": "image", "name": filename, "bytes": file_bytes, "mime": file_obj.type
            }
            st.session_state.messages.append({
                "role": "user", "content": f"🖼️ {filename}",
                "metadata": {"type": "image_upload", "file_key": file_key}
            })
            with st.chat_message("user"):
                st.image(file_bytes, use_container_width=True)
            response = f"🖼️ **{filename}** received ({len(file_bytes)} bytes). Ask me to analyze it."
        else:
            try:
                text_content = file_bytes.decode('utf-8', errors='ignore')
            except:
                text_content = f"[Binary file: {len(file_bytes)} bytes]"
            
            st.session_state.uploaded_files[file_key] = {
                "type": "text", "name": filename, "content": text_content, "size": len(text_content)
            }
            st.session_state.messages.append({
                "role": "user", "content": f"📎 {filename}",
                "metadata": {"type": "file", "file_key": file_key}
            })
            with st.chat_message("user"):
                st.markdown(f"📎 **{filename}**")
                with st.expander("Preview"):
                    ext = filename.split('.')[-1] if '.' in filename else 'text'
                    st.code(text_content[:2000], language=ext)
                st.download_button("⬇️ Download", data=file_bytes, file_name=filename, key=f"dl_up_{file_key}")
            response = f"📄 **{filename}** loaded ({len(text_content)} chars). Use `/analyze` to inspect."
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
    
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# ============ MESSAGE RENDERER WITH KIMI-STYLE ACTIONS ============

def render_message_actions(msg_idx: int, content: str, msg_type: str = "text"):
    """Render action buttons below each message."""
    cols = st.columns([1, 1, 1, 1, 6])
    
    with cols[0]:
        if st.button("📋", key=f"copy_{msg_idx}", help="Copy to clipboard"):
            st.toast("Copied!")
    
    with cols[1]:
        if st.button("🔊", key=f"speak_{msg_idx}", help="Read aloud"):
            st.audio(f"https://gen.pollinations.ai/audio/{requests.utils.quote(content[:500])}?voice=nova")
    
    with cols[2]:
        if st.button("🔄", key=f"regen_{msg_idx}", help="Regenerate"):
            st.session_state.messages = st.session_state.messages[:msg_idx]
            st.rerun()
    
    with cols[3]:
        if st.button("👍", key=f"like_{msg_idx}", help="Good response"):
            st.toast("Thanks for feedback!")

# ============ MAIN CHAT DISPLAY ============

st.markdown('<div style="max-width: 800px; margin: 0 auto;">', unsafe_allow_html=True)

for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "system":
        continue
    
    metadata = msg.get("metadata", {})
    msg_type = metadata.get("type", "text")
    
    with st.chat_message(msg["role"]):
        # Content rendering
        if msg_type == "image":
            st.image(msg["content"], use_container_width=True)
            st.caption("🎨 Generated")
            # Download
            try:
                import requests
                img_data = requests.get(msg["content"]).content
                st.download_button("⬇️ Save", img_data, f"denlab_{idx}.png", "image/png", key=f"dl_img_{idx}")
            except:
                pass
                
        elif msg_type == "image_upload":
            file_key = metadata.get("file_key")
            if file_key and file_key in st.session_state.uploaded_files:
                fd = st.session_state.uploaded_files[file_key]
                st.image(fd["bytes"], use_container_width=True)
                st.caption(f"📎 {fd['name']}")
            else:
                st.markdown(msg["content"])
                
        elif msg_type == "file":
            st.markdown(msg["content"])
            file_key = metadata.get("file_key")
            if file_key and file_key in st.session_state.uploaded_files:
                fd = st.session_state.uploaded_files[file_key]
                with st.expander("📄 View content"):
                    st.code(fd["content"][:3000], language=fd["name"].split('.')[-1] if '.' in fd["name"] else 'text')
        
        elif msg_type == "agent_trace":
            st.markdown(msg["content"])
            with st.expander("🔍 Trace", expanded=False):
                for trace in metadata.get("traces", []):
                    st.markdown(f"**Step {trace.get('step', '?')}**")
                    for tc in trace.get("tool_calls", []):
                        icon = "✅" if tc.get("status") == "success" else "❌"
                        st.markdown(f"{icon} `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
                        with st.expander("Details"):
                            st.json({"args": tc.get("arguments", {}), "result": str(tc.get("result", ""))[:400]})
        
        elif msg_type == "code_execution":
            st.markdown(msg["content"])
            code = metadata.get("code", "")
            if code:
                st.download_button("⬇️ Save Code", code, "code.py", "text/x-python", key=f"dl_code_{idx}")
        
        else:
            # Regular text - render markdown
            st.markdown(msg["content"])
        
        # Action buttons for assistant messages
        if msg["role"] == "assistant" and idx > 0:
            render_message_actions(idx, msg["content"], msg_type)

st.markdown('</div>', unsafe_allow_html=True)

# ============ CHAT INPUT ============

placeholder = "Message DenLab..." if not st.session_state.agent_mode else "🤖 Agent mode: Describe task..."

if prompt := st.chat_input(placeholder):
    
    # ============ COMMANDS ============
    
    if prompt.lower().startswith("/imagine"):
        desc = prompt[8:].strip()
        if desc:
            st.session_state.messages.append({"role": "user", "content": f"🎨 {desc}", "metadata": {"type": "image_request"}})
            with st.chat_message("user"):
                st.markdown(f"🎨 **{desc}**")
            with st.chat_message("assistant"):
                with st.spinner("Creating..."):
                    client = PollinationsClient()
                    img_url = client.generate_image(desc)
                    st.image(img_url, caption=desc, use_container_width=True)
                    try:
                        import requests
                        img_data = requests.get(img_url).content
                        st.download_button("⬇️ Save Image", img_data, f"denlab_{desc[:20]}.png", "image/png")
                    except:
                        pass
                    response = img_url
            st.session_state.messages.append({"role": "assistant", "content": response, "metadata": {"type": "image"}})
            st.rerun()
    
    elif prompt.lower().startswith("/research"):
        topic = prompt[9:].strip()
        if topic:
            st.session_state.messages.append({"role": "user", "content": f"🔬 {topic}"})
            with st.chat_message("assistant"):
                with st.status("🔬 Researching...", expanded=True) as status:
                    result = deep_research(topic, depth=2)
                    data = json.loads(result)
                    status.update(label="Done!", state="complete")
                    
                    st.markdown(f"**{data['topic']}** — {data['total_sources']} sources")
                    for f in data['findings'][:3]:
                        with st.expander(f"📄 {f['title'][:40]}..."):
                            st.markdown(f["content"][:600] + "...")
                    
                    # Export
                    md = f"# Research: {topic}\n\n"
                    for f in data['findings']:
                        md += f"## {f['title']}\nSource: {f['source']}\n\n{f['content']}\n\n---\n\n"
                    st.download_button("⬇️ Export Research", md, f"research_{topic[:20]}.md", "text/markdown")
                    
                    synthesis = f"Research on **{topic}** complete. Found {data['total_sources']} sources. Key insights available above."
                    st.markdown(synthesis)
                    st.session_state.messages.append({"role": "assistant", "content": synthesis, "metadata": {"type": "research_result", "data": data}})
            st.rerun()
    
    elif prompt.lower().startswith("/code"):
        task = prompt[5:].strip()
        if task:
            st.session_state.messages.append({"role": "user", "content": f"💻 {task}"})
            with st.chat_message("assistant"):
                with st.status("💻 Coding...", expanded=True):
                    client = PollinationsClient()
                    code_prompt = f"Write Python for: {task}\nReturn ONLY code, no explanation."
                    code = client.chat([{"role": "system", "content": "Python expert. Only code."}, {"role": "user", "content": code_prompt}], model=st.session_state.model)["content"]
                    code = code.replace("```python", "").replace("```", "").strip()
                    
                    st.code(code, language="python")
                    st.download_button("⬇️ Save", code, "script.py", "text/x-python")
                    
                    result = execute_code(code)
                    data = json.loads(result)
                    if data.get("success"):
                        st.success("✅ Success")
                        if data.get("stdout"):
                            st.text(data["stdout"])
                    else:
                        st.error(f"❌ {data.get('stderr', data.get('error'))}")
                    
                    response = f"```python\n{code}\n```\n\n**Output:**\n```\n{data.get('stdout', data.get('stderr', 'No output'))}\n```"
                    st.session_state.messages.append({"role": "assistant", "content": response, "metadata": {"type": "code_execution", "code": code, "result": data}})
            st.rerun()
    
    elif prompt.lower().startswith("/analyze") or prompt.lower().startswith("analyse"):
        if st.session_state.uploaded_files:
            latest = list(st.session_state.uploaded_files.values())[-1]
            st.session_state.messages.append({"role": "user", "content": f"🔍 Analyze: {latest['name']}"})
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    if latest["type"] == "text":
                        client = PollinationsClient()
                        analysis = client.chat([
                            {"role": "system", "content": "Code analysis expert. Be concise."},
                            {"role": "user", "content": f"Analyze {latest['name']}:\n\n{latest['content'][:4000]}\n\nProvide: 1) Purpose 2) Structure 3) Issues 4) Improvements"}
                        ], model=st.session_state.model)["content"]
                        st.markdown(analysis)
                        st.download_button("⬇️ Save Analysis", analysis, f"analysis_{latest['name']}.md", "text/markdown")
                        st.session_state.messages.append({"role": "assistant", "content": analysis})
                    else:
                        st.markdown("Image analysis requires vision model.")
                        st.session_state.messages.append({"role": "assistant", "content": "Image analysis requires vision model."})
            st.rerun()
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                st.markdown("No files uploaded. Use sidebar to upload first.")
            st.session_state.messages.append({"role": "assistant", "content": "No files uploaded. Use sidebar to upload first."})
            st.rerun()
    
    # ============ AGENT MODE ============
    elif st.session_state.agent_mode:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            if st.session_state.swarm_mode:
                with st.status("🐝 Swarm executing...", expanded=True) as status:
                    try:
                        orchestrator = SwarmOrchestrator(max_parallel=3)
                        planner = TaskPlanner()
                        plan = planner.create_plan(prompt)
                        
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
                        
                        def on_progress(subtask):
                            status.write(f"🔄 {subtask.agent_type}: {subtask.description[:50]}...")
                        orchestrator.on_progress = on_progress
                        
                        result = asyncio.run(orchestrator.execute(prompt, plan))
                        status.update(label="✅ Complete!", state="complete")
                        
                        st.markdown("## 🐝 Results")
                        if result.get("subtasks"):
                            cols = st.columns(min(len(result["subtasks"]), 3))
                            for idx, (st_id, st_data) in enumerate(result["subtasks"].items()):
                                with cols[idx % 3]:
                                    icon = "✅" if st_data.get("status") == "complete" else "❌"
                                    st.metric(f"{icon} {st_id}", f"{st_data.get('duration', 0):.1f}s")
                        
                        synthesis = result.get("synthesis", "Done.")
                        st.markdown(synthesis)
                        st.download_button("⬇️ Export JSON", json.dumps(result, indent=2, default=str), "swarm_result.json", "application/json")
                        
                        st.session_state.messages.append({
                            "role": "assistant", "content": synthesis,
                            "metadata": {"type": "agent_trace", "subtasks": result.get("subtasks", {})}
                        })
                    except Exception as e:
                        st.error(f"Swarm error: {str(e)}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
            else:
                agent = get_agent(st.session_state.model)
                agent.model = st.session_state.model
                traces = []
                def on_step(trace):
                    traces.append(trace)
                agent.on_step = on_step
                
                with st.status("🤖 Agent executing...", expanded=True) as status:
                    try:
                        async def run_updates():
                            task = asyncio.create_task(agent.run(prompt))
                            while not task.done():
                                if agent.traces:
                                    latest = agent.traces[-1]
                                    status.write(f"Step {latest.step}: {latest.thought[:60]}...")
                                await asyncio.sleep(0.5)
                            return await task
                        
                        response = asyncio.run(run_updates())
                        status.update(label="✅ Done!", state="complete")
                        
                        if traces and st.session_state.show_traces:
                            with st.expander("🔍 Trace", expanded=False):
                                for trace in traces:
                                    st.markdown(f"**Step {trace.step}**")
                                    if trace.thought:
                                        st.markdown(f"💭 {trace.thought[:150]}")
                                    for tc in trace.tool_calls:
                                        icon = "✅" if tc.status == "success" else "❌"
                                        st.markdown(f"{icon} `{tc.name}` ({tc.duration_ms:.0f}ms)")
                        
                        st.markdown(response)
                        st.download_button("⬇️ Report", f"# Agent Report\n\nTask: {prompt}\n\n{response}", "report.md", "text/markdown")
                        
                        st.session_state.messages.append({
                            "role": "assistant", "content": response,
                            "metadata": {
                                "type": "agent_trace",
                                "traces": [{"step": t.step, "thought": t.thought, "tool_calls": [{"name": tc.name, "arguments": tc.arguments, "result": str(tc.result)[:400], "status": tc.status, "duration_ms": tc.duration_ms} for tc in t.tool_calls]} for t in traces]
                            }
                        })
                    except Exception as e:
                        st.error(f"Agent error: {str(e)}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
        st.rerun()
    
    # ============ NORMAL CHAT ============
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                client = PollinationsClient()
                msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] != "system"]
                msgs.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                response = client.chat(msgs, model=st.session_state.model)["content"]
            st.markdown(response)
            st.download_button("⬇️ Save", response, "response.md", "text/markdown", key=f"dl_{len(st.session_state.messages)}")
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
