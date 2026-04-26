"""
Chat Interface with Upload Integration.
Fixed input area at viewport bottom, developer-aware, image generation support.
"""

import streamlit as st
from typing import List, Dict, Optional, Any
import os
import asyncio
import json
import requests

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
    from features.memory import get_memory
    MEMORY_AVAILABLE = True
except:
    MEMORY_AVAILABLE = False


class ChatInterface:
    """Main chat interface with fixed input and all features."""
    
    def __init__(self, db: ConversationDB, conversation_id: str,
                 model: str = "openai", agent_mode: bool = False,
                 swarm_mode: bool = False):
        self.db = db
        self.conversation_id = conversation_id
        self.model = model
        self.agent_mode = agent_mode
        self.swarm_mode = swarm_mode
        self.client = get_client()
        self._init_session()
    
    def _init_session(self):
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
        
        # Status bar
        self._render_status_bar()
        
        st.divider()
        
        # Chat history in scrollable area
        self._render_chat_history()
        
        # Fixed input at bottom of viewport
        self._render_fixed_input()
    
    def _render_status_bar(self):
        """Render model/agent status indicators."""
        cols = st.columns([0.35, 0.25, 0.25, 0.15])
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
        
        if not messages:
            st.info("Start a conversation! Try `/imagine a sunset over mountains` or just say hello.")
        
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            
            if role == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(content)
            elif role == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content, unsafe_allow_html=True)
    
    def _render_fixed_input(self):
        """Render input area fixed at the bottom of the viewport."""
        
        # Inject CSS to fix input at bottom and give chat area breathing room
        st.markdown("""
        <style>
        /* Create space at the bottom of the main container so chat doesn't hide behind input */
        .main .block-container {
            padding-bottom: 200px !important;
        }
        
        /* Style for the fixed input container */
        .fixed-input-container {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            background: #0d0d0d !important;
            z-index: 9999 !important;
            padding: 12px 24px 24px 24px !important;
            border-top: 1px solid #1a1a1a !important;
        }
        
        /* Make text area visible */
        div[data-testid="stTextArea"] textarea {
            background: #1a1a1a !important;
            color: #e0e0e0 !important;
            border: 1px solid #333 !important;
            border-radius: 8px !important;
            min-height: 55px !important;
            max-height: 120px !important;
            font-size: 14px !important;
        }
        
        /* Make file uploader less obtrusive */
        div[data-testid="stFileUploader"] {
            max-width: 50px !important;
        }
        div[data-testid="stFileUploader"] section {
            padding: 4px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Fixed input container
        st.markdown('<div class="fixed-input-container">', unsafe_allow_html=True)
        
        msg_count = st.session_state.get("message_counter", 0)
        
        user_input = st.text_area(
            "Message",
            key=f"chat_input_{self.conversation_id}_{msg_count}",
            height=55,
            placeholder="Type a message... (Use /imagine for images, /agent for agent mode)",
            label_visibility="collapsed"
        )
        
        col_upload, col_spacer, col_send = st.columns([0.08, 0.72, 0.20])
        
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
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if send_clicked and user_input.strip():
            st.session_state.message_counter += 1
            asyncio.run(self._handle_send(user_input.strip()))
            st.rerun()
    
    # ========================================================================
    # SEND HANDLER
    # ========================================================================
    
    async def _handle_send(self, user_input: str):
        """Process user message and generate response."""
        
        # ---- IMAGE GENERATION ----
        if user_input.lower().startswith("/imagine") or user_input.lower().startswith("/image"):
            prompt = user_input.replace("/imagine", "").replace("/image", "").strip()
            if prompt:
                self.db.add_message(self.conversation_id, "user", user_input)
                encoded = requests.utils.quote(prompt)
                img_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
                response = f"🖼️ **Generated image for:** *{prompt}*\n\n![Image]({img_url})\n\n[🔗 Open full size]({img_url})"
                self.db.add_message(self.conversation_id, "assistant", response)
                return
        
        # ---- FILE UPLOADS ----
        file_attachments = list(st.session_state.get("uploaded_files", []))
        file_context = ""
        for fname in file_attachments:
            fdata = st.session_state.uploaded_file_data.get(fname)
            if fdata:
                ext = os.path.splitext(fname)[1].lower()
                if ext in ['.txt', '.md', '.py', '.json', '.csv', '.html', '.css', '.js']:
                    try:
                        text = fdata.decode('utf-8')[:3000]
                        file_context += f"\n\n[File: {fname}]\n```\n{text}\n```\n"
                    except:
                        file_context += f"\n\n[Binary file attached: {fname}]\n"
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                    file_context += f"\n\n[Image attached: {fname}] - User may want you to describe or analyze this.\n"
                else:
                    file_context += f"\n\n[File attached: {fname}]\n"
        
        # Add user message
        metadata = {"file_uploads": file_attachments} if file_attachments else None
        self.db.add_message(self.conversation_id, "user", user_input, metadata=metadata)
        
        # Clear uploads
        st.session_state.uploaded_files = []
        st.session_state.uploaded_file_data = {}
        
        # ---- BUILD MESSAGES ----
        messages = self._build_messages(user_input, file_context)
        
        # ---- GENERATE RESPONSE ----
        with st.spinner("Thinking..." if not self.agent_mode else "Agent working..."):
            try:
                if self.swarm_mode and KIMI_SWARM_AVAILABLE:
                    response = await self._run_kimi_swarm(user_input, file_context)
                elif self.agent_mode and HERMES_AVAILABLE and st.session_state.get("hermes_mode"):
                    response = await self._run_hermes_agent(user_input, file_context)
                elif self.agent_mode:
                    response = await self._run_standard_agent(user_input, file_context)
                else:
                    response = await self._run_chat(messages)
            except Exception as e:
                response = f"❌ Error: {str(e)}\n\nTry again or use a different mode."
        
        self.db.add_message(self.conversation_id, "assistant", response)
    
    def _build_messages(self, user_input: str, file_context: str = "") -> List[Dict]:
        """Build message list with proper developer/system prompt."""
        
        # Use developer prompt if user is developer
        if st.session_state.get("is_developer"):
            system_content = SystemPrompts.DEVELOPER
        else:
            system_content = SystemPrompts.DEFAULT
        
        messages = [{"role": "system", "content": system_content}]
        
        # Add memory context if enabled
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
        
        # Add recent history
        history = self.db.get_messages(self.conversation_id)
        for msg in history[-6:]:
            if msg.get("content"):
                messages.append({"role": msg["role"], "content": msg.get("content", "")})
        
        # Current input with file context
        full_input = user_input
        if file_context:
            full_input += file_context
        
        messages.append({"role": "user", "content": full_input})
        return messages
    
    async def _run_chat(self, messages: List[Dict]) -> str:
        """Standard chat completion."""
        response = self.client.generate(
            messages=messages,
            model=self.model,
            temperature=0.7,
            user_id=st.session_state.get("current_user", {}).get("username"),
            conversation_id=self.conversation_id
        )
        content = response.get("content", "")
        if not content:
            content = "I received your message but couldn't generate a response. Please try again."
        return content
    
    async def _run_standard_agent(self, user_input: str, file_context: str = "") -> str:
        """Standard agent execution."""
        try:
            agent = create_simple_agent(model=self.model, max_steps=st.session_state.get("agent_max_steps", 10))
            task = user_input
            if file_context:
                task += f"\n\nFile context:\n{file_context}"
            result = await agent.run(task, user_id=st.session_state.get("current_user", {}).get("username"))
            return result if result else "Agent completed but produced no output. Try a more specific request."
        except Exception as e:
            # Fall back to chat if agent fails
            messages = self._build_messages(user_input, file_context)
            return await self._run_chat(messages)
    
    async def _run_hermes_agent(self, user_input: str, file_context: str = "") -> str:
        """Hermes agent with self-reflection."""
        try:
            agent = create_hermes_agent(model=self.model, max_steps=st.session_state.get("agent_max_steps", 10))
            task = user_input
            if file_context:
                task += f"\n\nFile context:\n{file_context}"
            result = await agent.run(task, user_id=st.session_state.get("current_user", {}).get("username"))
            return result if result else "Hermes agent completed. Try a more specific request."
        except Exception as e:
            messages = self._build_messages(user_input, file_context)
            return await self._run_chat(messages)
    
    async def _run_kimi_swarm(self, user_input: str, file_context: str = "") -> str:
        """Kimi swarm with hierarchical planning."""
        try:
            swarm = create_kimi_swarm(model=self.model, max_agents=st.session_state.get("swarm_max_parallel", 4))
            task = user_input
            if file_context:
                task += f"\n\nFile context:\n{file_context}"
            result = await swarm.run_swarm(task, user_id=st.session_state.get("current_user", {}).get("username"))
            return result if result else "Swarm completed. Try a more specific request."
        except Exception as e:
            messages = self._build_messages(user_input, file_context)
            return await self._run_chat(messages)