import streamlit as st
from backend import chat_api, generate_image, analyze_file, MODELS, SYSTEM_PROMPT
import uuid
import base64
from pathlib import Path

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="DenLab", page_icon="🧪", layout="wide")

# ---------- LIGHT THEME CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    * { font-family: 'Inter', sans-serif; }
    
    .stApp { background-color: #ffffff; }
    
    .main > div {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px 20px 120px 20px;
    }
    
    .stChatMessage { background: transparent !important; padding: 20px 0 !important; }
    
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: #f0f2f6 !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin: 16px 0 !important;
        color: #000000 !important;
    }
    
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: transparent !important;
        padding: 16px 0 !important;
        color: #000000 !important;
    }
    
    .stChatInput {
        position: fixed !important;
        bottom: 20px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 40px) !important;
        max-width: 860px !important;
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 30px !important;
        padding: 8px 16px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important;
        z-index: 100 !important;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        border: none !important;
        color: #000000 !important;
        font-size: 16px !important;
        padding: 12px 50px 12px 16px !important;
    }
    
    .stChatInput textarea::placeholder { color: #888888 !important; }
    
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #e0e0e0;
    }
    
    [data-testid="stSidebar"] * { color: #000000 !important; }
    
    .stButton button {
        background: #ffffff;
        color: #000000;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 500;
    }
    
    .stButton button:hover {
        background: #f0f2f6;
        border-color: #667eea;
        color: #667eea;
    }
    
    h1, h2, h3, h4, p, span, div { color: #000000 !important; }
    
    .welcome-container { text-align: center; padding: 60px 20px; }
    .welcome-title { font-size: 32px; font-weight: 600; color: #000000; margin-bottom: 16px; }
    .welcome-subtitle { font-size: 18px; color: #666666; margin-bottom: 40px; }
    
    .image-container {
        background: #f8f9fa;
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "🧪 Hello! I'm DenLab. I can chat, analyze files, and generate images.\n\n**Try:**\n- `/imagine sunset over mountains` to create images\n- Upload files for analysis\n- Ask me anything!"}
    ]

if "model" not in st.session_state:
    st.session_state.model = "openai"

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())

if "pending_upload" not in st.session_state:
    st.session_state.pending_upload = None

if "processing_upload" not in st.session_state:
    st.session_state.processing_upload = False

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🧪 DenLab")
    
    st.subheader("Model")
    model_names = list(MODELS.keys())
    current_idx = list(MODELS.values()).index(st.session_state.model) if st.session_state.model in MODELS.values() else 0
    model_choice = st.selectbox("Select model", model_names, index=current_idx)
    st.session_state.model = MODELS[model_choice]
    
    st.divider()
    
    if st.button("🔄 New Chat", use_container_width=True):
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "🧪 Hello! I'm DenLab. How can I help you today?"}
        ]
        st.rerun()
    
    st.divider()
    st.subheader("📎 File Upload")
    
    uploaded_file = st.file_uploader(
        "Upload file for analysis",
        type=["txt", "py", "js", "html", "css", "json", "md", "csv", "php", "java", "c", "cpp"],
        key=f"uploader_{st.session_state.uploader_key}"
    )
    
    st.caption("v2.0 · Light Theme")

# ---------- HANDLE FILE UPLOAD ----------
if uploaded_file and not st.session_state.processing_upload:
    st.session_state.pending_upload = uploaded_file
    st.session_state.processing_upload = True
    st.session_state.uploader_key = str(uuid.uuid4())
    st.rerun()

if st.session_state.pending_upload and st.session_state.processing_upload:
    file_obj = st.session_state.pending_upload
    filename = file_obj.name
    
    try:
        content = file_obj.read().decode('utf-8', errors='ignore')
    except:
        content = "[Could not read file]"
    
    st.session_state.messages.append({"role": "user", "content": f"📎 Uploaded: {filename}"})
    
    with st.chat_message("user"):
        st.markdown(f"📎 **Uploaded**: `{filename}`")
        if content != "[Could not read file]":
            with st.expander("Preview"):
                ext = Path(filename).suffix[1:] if Path(filename).suffix else "text"
                st.code(content[:2000], language=ext)
    
    with st.chat_message("assistant"):
        with st.spinner(f"Analyzing {filename}..."):
            analysis = analyze_file(content, filename, st.session_state.model)
        st.markdown(analysis)
    
    st.session_state.messages.append({"role": "assistant", "content": analysis})
    st.session_state.pending_upload = None
    st.session_state.processing_upload = False
    st.rerun()

# ---------- MAIN CHAT ----------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        if msg["content"].startswith("![Generated]"):
            img_url = msg["content"].split("](")[1].rstrip(")")
            st.markdown('<div class="image-container">', unsafe_allow_html=True)
            st.image(img_url, use_container_width=True)
            st.caption("🎨 Generated image")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

st.markdown('</div>', unsafe_allow_html=True)

# ---------- CHAT INPUT ----------
if prompt := st.chat_input("Message DenLab... (/imagine for images)"):
    
    if prompt.lower().startswith("/imagine"):
        image_desc = prompt[8:].strip()
        if image_desc:
            st.session_state.messages.append({"role": "user", "content": f"🎨 {prompt}"})
            
            with st.chat_message("user"):
                st.markdown(f"🎨 {prompt}")
            
            with st.chat_message("assistant"):
                with st.spinner("🎨 Creating image..."):
                    img_url = generate_image(image_desc)
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    st.image(img_url, caption=image_desc, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    response = f"![Generated]({img_url})"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                api_messages = [m for m in st.session_state.messages if m["role"] != "system"]
                api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                response = chat_api(api_messages, st.session_state.model)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()
