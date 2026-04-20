"""Custom CSS themes."""

DARK_THEME = """
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #0f172a 100%);
    }
    .stChatMessage {
        background: rgba(255,255,255,0.03) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }
    .stChatInput {
        position: fixed !important;
        bottom: 20px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 90% !important;
        max-width: 800px !important;
        background: rgba(18, 18, 26, 0.9) !important;
        backdrop-filter: blur(20px);
        border-radius: 24px !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        z-index: 9999 !important;
    }
</style>
"""
