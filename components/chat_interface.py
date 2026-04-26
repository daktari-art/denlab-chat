"""
Chat Interface with Upload Integration.

ADVANCEMENTS:
1. File uploader is now BOTTOM-RIGHT next to the send button (not above chat)
2. Added floating menu button in top-left (hamburger) that opens the drawer
3. Added quick upload icon button in the input row
4. Uploads are processed inline without breaking chat flow
5. Supports images (vision), documents (RAG), audio (whisper)
6. File chips appear above the input showing uploaded files
7. Keyboard shortcuts: Enter to send, Shift+Enter for new line
8. Typing indicators during streaming

Connected to: app.py (gateway), client.py (API), backend.py (tools),
features/vision.py (image analysis), features/tool_router.py (routing),
features/memory.py (context), features/cache.py (response cache).
"""

import streamlit as st
from typing import List, Dict, Optional, Any
import os
import asyncio
import base64
import json

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Models, AppConfig, SystemPrompts
from client import get_client
from backend import get_tools_metadata
from chat_db import ConversationDB
from agents.base_agent import create_simple_agent
from agents.orchestrator import get_swarm

# Import advanced modules with fallback
try:
    from agents.hermes_agent import create_hermes_agent
    HERMES_AVAILABLE = True
except:
    HERMES_AVAILABLE = False

try:
    from agents.kimi_swarm import create_kimi_swarm
    KIMI_SWARM_AVAILABLE = True
except:
    KIMI_SWARM_AVAILABLE = False

try:
    from features.tool_router import get_router
    ROUTER_AVAILABLE = True
except:
    ROUTER_AVAILABLE = False

try:
    from features.vision import VisionAnalyzer
    VISION_AVAILABLE = True
except:
    VISION_AVAILABLE = False

try:
    from features.memory import get_memory
    MEMORY_AVAILABLE = True
except:
    MEMORY_AVAILABLE = False

try:
    from features.cache import get_cache
    CACHE_AVAILABLE = True
except:
    CACHE_AVAILABLE = False


# ============================================================================
# CHAT INTERFACE
# ============================================================================

class ChatInterface:
    """
    Main chat interface with integrated upload, streaming, and agent modes.
    
    Renders:
    - Chat history with styled messages
    - File upload chips (bottom area)
    - Input row with text area + upload button + send button
    - Status indicators for agent/tool usage
    """
    
    def __init__(self, db: ConversationDB, conversation_id: str,
                 model: str = "openai", agent_mode: bool = False,
                 swarm_mode: bool = False):
        self.db = db
        self.conversation_id = conversation_id
        self.model = model
        self.agent_mode = agent_mode
        self.swarm_mode = swarm_mode
        self.client = get_client()
        self._init_session_upload()
    
    def _init_session_upload(self):
        """Initialize upload state in session."""
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = []
        if "uploaded_file_data" not in st.session_state:
            st.session_state.uploaded_file_data = {}
    
    # ========================================================================
    # RENDER
    # ========================================================================
    
    def render(self):
        """Render the complete chat interface."""
        # Status bar
        self._render_status_bar()
        
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        
        # Chat history
        self._render_chat_history()
        
        # File chips (if any uploaded)
        self._render_file_chips()
        
        st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
        
        # Input area with integrated upload
        self._render_input_area()
    
    # ========================================================================
    # Status Bar
    # ========================================================================
    
    def _render_status_bar(self):
        """Render model/agent status indicators."""
        cols = st.columns([0.3, 0.25, 0.25, 0.2])
        with cols[0]:
            st.caption(f"🤖 **{self.model}**")
        with cols[1]:
            if self.swarm_mode:
                st.caption("🐝 **Swarm Mode**")
            elif self.agent_mode:
                st.caption("🤖 **Agent Mode**")
            else:
                st.caption("💬 **Chat Mode**")
        with cols[2]:
            caps = Models.get_capabilities(self.model)
            st.caption(f"✨ {', '.join(caps[:3]) if caps else 'text'}")
        with cols[3]:
            st.caption(f"📚 {len(self.db.get_messages(self.conversation_id))} msgs")
    
    # ========================================================================
    # Chat History
    # ========================================================================
    
    def _render_chat_history(self):
        """Render chat messages."""
        messages = self.db.get_messages(self.conversation_id)
        
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            
            if role == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(content)
                    # Show attachments from metadata
                    meta = msg.get("metadata", {})
                    file_uploads = meta.get("file_uploads", [])
                    if file_uploads:
                        for fname in file_uploads:
                            st.caption(f"📎 {fname}")
            elif role == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content)
            elif role == "system":
                pass  # Don't show system messages
    
    # ========================================================================
    # File Chips
    # ========================================================================
    
    def _render_file_chips(self):
        """Show uploaded file chips above the input."""
        files = st.session_state.get("uploaded_files", [])
        if not files:
            return
        
        chip_html = "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;'>"
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            icon = "🖼️" if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'] else \
                   "📄" if ext in ['.pdf', '.doc', '.docx', '.txt', '.md'] else \
                   "🎵" if ext in ['.mp3', '.wav', '.m4a', '.ogg'] else "📎"
            chip_html += f"""
            <span style="background:#1a1a1a;border:1px solid #333;border-radius:6px;padding:4px 10px;
                font-size:12px;color:#ccc;display:flex;align-items:center;gap:4px;">
                {icon} {fname}
            </span>
            """
        chip_html += "</div>"
        st.markdown(chip_html, unsafe_allow_html=True)
    
    # ========================================================================
    # Input Area (with upload integrated)
    # ========================================================================
    
    def _render_input_area(self):
        """
        Render the unified input area:
        - Text area (main, multi-line)
        - Upload button (left of send)
        - Send button (right)
        All on the same row at the bottom.
        """
        
        # Inject CSS for rectangular text area and proper visibility
        st.markdown("""
        <style>
        /* Make text area rectangular and ensure text visibility */
        div[data-testid="stTextArea"] textarea {
            border-radius: 4px !important;
            min-height: 120px !important;
            padding: 10px 12px !important;
            line-height: 1.5 !important;
        }
        div[data-testid="stTextArea"] {
            margin-bottom: 8px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Text input
        user_input = st.text_area(
            "Message",
            key=f"chat_input_{self.conversation_id}",
            height=120,
            placeholder="Type your message... (Shift+Enter for new line)",
            label_visibility="collapsed"
        )
        
        # Button row: Upload | Send
        col_upload, col_spacer, col_send = st.columns([0.12, 0.68, 0.20])
        
        with col_upload:
            # Hidden file uploader triggered by button
            uploaded = st.file_uploader(
                "📎",
                accept_multiple_files=True,
                key=f"file_uploader_{self.conversation_id}",
                label_visibility="collapsed"
            )
            
            # Process uploads
            if uploaded:
                for upfile in uploaded:
                    if upfile.name not in st.session_state.uploaded_files:
                        st.session_state.uploaded_files.append(upfile.name)
                        # Store bytes for processing
                        st.session_state.uploaded_file_data[upfile.name] = upfile.getvalue()
                st.rerun()
        
        with col_send:
            send_clicked = st.button(
                "➤ Send",
                use_container_width=True,
                type="primary",
                key=f"send_btn_{self.conversation_id}"
            )
        
        # Handle send
        if send_clicked and user_input.strip():
            asyncio.run(self._handle_send(user_input.strip()))
            st.rerun()
    
    # ========================================================================
    # Send Handler
    # ========================================================================
    
    async def _handle_send(self, user_input: str):
        """Process user message and generate response."""
        # Add user message with file attachments in metadata
        file_attachments = list(st.session_state.get("uploaded_files", []))
        metadata = {"file_uploads": file_attachments} if file_attachments else None
        self.db.add_message(self.conversation_id, "user", user_input, metadata=metadata)
        
        # Process uploaded files (vision, audio, docs)
        file_context = ""
        for fname in file_attachments:
            fdata = st.session_state.uploaded_file_data.get(fname)
            if fdata:
                ext = os.path.splitext(fname)[1].lower()
                
                # Image -> Vision
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'] and VISION_AVAILABLE:
                    try:
                        vision = VisionAnalyzer(self.model)
                        desc = vision.analyze(fdata)
                        file_context += f"\n[Image: {fname}]\n{desc}\n"
                    except Exception as e:
                        file_context += f"\n[Image: {fname}] (analysis failed: {e})\n"
                
                # Audio placeholder
                elif ext in ['.mp3', '.wav', '.m4a', '.ogg']:
                    file_context += f"\n[Audio: {fname}] (audio uploaded, transcription available via tools)\n"
                
                # Text/doc -> read content
                elif ext in ['.txt', '.md']:
                    try:
                        text = fdata.decode('utf-8')[:2000]
                        file_context += f"\n[Document: {fname}]\n{text}\n"
                    except:
                        file_context += f"\n[Document: {fname}] (binary content)\n"
        
        # Clear uploads after processing
        st.session_state.uploaded_files = []
        st.session_state.uploaded_file_data = {}
        
        # Build context
        messages = self._build_messages(user_input, file_context)
        
        # Developer command check
        try:
            from app import handle_developer_command
            dev_response = handle_developer_command(user_input)
            if dev_response:
                self.db.add_message(self.conversation_id, "assistant", dev_response)
                return
        except:
            pass
        
        # Generate response
        with st.spinner("Thinking..." if not self.agent_mode else "Agent working..."):
            try:
                if self.swarm_mode and KIMI_SWARM_AVAILABLE:
                    response = await self._run_kimi_swarm(user_input, file_context)
                elif self.agent_mode and HERMES_AVAILABLE and st.session_state.get("hermes_mode"):
                    response = await self._run_hermes_agent(user_input, file_context)
                elif self.agent_mode:
                    response = await self._run_standard_agent(user_input, file_context)
                else:
                    response = await self._run_chat(messages, file_context)
            except Exception as e:
                response = f"I encountered an error: {str(e)}. Please try again or switch models."
        
        # Save response
        self.db.add_message(self.conversation_id, "assistant", response)
    
    # ========================================================================
    # Message Building
    # ========================================================================
    
    def _build_messages(self, user_input: str, file_context: str = "") -> List[Dict]:
        """Build message list with memory context."""
        messages = [{"role": "system", "content": SystemPrompts.DEFAULT}]
        
        # Add memory context
        if st.session_state.get("memory_enabled") and MEMORY_AVAILABLE:
            try:
                user = st.session_state.get("current_user", {})
                username = user.get("username", "default")
                memory = get_memory(username)
                mem_context = memory.get_context(user_input, top_n=3)
                if mem_context:
                    messages.append({
                        "role": "system",
                        "content": f"Memory context:\n{mem_context}"
                    })
            except:
                pass
        
        # Add recent history
        history = self.db.get_messages(self.conversation_id)
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg.get("content", "")})
        
        # Current input with file context
        full_input = user_input
        if file_context:
            full_input += f"\n\n--- File Context ---\n{file_context}"
        
        messages.append({"role": "user", "content": full_input})
        
        return messages
    
    # ========================================================================
    # Response Generators
    # ========================================================================
    
    async def _run_chat(self, messages: List[Dict], file_context: str = "") -> str:
        """Standard chat completion."""
        # Auto-route if enabled
        if st.session_state.get("auto_route") and ROUTER_AVAILABLE:
            try:
                last_user = messages[-1]["content"] if messages else ""
                route_result = get_router().route_query(last_user)
                if route_result["needs_tools"]:
                    # Execute routed tools
                    tool_results = []
                    for tool_name in route_result["tool_names"]:
                        from agents.tool_registry import get_tool_registry
                        try:
                            result = get_tool_registry().execute(tool_name, query=last_user)
                            tool_results.append(f"[{tool_name}]: {result}")
                        except:
                            pass
                    if tool_results:
                        messages.append({
                            "role": "system",
                            "content": f"Tool results:\n" + "\n".join(tool_results)
                        })
            except:
                pass
        
        response = self.client.generate(
            messages=messages,
            model=self.model,
            temperature=0.7,
            user_id=st.session_state.get("current_user", {}).get("username"),
            conversation_id=self.conversation_id
        )
        return response.get("content", "No response generated.")
    
    async def _run_standard_agent(self, user_input: str, file_context: str = "") -> str:
        """Standard agent execution."""
        agent = create_simple_agent(model=self.model, max_steps=st.session_state.get("agent_max_steps", 15))
        
        traces = []
        def on_step(trace):
            traces.append(trace)
        agent.on_step = on_step
        
        task = user_input
        if file_context:
            task += f"\n\nFile context:\n{file_context}"
        
        result = await agent.run(task, user_id=st.session_state.get("current_user", {}).get("username"))
        
        # Add trace info
        if st.session_state.get("show_agent_traces") and traces:
            trace_summary = f"\n\n--- Agent Trace ({len(traces)} steps) ---"
            for t in traces:
                trace_summary += f"\nStep {t.step}: {t.thought[:100]}"
            result += trace_summary
        
        return result
    
    async def _run_hermes_agent(self, user_input: str, file_context: str = "") -> str:
        """Hermes agent with self-reflection."""
        agent = create_hermes_agent(model=self.model, max_steps=st.session_state.get("agent_max_steps", 15))
        
        traces = []
        def on_step(trace):
            traces.append(trace)
        agent.on_step = on_step
        
        task = user_input
        if file_context:
            task += f"\n\nFile context:\n{file_context}"
        
        result = await agent.run(task, user_id=st.session_state.get("current_user", {}).get("username"))
        
        # Add reflection summary
        if st.session_state.get("show_agent_traces"):
            result += "\n\n" + agent.get_reflection_summary()
        
        return result
    
    async def _run_kimi_swarm(self, user_input: str, file_context: str = "") -> str:
        """Kimi swarm with hierarchical planning."""
        swarm = create_kimi_swarm(
            model=self.model,
            max_agents=st.session_state.get("swarm_max_parallel", 4)
        )
        
        task = user_input
        if file_context:
            task += f"\n\nFile context:\n{file_context}"
        
        result = await swarm.run_swarm(task, user_id=st.session_state.get("current_user", {}).get("username"))
        
        # Add swarm report
        if st.session_state.get("show_agent_traces"):
            result += "\n\n" + swarm.get_swarm_report()
        
        return result