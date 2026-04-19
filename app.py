import streamlit as st
from backend import chat_api, generate_image, analyze_file, MODELS, SYSTEM_PROMPT
from ui_components import apply_custom_css, render_sidebar, render_chat_message, render_welcome
import uuid
import base64
import mimetypes
from pathlib import Path

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="DenLab", page_icon="🧪", layout="wide")
apply_custom_css()

# ---------- SESSION STATE INIT ----------
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

if "model" not in st.session_state:
    st.session_state.model = "openai"

if "sessions" not in st.session_state:
    st.session_state.sessions = {}

if "current_session" not in st.session_state:
    st.session_state.current_session = "Main"

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())

if "pending_upload" not in st.session_state:
    st.session_state.pending_upload = None

if "processing_upload" not in st.session_state:
    st.session_state.processing_upload = False

# ---------- SIDEBAR ----------
model_choice, new_session_clicked, uploaded_file = render_sidebar(
    st.session_state.model, 
    st.session_state.sessions,
    st.session_state.uploader_key
)

if model_choice:
    st.session_state.model = model_choice

if new_session_clicked:
    new_name = f"Session {len(st.session_state.sessions) + 1}"
    st.session_state.sessions[new_name] = []
    st.session_state.current_session = new_name
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.rerun()

# Handle session switching from sidebar
for sess in list(st.session_state.sessions.keys()):
    if st.session_state.get(f"switch_to_{sess}"):
        st.session_state.current_session = sess
        loaded = st.session_state.sessions.get(sess, [])
        st.session_state.messages = loaded if loaded else [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state[f"switch_to_{sess}"] = False
        st.rerun()
    if st.session_state.get(f"delete_{sess}"):
        del st.session_state.sessions[sess]
        if st.session_state.current_session == sess:
            st.session_state.current_session = "Main"
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state[f"delete_{sess}"] = False
        st.rerun()

# ---------- HANDLE FILE UPLOAD ----------
if uploaded_file is not None and not st.session_state.processing_upload:
    st.session_state.pending_upload = {
        "file": uploaded_file,
        "name": uploaded_file.name,
        "type": uploaded_file.type
    }
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(uuid.uuid4())
    st.rerun()

if st.session_state.pending_upload is not None and st.session_state.processing_upload:
    pending = st.session_state.pending_upload
    file_obj = pending["file"]
    filename = pending["name"]
    mime_type = pending["type"]
    
    file_bytes = file_obj.getvalue()
    
    if mime_type and mime_type.startswith("image/"):
        st.session_state.messages.append({
            "role": "user",
            "content": f"[IMAGE_UPLOAD]|{filename}|{base64.b64encode(file_bytes).decode()}"
        })
        with st.chat_message("user"):
            st.image(file_bytes, caption=filename, use_container_width=True)
        
        with st.chat_message("assistant"):
            with st.spinner("📸 Processing image..."):
                size_mb = len(file_bytes) / (1024 * 1024)
                analysis = f"📸 Image received: **{filename}** ({size_mb:.2f} MB)\n\nI cannot directly see images, but you can describe it and I'll help. Or use `/imagine` to generate similar images."
            st.markdown(analysis)
        st.session_state.messages.append({"role": "assistant", "content": analysis})
    else:
        try:
            content = file_bytes.decode('utf-8', errors='ignore')
        except:
            content = "[Binary file - cannot display]"
        
        st.session_state.messages.append({
            "role": "user",
            "content": f"[FILE_UPLOAD]|{filename}"
        })
        with st.chat_message("user"):
            st.markdown(f"📎 **Uploaded**: `{filename}`")
            if content != "[Binary file - cannot display]":
                with st.expander("View file content"):
                    ext = Path(filename).suffix[1:] if Path(filename).suffix else "text"
                    st.code(content[:2000], language=ext)
        
        with st.chat_message("assistant"):
            with st.spinner(f"📄 Analyzing {filename}..."):
                analysis = analyze_file(content, filename, st.session_state.model)
            st.markdown(analysis)
        st.session_state.messages.append({"role": "assistant", "content": analysis})
    
    st.session_state.sessions[st.session_state.current_session] = st.session_state.messages.copy()
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# ---------- MAIN CHAT AREA ----------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

if len(st.session_state.messages) <= 1:
    render_welcome()

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    render_chat_message(msg)

st.markdown('</div>', unsafe_allow_html=True)

# ---------- CHAT INPUT ----------
col1, col2 = st.columns([10, 1])
with col1:
    prompt = st.chat_input("Message DenLab... (Use /imagine for images)")

# ---------- HANDLE CHAT INPUT ----------
if prompt:
    if prompt.lower().startswith("/imagine"):
        image_desc = prompt[8:].strip()
        if image_desc:
            st.session_state.messages.append({"role": "user", "content": f"🎨 /imagine {image_desc}"})
            with st.chat_message("user"):
                st.markdown(f"🎨 /imagine {image_desc}")
            
            with st.chat_message("assistant"):
                with st.spinner("🎨 Creating image..."):
                    img_url = generate_image(image_desc)
                    st.image(img_url, caption=image_desc, use_container_width=True)
                    response = f"![Generated]({img_url})"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("💭 Thinking..."):
                api_messages = [m for m in st.session_state.messages if m["role"] != "system"]
                api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                response = chat_api(api_messages, st.session_state.model)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.session_state.sessions[st.session_state.current_session] = st.session_state.messages.copy()
    st.rerun()
