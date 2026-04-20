"""DenLab v3.0 - Clean UI"""
import streamlit as st
import asyncio
import json
import requests
from datetime import datetime

st.set_page_config(page_title="DenLab", page_icon="🧪", layout="wide")

from assets.custom_css import DARK_THEME
st.markdown(DARK_THEME, unsafe_allow_html=True)

from core.api_client import PollinationsClient
from config.settings import MODELS, SYSTEM_PROMPT
from agents.base_agent import BaseAgent
from agents.orchestrator import SwarmOrchestrator
from agents.planner import TaskPlanner
from agents.tools import web_search, deep_research, execute_code, fetch_url, read_file, write_file

# ============ AGENT ============

class DenLabAgent(BaseAgent):
    def __init__(self, name="Agent", model="openai"):
        super().__init__(name, model, max_steps=15)
        self.client = PollinationsClient()
        for tool in [
            ("web_search", web_search, "Search web", {"query": {"type": "string"}}),
            ("deep_research", deep_research, "Deep research", {"topic": {"type": "string"}}),
            ("execute_code", execute_code, "Run Python", {"code": {"type": "string"}}),
            ("fetch_url", fetch_url, "Fetch URL", {"url": {"type": "string"}}),
            ("read_file", read_file, "Read file", {"path": {"type": "string"}}),
            ("write_file", write_file, "Write file", {"path": {"type": "string"}, "content": {"type": "string"}})
        ]:
            self.register_tool(*tool)
    
    async def _llm_call(self, messages, tools=None):
        return self.client.chat(messages=messages, model=self.model, tools=tools, temperature=0.7)

def get_agent(model="openai"):
    if "agent" not in st.session_state:
        st.session_state.agent = DenLabAgent(model=model)
    return st.session_state.agent

# ============ STATE ============

def init():
    defaults = {
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "assistant", "content": "**DenLab ready.**\n\nCommands: `/imagine`, `/research`, `/code`, `/analyze`"}],
        "model": "openai", "agent_mode": False, "swarm_mode": False,
        "uploader_key": "0", "pending_upload": None, "processing_upload": False,
        "current_session": "Main", "sessions": {}, "uploaded_files": {}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

# ============ SIDEBAR ============

with st.sidebar:
    st.markdown("### 🧪 DenLab")
    st.caption("v3.0")
    
    st.markdown("**Model**")
    model_names = list(MODELS.keys())
    idx = list(MODELS.values()).index(st.session_state.model) if st.session_state.model in MODELS.values() else 0
    choice = st.selectbox("", model_names, index=idx, label_visibility="collapsed")
    st.session_state.model = MODELS[choice]
    
    st.markdown("**Mode**")
    st.session_state.agent_mode = st.toggle("🤖 Agent", value=st.session_state.agent_mode)
    if st.session_state.agent_mode:
        st.session_state.swarm_mode = st.toggle("🐝 Swarm", value=st.session_state.swarm_mode)
    
    st.markdown("**Sessions**")
    c1, c2 = st.columns([3, 1])
    with c1:
        new_name = st.text_input("", placeholder="New...", label_visibility="collapsed")
    with c2:
        if st.button("➕", use_container_width=True):
            name = new_name or f"Session {len(st.session_state.sessions)+1}"
            st.session_state.sessions[st.session_state.current_session] = st.session_state.messages.copy()
            st.session_state.current_session = name
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "assistant", "content": f"**{name}** started."}]
            st.rerun()
    
    if st.session_state.sessions:
        for sname in list(st.session_state.sessions.keys())[-6:]:
            c1, c2 = st.columns([5, 1])
            with c1:
                if st.button(f"📁 {sname[:20]}", use_container_width=True, key=f"load_{sname}"):
                    st.session_state.current_session = sname
                    st.session_state.messages = st.session_state.sessions[sname]
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"del_{sname}"):
                    del st.session_state.sessions[sname]
                    st.rerun()
    
    if st.button("📥 Export", use_container_width=True):
        txt = "\n\n".join([f"**{m['role'].upper()}**: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
        st.download_button("Download", txt, f"chat.md", use_container_width=True)
    
    st.markdown("**Upload**")
    uploaded = st.file_uploader("", type=[
        "txt", "py", "js", "html", "css", "json", "md", "csv", "xml", "yaml", "yml",
        "java", "c", "cpp", "h", "hpp", "cs", "go", "rs", "rb", "php", "swift", "kt",
        "sql", "sh", "ps1", "ini", "toml", "cfg", "conf",
        "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "pdf"
    ], key=f"up_{st.session_state.uploader_key}", label_visibility="collapsed")

# ============ UPLOAD HANDLER ============

if uploaded and not st.session_state.processing_upload:
    st.session_state.pending_upload = uploaded
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(int(st.session_state.uploader_key) + 1)
    st.rerun()

if st.session_state.pending_upload and st.session_state.processing_upload:
    f = st.session_state.pending_upload
    fname = f.name
    fkey = f"{datetime.now().strftime('%H%M%S')}_{fname}"
    
    try:
        fb = f.read()
        if f.type and f.type.startswith("image/"):
            st.session_state.uploaded_files[fkey] = {"type": "image", "name": fname, "bytes": fb, "mime": f.type}
            st.session_state.messages.append({"role": "user", "content": f"🖼️ {fname}", "meta": {"type": "img_up", "key": fkey}})
            with st.chat_message("user"):
                st.image(fb, use_container_width=True)
            resp = f"🖼️ **{fname}** received. Ask me to analyze it."
        else:
            try:
                txt = fb.decode('utf-8', errors='ignore')
            except:
                txt = f"[Binary: {len(fb)} bytes]"
            st.session_state.uploaded_files[fkey] = {"type": "text", "name": fname, "content": txt, "size": len(txt)}
            st.session_state.messages.append({"role": "user", "content": f"📎 {fname}", "meta": {"type": "file", "key": fkey}})
            with st.chat_message("user"):
                st.markdown(f"📎 **{fname}**")
                with st.expander("Preview"):
                    st.code(txt[:1500], language=fname.split('.')[-1] if '.' in fname else 'text')
                st.download_button("⬇️", fb, fname, key=f"dl_{fkey}")
            resp = f"📄 **{fname}** loaded ({len(txt)} chars). Use `/analyze`."
        
        st.session_state.messages.append({"role": "assistant", "content": resp})
    except Exception as e:
        st.error(f"Upload error: {e}")
    
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# ============ MESSAGE ACTIONS - COMPACT ============

def msg_actions(idx, content, msg_type="text"):
    """Render compact action buttons below message."""
    cols = st.columns([1, 1, 1, 1, 8])
    
    with cols[0]:
        if st.button("📋", key=f"cp_{idx}", help="Copy"):
            st.toast("Copied!")
    
    with cols[1]:
        if st.button("🔊", key=f"sp_{idx}", help="Speak"):
            try:
                st.audio(f"https://gen.pollinations.ai/audio/{requests.utils.quote(content[:400])}?voice=nova")
            except:
                pass
    
    with cols[2]:
        if st.button("🔄", key=f"rg_{idx}", help="Regenerate"):
            st.session_state.messages = st.session_state.messages[:idx]
            st.rerun()
    
    with cols[3]:
        if st.button("👍", key=f"lk_{idx}", help="Like"):
            st.toast("Thanks!")

# ============ RENDER MESSAGES ============

for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "system":
        continue
    
    meta = msg.get("meta", {})
    mtype = meta.get("type", "text")
    
    with st.chat_message(msg["role"]):
        if mtype == "image":
            st.image(msg["content"], use_container_width=True)
            st.caption("🎨 Generated")
            try:
                img_data = requests.get(msg["content"]).content
                st.download_button("⬇️ Save", img_data, f"img_{idx}.png", "image/png", key=f"dl_img_{idx}")
            except:
                pass
        
        elif mtype == "img_up":
            k = meta.get("key")
            if k and k in st.session_state.uploaded_files:
                fd = st.session_state.uploaded_files[k]
                st.image(fd["bytes"], use_container_width=True)
                st.caption(f"📎 {fd['name']}")
            else:
                st.markdown(msg["content"])
        
        elif mtype == "file":
            st.markdown(msg["content"])
            k = meta.get("key")
            if k and k in st.session_state.uploaded_files:
                fd = st.session_state.uploaded_files[k]
                with st.expander("📄 View"):
                    st.code(fd["content"][:2000], language=fd["name"].split('.')[-1] if '.' in fd["name"] else 'text')
        
        elif mtype == "agent_trace":
            st.markdown(msg["content"])
            with st.expander("🔍 Trace", expanded=False):
                for t in meta.get("traces", []):
                    st.markdown(f"**Step {t.get('step', '?')}**")
                    for tc in t.get("tool_calls", []):
                        icon = "✅" if tc.get("status") == "success" else "❌"
                        st.markdown(f"{icon} `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
                        with st.expander("Details"):
                            st.json({"args": tc.get("arguments", {}), "result": str(tc.get("result", ""))[:300]})
        
        elif mtype == "code":
            st.markdown(msg["content"])
            c = meta.get("code", "")
            if c:
                st.download_button("⬇️ Code", c, "code.py", "text/x-python", key=f"dl_cd_{idx}")
        
        else:
            st.markdown(msg["content"])
        
        # Actions for assistant only
        if msg["role"] == "assistant" and idx > 0:
            msg_actions(idx, msg["content"], mtype)

# ============ INPUT ============

ph = "Message DenLab..." if not st.session_state.agent_mode else "🤖 Agent mode..."

if prompt := st.chat_input(ph):
    
    # /imagine
    if prompt.lower().startswith("/imagine"):
        desc = prompt[8:].strip()
        if desc:
            st.session_state.messages.append({"role": "user", "content": f"🎨 {desc}", "meta": {"type": "img_req"}})
            with st.chat_message("user"):
                st.markdown(f"🎨 **{desc}**")
            with st.chat_message("assistant"):
                with st.spinner("Creating..."):
                    img = PollinationsClient().generate_image(desc)
                    st.image(img, caption=desc, use_container_width=True)
                    try:
                        st.download_button("⬇️ Save", requests.get(img).content, f"{desc[:20]}.png", "image/png")
                    except:
                        pass
                    st.session_state.messages.append({"role": "assistant", "content": img, "meta": {"type": "image"}})
            st.rerun()
    
    # /research
    elif prompt.lower().startswith("/research"):
        topic = prompt[9:].strip()
        if topic:
            st.session_state.messages.append({"role": "user", "content": f"🔬 {topic}"})
            with st.chat_message("assistant"):
                with st.status("🔬 Researching...", expanded=True) as s:
                    data = json.loads(deep_research(topic, 2))
                    s.update(label="Done!", state="complete")
                    st.markdown(f"**{data['topic']}** — {data['total_sources']} sources")
                    for f in data['findings'][:3]:
                        with st.expander(f"📄 {f['title'][:40]}..."):
                            st.markdown(f["content"][:500] + "...")
                    md = f"# Research: {topic}\n\n" + "\n\n".join([f"## {f['title']}\n{f['content']}" for f in data['findings']])
                    st.download_button("⬇️ Export", md, f"research.md", "text/markdown")
                    r = f"Research on **{topic}** complete. {data['total_sources']} sources analyzed."
                    st.markdown(r)
                    st.session_state.messages.append({"role": "assistant", "content": r, "meta": {"type": "research", "data": data}})
            st.rerun()
    
    # /code
    elif prompt.lower().startswith("/code"):
        task = prompt[5:].strip()
        if task:
            st.session_state.messages.append({"role": "user", "content": f"💻 {task}"})
            with st.chat_message("assistant"):
                with st.status("💻 Coding...", expanded=True):
                    c = PollinationsClient().chat([
                        {"role": "system", "content": "Python expert. Only code."},
                        {"role": "user", "content": f"Write Python for: {task}\nOnly code, no explanation."}
                    ], model=st.session_state.model)["content"]
                    c = c.replace("```python", "").replace("```", "").strip()
                    st.code(c, language="python")
                    st.download_button("⬇️ Save", c, "script.py", "text/x-python")
                    res = execute_code(c)
                    d = json.loads(res)
                    out = d.get("stdout", d.get("stderr", "No output"))
                    if d.get("success"):
                        st.success("✅ Success")
                        if out: st.text(out)
                    else:
                        st.error(f"❌ {out}")
                    r = f"```python\n{c}\n```\n\n**Output:**\n```\n{out}\n```"
                    st.session_state.messages.append({"role": "assistant", "content": r, "meta": {"type": "code", "code": c, "result": d}})
            st.rerun()
    
    # /analyze
    elif prompt.lower().startswith("/analyze") or prompt.lower().startswith("analyse"):
        if st.session_state.uploaded_files:
            latest = list(st.session_state.uploaded_files.values())[-1]
            st.session_state.messages.append({"role": "user", "content": f"🔍 {latest['name']}"})
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    if latest["type"] == "text":
                        a = PollinationsClient().chat([
                            {"role": "system", "content": "Code analysis expert. Be concise."},
                            {"role": "user", "content": f"Analyze {latest['name']}:\n\n{latest['content'][:4000]}\n\nProvide: 1) Purpose 2) Structure 3) Issues 4) Improvements"}
                        ], model=st.session_state.model)["content"]
                        st.markdown(a)
                        st.download_button("⬇️ Save", a, f"analysis.md", "text/markdown")
                        st.session_state.messages.append({"role": "assistant", "content": a})
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
    
    # AGENT MODE
    elif st.session_state.agent_mode:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            if st.session_state.swarm_mode:
                with st.status("🐝 Swarm...", expanded=True) as s:
                    try:
                        orch = SwarmOrchestrator(max_parallel=3)
                        plan = TaskPlanner().create_plan(prompt)
                        
                        def make_r():
                            a = DenLabAgent("R", st.session_state.model)
                            a.max_steps = 10
                            return a
                        def make_c():
                            a = DenLabAgent("C", st.session_state.model)
                            a.max_steps = 8
                            return a
                        
                        orch.register_agent("researcher", make_r)
                        orch.register_agent("coder", make_c)
                        orch.register_agent("analyst", make_r)
                        orch.register_agent("writer", make_r)
                        
                        def on_p(sub):
                            s.write(f"🔄 {sub.agent_type}: {sub.description[:50]}...")
                        orch.on_progress = on_p
                        
                        res = asyncio.run(orch.execute(prompt, plan))
                        s.update(label="✅ Done!", state="complete")
                        
                        st.markdown("## 🐝 Results")
                        if res.get("subtasks"):
                            cols = st.columns(min(len(res["subtasks"]), 3))
                            for i, (sid, sd) in enumerate(res["subtasks"].items()):
                                with cols[i % 3]:
                                    icon = "✅" if sd.get("status") == "complete" else "❌"
                                    st.metric(f"{icon} {sid}", f"{sd.get('duration', 0):.1f}s")
                        
                        syn = res.get("synthesis", "Done.")
                        st.markdown(syn)
                        st.download_button("⬇️ JSON", json.dumps(res, indent=2, default=str), "result.json", "application/json")
                        st.session_state.messages.append({"role": "assistant", "content": syn, "meta": {"type": "agent_trace", "subtasks": res.get("subtasks", {})}})
                    except Exception as e:
                        st.error(f"Swarm error: {e}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})
            else:
                agent = get_agent(st.session_state.model)
                agent.model = st.session_state.model
                traces = []
                def on_step(t):
                    traces.append(t)
                agent.on_step = on_step
                
                with st.status("🤖 Agent...", expanded=True) as s:
                    try:
                        async def run_u():
                            task = asyncio.create_task(agent.run(prompt))
                            while not task.done():
                                if agent.traces:
                                    lt = agent.traces[-1]
                                    s.write(f"Step {lt.step}: {lt.thought[:60]}...")
                                await asyncio.sleep(0.5)
                            return await task
                        
                        resp = asyncio.run(run_u())
                        s.update(label="✅ Done!", state="complete")
                        
                        if traces:
                            with st.expander("🔍 Trace", expanded=False):
                                for t in traces:
                                    st.markdown(f"**Step {t.step}**")
                                    if t.thought:
                                        st.markdown(f"💭 {t.thought[:150]}")
                                    for tc in t.tool_calls:
                                        icon = "✅" if tc.status == "success" else "❌"
                                        st.markdown(f"{icon} `{tc.name}` ({tc.duration_ms:.0f}ms)")
                        
                        st.markdown(resp)
                        st.download_button("⬇️ Report", f"# Report\n\nTask: {prompt}\n\n{resp}", "report.md", "text/markdown")
                        
                        st.session_state.messages.append({
                            "role": "assistant", "content": resp,
                            "meta": {
                                "type": "agent_trace",
                                "traces": [{"step": t.step, "thought": t.thought, "tool_calls": [{"name": tc.name, "arguments": tc.arguments, "result": str(tc.result)[:400], "status": tc.status, "duration_ms": tc.duration_ms} for tc in t.tool_calls]} for t in traces]
                            }
                        })
                    except Exception as e:
                        st.error(f"Agent error: {e}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})
        st.rerun()
    
    # NORMAL CHAT
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] != "system"]
                msgs.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                r = PollinationsClient().chat(msgs, model=st.session_state.model)["content"]
            st.markdown(r)
            st.download_button("⬇️ Save", r, "response.md", "text/markdown", key=f"dl_{len(st.session_state.messages)}")
        
        st.session_state.messages.append({"role": "assistant", "content": r})
        st.rerun()
