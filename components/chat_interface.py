"""Main chat UI."""
import streamlit as st
from core.session_manager import SessionManager
from core.api_client import PollinationsClient
from features.image_gen import ImageGenerator
from config.models import MessageRole

class ChatInterface:
    def __init__(self):
        self.sessions = SessionManager()
        self.client = PollinationsClient()
        self.image_gen = ImageGenerator()
    
    def render_messages(self):
        session = self.sessions.get_current()
        for msg in session.messages:
            if msg.role == MessageRole.SYSTEM:
                continue
            with st.chat_message(msg.role.value):
                if msg.metadata.get("type") == "image":
                    st.image(msg.content, use_container_width=True)
                else:
                    st.markdown(msg.content)
    
    def handle_input(self, prompt: str):
        session = self.sessions.get_current()
        
        # Check for /imagine
        img_params = self.image_gen.parse_command(prompt)
        if img_params:
            session.messages.append({
                "role": MessageRole.USER,
                "content": f"🎨 {img_params['prompt']}"
            })
            img_url = self.image_gen.generate(**img_params)
            session.messages.append({
                "role": MessageRole.ASSISTANT,
                "content": img_url,
                "metadata": {"type": "image"}
            })
        else:
            # Normal chat
            session.messages.append({
                "role": MessageRole.USER,
                "content": prompt
            })
            
            # Build messages for API
            api_msgs = [{"role": m.role.value, "content": m.content} 
                       for m in session.messages]
            
            # Stream response
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full = []
                
                def on_chunk(chunk):
                    full.append(chunk)
                    placeholder.markdown(''.join(full) + "▌")
                
                response = self.client.chat(api_msgs, model=session.model, 
                                          temperature=session.temperature,
                                          stream=True, on_chunk=on_chunk)
                response_text = response.get("content", "") if isinstance(response, dict) else str(response)
                placeholder.markdown(response_text)
            
            session.messages.append({
                "role": MessageRole.ASSISTANT,
                "content": response_text
            })
        
        self.sessions.update(session)
        st.rerun()
