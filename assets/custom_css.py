"""Custom CSS themes."""

DARK_THEME = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #0f172a 100%);
        color: #e2e8f0 !important;
    }
    
    /* Force ALL text to be light */
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label, 
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp li, .stApp td, .stApp th, .stApp strong, .stApp em {
        color: #e2e8f0 !important;
    }
    
    /* Chat messages */
    .stChatMessage {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        padding: 16px !important;
        margin: 8px 0 !important;
    }
    
    /* User message specific */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: rgba(99, 102, 241, 0.15) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
    }
    
    /* Assistant message */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: rgba(255,255,255,0.03) !important;
    }
    
    /* Chat input */
    .stChatInput {
        position: fixed !important;
        bottom: 20px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 90% !important;
        max-width: 800px !important;
        background: rgba(18, 18, 26, 0.95) !important;
        backdrop-filter: blur(20px);
        border-radius: 24px !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
        z-index: 9999 !important;
    }
    
    .stChatInput textarea {
        color: #e2e8f0 !important;
        font-size: 15px !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.08) !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    
    /* Buttons */
    .stButton button {
        background: rgba(99, 102, 241, 0.2) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-radius: 10px !important;
        transition: all 0.2s !important;
    }
    
    .stButton button:hover {
        background: rgba(99, 102, 241, 0.4) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Input fields */
    .stTextInput input, .stSelectbox, .stSlider {
        background: rgba(255,255,255,0.05) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
    }
    
    /* Code blocks */
    pre {
        background: #1e1e2e !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        padding: 16px !important;
    }
    
    code {
        background: rgba(99, 102, 241, 0.1) !important;
        color: #a5b4fc !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.03) !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
    }
    
    /* Status/Spinner */
    .stStatus {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 12px !important;
    }
    
    /* File uploader */
    .stFileUploader {
        background: rgba(255,255,255,0.03) !important;
        border: 2px dashed rgba(99, 102, 241, 0.3) !important;
        border-radius: 12px !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { 
        background: rgba(99, 102, 241, 0.5); 
        border-radius: 4px; 
    }
    ::-webkit-scrollbar-thumb:hover { 
        background: rgba(99, 102, 241, 0.8); 
    }
    
    /* Images */
    .stImage {
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    
    /* Toast notifications */
    .stToast {
        background: rgba(30, 30, 46, 0.95) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        color: #e2e8f0 !important;
    }
    
    /* Metric */
    [data-testid="stMetricValue"] {
        color: #e2e8f0 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }
</style>
"""
