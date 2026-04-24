"""
Chat Interface Component for DenLab Chat.
Handles message display, input handling, command parsing, and agent integration.
"""

import streamlit as st
import re
import json
import time
import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

# Import from completed files
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AppConfig, Constants, AspectRatios
from backend import web_search, deep_research, execute_code
from client import get_client
from features.tool_router import get_router, route_query
from agents.orchestrator import run_swarm_simple_sync
from agents.base_agent import create_simple_agent
from ui_components import render_message_actions, render_welcome
from components.agent_interface import (
    render_trace, render_swarm_status, render_step_progress,
    render_status_message, should_show_traces
)


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

class CommandHandler:
    """Handle slash commands like /imagine, /research, /code, etc."""
    
    def __init__(self, db, conv_id: str, model: str, user_id: str):
        self.db = db
        self.conv_id = conv_id
        self.model = model
        self.user_id = user_id
        self.client = get_client()
    
    def handle(self, prompt: str) -> Optional[str]:
        """
        Handle a command and return response.
        Returns None if not a command or if handled elsewhere.
        """
        prompt_lower = prompt.lower()
        
        # /imagine - Image generation
        if prompt_lower.startswith("/imagine"):
            return self._handle_imagine(prompt)
        
        # /research - Web research
        elif prompt_lower.startswith("/research"):
            return self._handle_research(prompt)
        
        # /code - Code execution
        elif prompt_lower.startswith("/code"):
            return self._handle_code(prompt)
        
        # /analyze - File analysis
        elif prompt_lower.startswith("/analyze"):
            return self._handle_analyze(prompt)
        
        # /audio - Text to speech
        elif prompt_lower.startswith("/audio"):
            return self._handle_audio(prompt)
        
        # /agent - Agent mode (handled separately, but we return a flag)
        elif prompt_lower.startswith("/agent"):
            return "AGENT_MODE"
        
        return None
    
    def _handle_imagine(self, prompt: str) -> str:
        """
        Handle /imagine command.
        Generates image, stores in database, returns special marker.
        NO direct rendering - let _render_messages handle display.
        """
        desc = prompt[8:].strip()
        if not desc:
            return "Please provide an image description.\n\nExample: `/imagine a cat sitting on a mat`"
        
        # Parse aspect ratio
        width, height = 1024, 1024
        ar_match = re.search(r'--ar\s+(\d+:\d+)', desc)
        if ar_match:
            ratio = ar_match.group(1)
            if ratio in AspectRatios.RATIOS:
                width, height = AspectRatios.RATIOS[ratio]
            desc = re.sub(r'--ar\s+\d+:\d+', '', desc).strip()
        
        # Generate image URL
        url = self.client.generate_image(desc, width, height)
        
        # Store in database - will be rendered on next rerun
        self.db.add_message(self.conv_id, "assistant", url, {"type": "image"})
        
        # Return special marker - no direct display
        return "__IMAGE_STORED__"
    
    def _handle_research(self, prompt: str) -> str:
        """Handle /research command."""
        topic = prompt[9:].strip()
        if not topic:
            return "Please provide a research topic.\n\nExample: `/research artificial intelligence`"
        
        # Perform research using deep_research for better results
        result = deep_research(topic, depth=2)
        data = json.loads(result)
        
        if not data.get("success"):
            # Fallback to simple web search
            fallback = web_search(topic)
            fb_data = json.loads(fallback)
            if fb_data.get("success"):
                output = f"## Research: {topic}\n\n"
                output += f"**Results found:** {len(fb_data.get('results', []))}\n\n"
                for i, item in enumerate(fb_data.get('results', [])[:5], 1):
                    output += f"### {i}. {item.get('title', 'Untitled')}\n"
                    output += f"**Source:** {item.get('url', 'Unknown')}\n\n"
                    output += f"{item.get('snippet', 'No content')}\n\n"
                return output
            return f"Research failed: {data.get('error', 'Unknown error')}"
        
        # Format output
        output = f"## Research: {data['topic']}\n\n"
        output += f"**Sources found:** {data['total_sources']}\n"
        output += f"**Findings:** {data['total_findings']}\n\n"
        
        for i, finding in enumerate(data.get('findings', [])[:5], 1):
            output += f"### {i}. {finding.get('title', 'Untitled')}\n"
            output += f"**Source:** {finding.get('source', 'Unknown')}\n\n"
            output += f"{finding.get('content', 'No content')}\n\n"
        
        return output
    
    def _handle_code(self, prompt: str) -> str:
        """Handle /code command."""
        task = prompt[5:].strip()
        if not task:
            return "Please describe what code you want.\n\nExample: `/code calculate factorial of 10`"
        
        # Generate code using LLM
        code_prompt = f"""Write Python code to: {task}
Return ONLY the code inside a markdown code block with language specification.
Include comments to explain the code."""
        
        response = self.client.chat([
            {"role": "system", "content": "You are an expert Python programmer. Return only code in markdown blocks."},
            {"role": "user", "content": code_prompt}
        ], model=self.model, user_id=self.user_id)
        
        raw_content = response.get("content", "")
        
        # Extract code from markdown
        code_match = re.search(r'```python\n(.*?)```', raw_content, re.DOTALL)
        if not code_match:
            code_match = re.search(r'```\n(.*?)```', raw_content, re.DOTALL)
        
        code = code_match.group(1).strip() if code_match else raw_content.strip()
        
        # Execute code
        exec_result = execute_code(code)
        exec_data = json.loads(exec_result)
        
        # Format output
        output = f"```python\n{code}\n```\n\n"
        
        if exec_data.get("success"):
            output += "**Output:**\n```\n"
            output += exec_data.get("stdout", "(no output)")
            if exec_data.get("stderr"):
                output += f"\n\n**Stderr:**\n{exec_data['stderr']}"
            output += "\n```"
        else:
            output += f"**Error:**\n```\n{exec_data.get('error', 'Unknown error')}\n```"
        
        return output
    
    def _handle_analyze(self, prompt: str) -> str:
        """Handle /analyze command."""
        uploaded_files = st.session_state.get("uploaded_files", {})
        
        if not uploaded_files:
            return "No file uploaded. Please upload a file first using the 📎 button."
        
        # Get most recent file
        file_key = list(uploaded_files.keys())[-1]
        file_data = uploaded_files[file_key]
        
        if file_data.get("type") == "text":
            content = file_data.get("content", "")
            filename = file_data.get("name", "file")
            
            analysis_prompt = f"""Analyze this file: {filename}

Content:
`\`\`\
{content[:4000]}
`\`\`\

Provide a structured analysis covering:
1. **Purpose** - What this file does
2. **Key Components** - Main functions, classes, or sections
3. **Dependencies** - External libraries or modules
4. **Code Quality** - Structure, patterns, best practices
5. **Issues/Suggestions** - Potential bugs or improvements"""
            
            response = self.client.chat([
                {"role": "system", "content": "You are a senior code reviewer. Provide thorough analysis."},
                {"role": "user", "content": analysis_prompt}
            ], model=self.model, user_id=self.user_id)
            
            return response.get("content", "Analysis failed.")
        
        elif file_data.get("type") == "image":
            return "Image analysis: Please use the agent mode for image analysis, or describe what you want to know about the image."
        
        return "File analysis not available for this file type."
    
    def _handle_audio(self, prompt: str) -> str:
        """Handle /audio command."""
        text = prompt[6:].strip()
        if not text:
            return "Please provide text to convert to speech.\n\nExample: `/audio Hello, world!`"
        
        url = self.client.generate_audio(text)
        return url


# ============================================================================
# CHAT INTERFACE
# ============================================================================

class ChatInterface:
    """Main chat interface component."""
    
    def __init__(self):
        self.client = get_client()
        self.router = get_router()
        self.command_handler = None
    
    # ========================================================================
    # Main Render Methods
    # ========================================================================
    
    def render(self, db, conv_id: str, model: str, user_id: str, messages: List[Dict]):
        """Render the chat interface."""
        # Initialize command handler
        self.command_handler = CommandHandler(db, conv_id, model, user_id)
        
        # Display all messages
        self._render_messages(messages)
        
        # Show welcome screen if no messages
        if not self._has_visible_messages(messages):
            render_welcome()
        
        # Chat input
        placeholder = "Message DenLab..." if not st.session_state.get("agent_mode", False) else "Describe your task for the agent..."
        
        if prompt := st.chat_input(placeholder):
            self._handle_input(prompt, db, conv_id, model, user_id, messages)
    
    def _render_messages(self, messages: List[Dict]):
        """Render all messages in the conversation."""
        for idx, msg in enumerate(messages):
            if msg.get("role") == "system":
                continue
            
            meta = msg.get("metadata", {})
            msg_type = meta.get("type", "text")
            content = msg.get("content", "")
            
            with st.chat_message(msg["role"]):
                self._render_single_message(content, msg_type, meta, idx)
    
    def _render_single_message(self, content: str, msg_type: str, meta: Dict, idx: int):
        """Render a single message based on its type."""
        if msg_type == "image":
            st.image(content, use_container_width=True)
            # Add download button for image
            try:
                import requests
                img_data = requests.get(content, timeout=15).content
                st.download_button(
                    label="⬇️ Download",
                    data=img_data,
                    file_name=f"image_{idx}.png",
                    mime="image/png",
                    key=f"img_dl_{idx}"
                )
            except:
                pass
        
        elif msg_type == "image_upload":
            file_key = meta.get("file_key")
            uploaded_files = st.session_state.get("uploaded_files", {})
            if file_key and file_key in uploaded_files:
                st.image(uploaded_files[file_key]["bytes"], use_container_width=True)
        
        elif msg_type == "file":
            st.markdown(content)
            file_key = meta.get("file_key")
            uploaded_files = st.session_state.get("uploaded_files", {})
            if file_key and file_key in uploaded_files:
                with st.expander("Preview"):
                    st.code(uploaded_files[file_key].get("content", "")[:3000])
        
        elif msg_type == "agent_trace":
            st.markdown(content)
            traces = meta.get("traces", [])
            if traces and should_show_traces():
                with st.expander("📋 Execution Details", expanded=False):
                    for t in traces:
                        st.markdown(f"**Step {t.get('step', '?')}**")
                        for tc in t.get("tool_calls", []):
                            icon = "✅" if tc.get("status") == "success" else "❌" if tc.get("status") == "error" else "🔄"
                            st.markdown(f"&nbsp;&nbsp;{icon} `{tc.get('name')}` ({tc.get('duration_ms', 0):.0f}ms)")
        
        elif msg_type == "swarm":
            st.markdown(content)
            swarm_results = meta.get("swarm_results", {})
            if swarm_results:
                with st.expander("🐝 Swarm Details", expanded=False):
                    for agent, result in swarm_results.items():
                        st.markdown(f"**{agent.upper()} Agent**")
                        st.markdown(f"{result[:300]}...")
        
        elif msg_type == "audio":
            st.audio(content, format='audio/mp3')
        
        else:
            st.markdown(content)
        
        # Add action buttons for assistant messages (not for images/audio)
        if idx > 0 and msg_type not in ["image", "audio"]:
            render_message_actions(idx, content, msg_type)
    
    def _has_visible_messages(self, messages: List[Dict]) -> bool:
        """Check if there are any non-system messages."""
        return any(m.get("role") != "system" for m in messages)
    
    # ========================================================================
    # Input Handling
    # ========================================================================
    
    def _handle_input(self, prompt: str, db, conv_id: str, model: str, user_id: str, messages: List[Dict]):
        """Process user input and generate response."""
        # Save user message
        db.add_message(conv_id, "user", prompt)
        
        # Check for commands
        cmd_result = self.command_handler.handle(prompt)
        
        # Handle IMAGE_STORED marker (no direct display, just rerun)
        if cmd_result == "__IMAGE_STORED__":
            st.rerun()
        
        # Handle AGENT_MODE flag
        elif cmd_result == "AGENT_MODE":
            st.session_state.agent_mode = True
            st.rerun()
        
        # Handle image/audio URLs (store and rerun, don't display directly)
        elif cmd_result and isinstance(cmd_result, str) and cmd_result.startswith("http"):
            if "image.pollinations" in cmd_result:
                db.add_message(conv_id, "assistant", cmd_result, {"type": "image"})
            elif "gen.pollinations" in cmd_result:
                db.add_message(conv_id, "assistant", cmd_result, {"type": "audio"})
            else:
                db.add_message(conv_id, "assistant", cmd_result)
            st.rerun()
        
        # Handle text response from commands
        elif cmd_result is not None:
            with st.chat_message("assistant"):
                st.markdown(cmd_result)
            db.add_message(conv_id, "assistant", cmd_result)
            st.rerun()
        
        # Agent Mode (Standard or Swarm)
        elif st.session_state.get("agent_mode", False):
            self._handle_agent_mode(prompt, db, conv_id, model, user_id)
        
        # Normal Chat with Auto-Routing
        else:
            self._handle_normal_chat(prompt, db, conv_id, model, user_id, messages)
    
    def _handle_agent_mode(self, prompt: str, db, conv_id: str, model: str, user_id: str):
        """Handle agent mode execution (Standard or Swarm)."""
        with st.chat_message("assistant"):
            progress_placeholder = st.empty()
            
            try:
                if st.session_state.get("swarm_mode", False):
                    # Swarm mode
                    render_status_message("🐝 Swarm mode activated. Decomposing task...", "info")
                    progress_placeholder.markdown("🔄 **Master Agent** is planning the task...")
                    
                    # Execute swarm (sync wrapper)
                    result = run_swarm_simple_sync(prompt, user_id=user_id, model=model)
                    
                    progress_placeholder.empty()
                    st.markdown(result)
                    db.add_message(conv_id, "assistant", result, {"type": "swarm"})
                
                else:
                    # Standard agent mode
                    render_status_message("🤖 Agent mode activated. Processing your task...", "info")
                    
                    # Create and run agent
                    agent = create_simple_agent(model=model)
                    
                    # Add progress callback
                    def on_step(trace):
                        if should_show_traces():
                            progress_placeholder.markdown(f"**Step {trace.step}**: {trace.thought[:150]}...")
                    
                    agent.on_step = on_step
                    
                    # Run agent (async)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(agent.run(prompt, user_id=user_id))
                    finally:
                        loop.close()
                    
                    progress_placeholder.empty()
                    st.markdown(result)
                    
                    # Store traces if any
                    traces = [t.to_dict() for t in agent.traces] if agent.traces else []
                    db.add_message(conv_id, "assistant", result, {
                        "type": "agent_trace",
                        "traces": traces
                    })
                
                st.rerun()
                
            except Exception as e:
                progress_placeholder.empty()
                st.error(f"Agent error: {str(e)}")
                db.add_message(conv_id, "assistant", f"Agent error: {str(e)}")
                st.rerun()
    
    def _handle_normal_chat(self, prompt: str, db, conv_id: str, model: str, user_id: str, messages: List[Dict]):
        """Handle normal chat with auto-routing."""
        with st.chat_message("assistant"):
            ph = st.empty()
            
            # Auto-route complex queries
            if st.session_state.get("auto_route", True):
                route_result = self.router.route(prompt, [
                    "web_search", "github_get_files", "execute_code",
                    "read_file", "fetch_url", "analyze_image"
                ])
                
                if route_result.get("needs_agent", False) and route_result.get("confidence", 0) > 0.7:
                    st.info(f"🔄 {route_result.get('explanation', 'Complex query detected')}")
                    st.session_state.agent_mode = True
                    time.sleep(1)
                    st.rerun()
            
            # Build messages for API
            api_messages = [{"role": "system", "content": "You are DenLab, a helpful AI assistant."}]
            for m in messages:
                if m.get("role") in ("user", "assistant"):
                    api_messages.append({"role": m["role"], "content": m.get("content", "")})
            api_messages.append({"role": "user", "content": prompt})
            
            # Stream response
            full_response = []
            def on_chunk(chunk):
                full_response.append(chunk)
                ph.markdown(''.join(full_response) + "▌")
            
            try:
                result = self.client.chat(
                    api_messages,
                    model=model,
                    stream=True,
                    on_chunk=on_chunk,
                    user_id=user_id
                )
                response = result.get("content", "")
                
                # If streaming returned empty, try non-streaming
                if not response or not response.strip():
                    result2 = self.client.chat(api_messages, model=model, stream=False, user_id=user_id)
                    response = result2.get("content", "")
                
                # Display and store response
                if response and response.strip():
                    ph.markdown(response)
                else:
                    ph.markdown("I received an empty response. Please try again.")
                    response = "Empty response from API."
                
                db.add_message(conv_id, "assistant", response)
                st.rerun()
                
            except Exception as e:
                ph.markdown(f"Error: {str(e)}")
                db.add_message(conv_id, "assistant", f"Error: {str(e)}")
                st.rerun()


# ============================================================================
# FILE UPLOAD HANDLER
# ============================================================================

class FileUploadHandler:
    """Handle file uploads and processing."""
    
    def __init__(self, db, conv_id: str):
        self.db = db
        self.conv_id = conv_id
    
    def process_uploaded_file(self, uploaded_file):
        """Process an uploaded file and add to session state."""
        if not uploaded_file:
            return None
        
        fname = uploaded_file.name
        fkey = f"{datetime.now().strftime('%H%M%S')}_{fname}"
        
        try:
            fb = uploaded_file.read()
            
            if uploaded_file.type and uploaded_file.type.startswith("image/"):
                # Handle image
                st.session_state.uploaded_files[fkey] = {
                    "type": "image",
                    "name": fname,
                    "bytes": fb,
                    "mime": uploaded_file.type
                }
                self.db.add_message(self.conv_id, "user", f"📎 {fname}", {
                    "type": "image_upload",
                    "file_key": fkey
                })
                
                # Auto-analyze image
                try:
                    from features.vision import VisionAnalyzer
                    analyzer = VisionAnalyzer()
                    analysis = analyzer.analyze(fb, model="gemini")
                    self.db.add_message(self.conv_id, "assistant", f"**📎 {fname}**\n\n{analysis}")
                except:
                    self.db.add_message(self.conv_id, "assistant", f"**📎 {fname}** received.")
            
            else:
                # Handle text file
                txt = fb.decode('utf-8', errors='ignore')
                st.session_state.uploaded_files[fkey] = {
                    "type": "text",
                    "name": fname,
                    "content": txt,
                    "size": len(txt)
                }
                self.db.add_message(self.conv_id, "user", f"📎 {fname}", {
                    "type": "file",
                    "file_key": fkey
                })
                self.db.add_message(self.conv_id, "assistant", f"**📎 {fname}** loaded ({len(txt)} chars).")
            
            return fkey
            
        except Exception as e:
            st.error(f"Upload error: {e}")
            return None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def render_chat_interface(db, conv_id: str, model: str, user_id: str, messages: List[Dict]):
    """Convenience function to render the chat interface."""
    interface = ChatInterface()
    interface.render(db, conv_id, model, user_id, messages)


def process_file_upload(db, conv_id: str, uploaded_file):
    """Convenience function to process file upload."""
    handler = FileUploadHandler(db, conv_id)
    return handler.process_uploaded_file(uploaded_file)