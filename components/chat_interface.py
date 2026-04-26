"""
Chat Interface with Upload Integration.
Uses fixed positioning for input and menu so they don't scroll away.
"""

import streamlit as st
from typing import List, Dict, Optional, Any
import os
import asyncio
import json

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Models, AppConfig, SystemPrompts
from client import get_client
from chat_db import ConversationDB
from agents.base_agent import create_simple_agent

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


class ChatInterface:
    """Main chat interface with fixed input area."""
    
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
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = []
        if "uploaded_file_data" not in st.session_state:
            st.session_state.uploaded_file_data = {}
        if "message_counter" not in st.session_state:
            st.session_state.message_counter = 0
    
    # ========================================================================
    # RENDER
    # ========================================================================
    
    def render(self):
        """Render the complete chat interface."""
        # Inject CSS for fixed input and proper scrolling
        st.markdown("""
        <style>
        /* Fixed input container at bottom of viewport */
        .fixed-bottom {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            background: #0d0d0d !important;
            z-index: 1000 !important;
            padding: 12px 20px 20px 20px !important;
            border-top: 1px solid #1a1a1a !important;
        }
        /* Add bottom padding to main content so chat doesn't hide behind fixed input */
        .main .block-container {
            padding-bottom: 200px !important;
        }
        /* Text area styling */
        div[data-testid="stTextArea"] textarea {
            border-radius: 8px !important;
            min-height: 60px !important;
            max-height: 150px !important;
            padding: 10px 12px !important;
            background: #1a1a1a !important;
            color: #e0e0e0 !important;
            border: 1px solid #333 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Status bar
        self._render_status_bar()
        
        # Chat history
        self._render_chat_history()
        
        # Spacer to push content above fixed input
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        # Fixed input area at bottom
        st.markdown('<div class="fixed-bottom">', unsafe_allow_html=True)
        self._render_input_area()
        st.markdown('</div>', unsafe_allow_html=True)
    
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
    
    def _render_chat_history(self):
        """Render chat messages."""
        messages = self.db.get_messages(self.conversation_id)
        
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            
            if role == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(content)
            elif role == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content)
    
    def _render_input_area(self):
        """Render the input area with upload and send."""
        # Use a counter-based key so it resets after sending
        msg_count = st.session_state.get("message_counter", 0)
        
        user_input = st.text_area(
            "Message",
            key=f"chat_input_{self.conversation_id}_{msg_count}",
            height=68,
            placeholder="Type your message...",
            label_visibility="collapsed"
        )
        
        col_upload, col_spacer, col_send = st.columns([0.1, 0.7, 0.2])
        
        with col_upload:
            uploaded = st.file_uploader(
                "📎",
                accept_multiple_files=True,
                key=f"file_uploader_{self.conversation_id}_{msg_count}",
                label_visibility="collapsed"
            )
            if uploaded:
                for upfile in uploaded:
                    if upfile.name not in st.session_state.uploaded_files:
                        st.session_state.uploaded_files.append(upfile.name)
                        st.session_state.uploaded_file_data[upfile.name] = upfile.getvalue()
                st.rerun()
        
        with col_send:
            send_clicked = st.button(
                "➤ Send",
                use_container_width=True,
                type="primary",
                key=f"send_btn_{self.conversation_id}_{msg_count}"
            )
        
        if send_clicked and user_input.strip():
            # Increment counter to reset the text area on next render
            st.session_state.message_counter += 1
            asyncio.run(self._handle_send(user_input.strip()))
            st.rerun()
    
    async def _handle_send(self, user_input: str):
        """Process user message and generate response."""
        file_attachments = list(st.session_state.get("uploaded_files", []))
        metadata = {"file_uploads": file_attachments} if file_attachments else None
        self.db.add_message(self.conversation_id, "user", user_input, metadata=metadata)
        
        file_context = ""
        for fname in file_attachments:
            fdata = st.session_state.uploaded_file_data.get(fname)
            if fdata:
                ext = os.path.splitext(fname)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'] and VISION_AVAILABLE:
                    try:
                        vision = VisionAnalyzer()
                        desc = vision.analyze(fdata)
                        file_context += f"\n[Image: {fname}]\n{desc}\n"
                    except:
                        pass
                elif ext in ['.txt', '.md']:
                    try:
                        text = fdata.decode('utf-8')[:2000]
                        file_context += f"\n[Document: {fname}]\n{text}\n"
                    except:
                        pass
        
        st.session_state.uploaded_files = []
        st.session_state.uploaded_file_data = {}
        
        messages = self._build_messages(user_input, file_context)
        
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
        
        self.db.add_message(self.conversation_id, "assistant", response)
    
    def _build_messages(self, user_input: str, file_context: str = "") -> List[Dict]:
        messages = [{"role": "system", "content": SystemPrompts.DEFAULT}]
        
        if st.session_state.get("memory_enabled") and MEMORY_AVAILABLE:
            try:
                user = st.session_state.get("current_user", {})
                username = user.get("username", "default")
                memory = get_memory(username)
                mem_context = memory.get_context(user_input, top_n=3)
                if mem_context:
                    messages.append({"role": "system", "content": f"Memory context:\n{mem_context}"})
            except:
                pass
        
        history = self.db.get_messages(self.conversation_id)
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg.get("content", "")})
        
        full_input = user_input
        if file_context:
            full_input += f"\n\n--- File Context ---\n{file_context}"
        
        messages.append({"role": "user", "content": full_input})
        return messages
    
    async def _run_chat(self, messages: List[Dict], file_context: str = "") -> str:
        response = self.client.generate(
            messages=messages,
            model=self.model,
            temperature=0.7,
            user_id=st.session_state.get("current_user", {}).get("username"),
            conversation_id=self.conversation_id
        )
        return response.get("content", "No response generated.")
    
    async def _run_standard_agent(self, user_input: str, file_context: str = "") -> str:
        agent = create_simple_agent(model=self.model, max_steps=st.session_state.get("agent_max_steps", 15))
        
        task = user_input
        if file_context:
            task += f"\n\nFile context:\n{file_context}"
        
        result = await agent.run(task, user_id=st.session_state.get("current_user", {}).get("username"))
        return result
    
    async def _run_hermes_agent(self, user_input: str, file_context: str = "") -> str:
        agent = create_hermes_agent(model=self.model, max_steps=st.session_state.get("agent_max_steps", 15))
        
        task = user_input
        if file_context:
            task += f"\n\nFile context:\n{file_context}"
        
        result = await agent.run(task, user_id=st.session_state.get("current_user", {}).get("username"))
        return result
    
    async def _run_kimi_swarm(self, user_input: str, file_context: str = "") -> str:
        swarm = create_kimi_swarm(
            model=self.model,
            max_agents=st.session_state.get("swarm_max_parallel", 4)
        )
        
        task = user_input
        if file_context:
            task += f"\n\nFile context:\n{file_context}"
        
        result = await swarm.run_swarm(task, user_id=st.session_state.get("current_user", {}).get("username"))
        return result