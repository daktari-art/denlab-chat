"""Custom CSS - Clean dark interface with compact action buttons."""

DARK_THEME = """
<style>
    /* ============================================
       GLOBAL DARK BACKGROUND
       ============================================ */
    
    .stApp, [data-testid="stAppViewContainer"], .main, 
    [data-testid="stAppViewContainer"] > div:first-child {
        background-color: #0d0d0d !important;
    }
    
    /* ============================================
       HIDE DEFAULT STREAMLIT ELEMENTS
       ============================================ */
    
    #MainMenu, footer, header, .stDeployButton {
        display: none !important;
    }
    
    /* ============================================
       CHAT MESSAGES - Clean boxes
       ============================================ */
    
    /* Remove default Streamlit message styling */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 4px 0 !important;
        margin: 4px 0 !important;
    }
    
    /* User message */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        margin: 4px 0 4px auto !important;
        max-width: 80% !important;
    }
    
    /* Assistant message */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: #16161e !important;
        border: 1px solid #252532 !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        margin: 4px auto 4px 0 !important;
        max-width: 85% !important;
    }
    
    /* Message text */
    .stChatMessage p, .stChatMessage span, .stChatMessage div {
        color: #e0e0e0 !important;
        font-size: 14px !important;
        line-height: 1.5 !important;
    }
    
    /* Hide the avatar name labels */
    .stChatMessage [data-testid="stMarkdownContainer"] > div:first-child {
        font-size: 14px !important;
    }
    
    /* ============================================
       ACTION BUTTONS - Compact horizontal row
       ============================================ */
    
    /* Container for action buttons */
    .message-actions {
        display: flex !important;
        gap: 4px !important;
        margin-top: 6px !important;
        padding-top: 6px !important;
        border-top: 1px solid rgba(255,255,255,0.05) !important;
    }
    
    /* Compact icon buttons */
    .message-actions button, 
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        color: #666 !important;
        font-size: 12px !important;
        padding: 2px 6px !important;
        min-height: 24px !important;
        height: 24px !important;
        line-height: 1 !important;
        border-radius: 4px !important;
    }
    
    .message-actions button:hover {
        background: rgba(255,255,255,0.05) !important;
        color: #aaa !important;
    }
    
    /* ============================================
       CHAT INPUT
       ============================================ */
    
    .stChatInput {
        position: fixed !important;
        bottom: 12px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 340px) !important;
        max-width: 800px !important;
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 16px !important;
        padding: 8px 16px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
        z-index: 9999 !important;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        color: #e0e0e0 !important;
        font-size: 14px !important;
    }
    
    .stChatInput textarea::placeholder {
        color: #555 !important;
    }
    
    /* ============================================
       SIDEBAR
       ============================================ */
    
    [data-testid="stSidebar"] {
        background: #0f0f15 !important;
        border-right: 1px solid #1a1a2e !important;
    }
    
    [data-testid="stSidebar"] h1 {
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #fff !important;
    }
    
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #666 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        margin-top: 16px !important;
    }
    
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] div {
        font-size: 13px !important;
        color: #999 !important;
    }
    
    [data-testid="stSidebar"] .stButton button {
        background: #1a1a2e !important;
        color: #ccc !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 8px !important;
        font-size: 12px !important;
        padding: 6px 10px !important;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        background: #252540 !important;
        border-color: #3d3d5c !important;
    }
    
    /* ============================================
       CODE BLOCKS
       ============================================ */
    
    pre {
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }
    
    code {
        background: #252540 !important;
        color: #a5b4fc !important;
        padding: 2px 5px !important;
        border-radius: 4px !important;
        font-size: 12px !important;
    }
    
    /* ============================================
       EXPANDERS
       ============================================ */
    
    .streamlit-expanderHeader {
        background: #1a1a2e !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 8px !important;
        font-size: 12px !important;
        color: #888 !important;
    }
    
    /* ============================================
       IMAGES
       ============================================ */
    
    .stImage img {
        border-radius: 8px !important;
        border: 1px solid #2d2d44 !important;
    }
    
    /* ============================================
       DOWNLOAD BUTTONS
       ============================================ */
    
    .stDownloadButton button {
        background: #252540 !important;
        color: #a5b4fc !important;
        border: 1px solid #3d3d5c !important;
        border-radius: 6px !important;
        font-size: 11px !important;
        padding: 4px 10px !important;
    }
    
    /* ============================================
       SCROLLBAR
       ============================================ */
    
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #2d2d44; border-radius: 3px; }
    
    /* ============================================
       MOBILE
       ============================================ */
    
    @media (max-width: 768px) {
        .stChatInput { width: calc(100% - 20px) !important; }
        [data-testid="stChatMessage"][data-testid*="user"],
        [data-testid="stChatMessage"][data-testid*="assistant"] {
            max-width: 95% !important;
        }
    }
</style>
"""
