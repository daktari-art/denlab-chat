"""Custom CSS - Kimi-inspired clean dark interface."""

DARK_THEME = """
<style>
    /* ============================================
       GLOBAL RESET - Force dark mode everywhere
       ============================================ */
    
    /* Override Streamlit's default light theme */
    .stApp, [data-testid="stAppViewContainer"], .main {
        background-color: #0d0d0d !important;
        color: #e0e0e0 !important;
    }
    
    /* All text elements */
    p, span, div, label, h1, h2, h3, h4, h5, h6, li, td, th, 
    strong, em, b, i, a, pre, code, button, input, textarea {
        color: #e0e0e0 !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    /* ============================================
       CHAT MESSAGES - Kimi-style boxes
       ============================================ */
    
    /* Message container */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 8px 0 !important;
    }
    
    /* User message - right aligned, distinct color */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        margin: 8px 0 8px auto !important;
        max-width: 85% !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
    }
    
    /* Assistant message - left aligned */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: #16161e !important;
        border: 1px solid #252532 !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        margin: 8px auto 8px 0 !important;
        max-width: 90% !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
    }
    
    /* Message content text */
    .stChatMessage p, .stChatMessage span {
        color: #e0e0e0 !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
    }
    
    /* ============================================
       CHAT INPUT - Fixed at bottom, dark styling
       ============================================ */
    
    .stChatInput {
        position: fixed !important;
        bottom: 12px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 320px) !important; /* Account for sidebar */
        max-width: 800px !important;
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 16px !important;
        padding: 8px 16px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
        z-index: 9999 !important;
    }
    
    /* Input textarea */
    .stChatInput textarea {
        background: transparent !important;
        color: #e0e0e0 !important;
        font-size: 14px !important;
        border: none !important;
        min-height: 24px !important;
    }
    
    /* Input placeholder */
    .stChatInput textarea::placeholder {
        color: #666 !important;
    }
    
    /* ============================================
       SIDEBAR - Fixed, non-scrollable header
       ============================================ */
    
    [data-testid="stSidebar"] {
        background: #0f0f15 !important;
        border-right: 1px solid #1a1a2e !important;
    }
    
    /* Sidebar content container */
    [data-testid="stSidebar"] > div {
        padding-top: 0 !important;
    }
    
    /* Make sidebar header sticky */
    [data-testid="stSidebar"] .block-container {
        padding-top: 1rem !important;
    }
    
    /* Sidebar title */
    [data-testid="stSidebar"] h1 {
        font-size: 20px !important;
        font-weight: 700 !important;
        color: #fff !important;
        margin-bottom: 4px !important;
    }
    
    /* Sidebar sections */
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #888 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        margin-top: 16px !important;
        margin-bottom: 8px !important;
    }
    
    /* Sidebar text */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        font-size: 13px !important;
        color: #aaa !important;
    }
    
    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton button {
        background: #1a1a2e !important;
        color: #e0e0e0 !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        padding: 6px 12px !important;
        transition: all 0.2s !important;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        background: #252540 !important;
        border-color: #4a4a6a !important;
    }
    
    /* Toggle switches */
    [data-testid="stSidebar"] .stToggle {
        background: #1a1a2e !important;
    }
    
    /* Selectbox */
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        color: #e0e0e0 !important;
    }
    
    /* ============================================
       MAIN CONTENT AREA
       ============================================ */
    
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 100px !important; /* Space for fixed input */
        max-width: 900px !important;
    }
    
    /* ============================================
       CODE BLOCKS - Clean, bordered
       ============================================ */
    
    pre {
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        overflow-x: auto !important;
    }
    
    code {
        background: #252540 !important;
        color: #a5b4fc !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 13px !important;
        font-family: 'Monaco', 'Menlo', monospace !important;
    }
    
    /* ============================================
       EXPANDERS - Agent traces, details
       ============================================ */
    
    .streamlit-expanderHeader {
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 8px !important;
        color: #aaa !important;
        font-size: 13px !important;
    }
    
    .streamlit-expanderContent {
        background: #16161e !important;
        border: 1px solid #1a1a2e !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }
    
    /* ============================================
       STATUS / SPINNER
       ============================================ */
    
    .stStatus {
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 8px !important;
    }
    
    /* ============================================
       IMAGES - Rounded corners
       ============================================ */
    
    .stImage img {
        border-radius: 8px !important;
        border: 1px solid #2d2d44 !important;
    }
    
    /* ============================================
       FILE UPLOADER
       ============================================ */
    
    .stFileUploader {
        background: #1a1a2e !important;
        border: 2px dashed #2d2d44 !important;
        border-radius: 8px !important;
    }
    
    .stFileUploader > div {
        color: #888 !important;
    }
    
    /* ============================================
       DOWNLOAD BUTTONS
       ============================================ */
    
    .stDownloadButton button {
        background: #252540 !important;
        color: #a5b4fc !important;
        border: 1px solid #3d3d5c !important;
        border-radius: 6px !important;
        font-size: 12px !important;
        padding: 4px 12px !important;
    }
    
    /* ============================================
       SCROLLBAR
       ============================================ */
    
    ::-webkit-scrollbar {
        width: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2d2d44;
        border-radius: 3px;
    }
    
    /* ============================================
       HIDE STREAMLIT BRANDING
       ============================================ */
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ============================================
       AGENT TRACE SPECIFIC STYLING
       ============================================ */
    
    .agent-trace-box {
        background: #1a1a2e;
        border: 1px solid #2d2d44;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
    }
    
    .agent-step {
        font-size: 13px;
        color: #888;
        margin-bottom: 4px;
    }
    
    .agent-tool {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        background: #252540;
        border-radius: 6px;
        font-size: 12px;
        color: #a5b4fc;
    }
    
    /* ============================================
       MOBILE RESPONSIVE
       ============================================ */
    
    @media (max-width: 768px) {
        .stChatInput {
            width: calc(100% - 24px) !important;
        }
        
        [data-testid="stChatMessage"][data-testid*="user"],
        [data-testid="stChatMessage"][data-testid*="assistant"] {
            max-width: 95% !important;
        }
    }
</style>
"""
