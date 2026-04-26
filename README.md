# 🧪 DenLab Chat

Free AI chat with multi-provider fallback, user accounts, and persistent chat history. No API keys required.

## Features

- **🔐 User Accounts** - Simple signup/login with local JSON storage. No email required.
- **💬 Persistent Chat History** - Conversations survive page refreshes and browser restarts.
- **🤖 Multi-Provider AI** - Automatically falls back between providers if one fails:
  - **Pollinations.ai** (primary) - Uncensored, free
  - **AI.LS** (fallback) - GPT-4, Claude, Gemini, Llama
- **🛡️ Guardrails** - Content safety that keeps responses flowing instead of blocking
- **📦 Code Boxes** - Copy-to-clipboard code blocks with syntax highlighting
- **🤖 Agent Mode** - Autonomous task execution with step-by-step progress
- **📁 File Manager** - Upload, preview, and analyze code files
- **📥 Export** - Download conversations as Markdown

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/daktari-art/denlab-chat.git
cd denlab-chat

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. The app deploys automatically

> **Note on Streamlit Cloud:** Since the free tier doesn't persist local files, chat history resets on app sleep. For persistent storage on Streamlit Cloud, you'll need to integrate an external database (Supabase, Firebase, etc.).

### Deploy with Persistent Storage

For production with persistent accounts and chat history:

**Option 1: Self-hosted (Recommended)**
```bash
# Run on any VPS or local server
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

**Option 2: Docker**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

```bash
docker build -t denlab-chat .
docker run -p 8501:8501 -v denlab-data:/app/data denlab-chat
```

## Architecture

```
denlab-chat/
├── app.py              # Main Streamlit application
├── client.py           # Multi-provider AI client with guardrails
├── auth.py             # User authentication system
├── chat_db.py          # Chat history database
├── requirements.txt    # Python dependencies
├── .gitignore         # Git ignore rules
└── data/              # Local JSON storage (auto-created)
    ├── users.json      # User accounts
    ├── sessions.json   # Active sessions
    └── chats_*.json    # Per-user chat history
```

## API Providers

| Provider | Type | Status |
|----------|------|--------|
| Pollinations.ai | Text, Image, Audio | Primary |
| AI.LS | Text (GPT-4, Claude, Gemini) | Fallback |
| Z-Image.run | Image Generation | Image Fallback |
| Kokoro TTS | Text-to-Speech | Audio Fallback |

## Guardrails Explained

The guardrails system works in three layers:

1. **Input Sanitization** - Rewrites potentially triggering phrases to safer alternatives (e.g., "how to hack" → "how to secure systems against unauthorized access")
2. **Output Validation** - Detects model refusals and empty responses, automatically retrying with fallback providers
3. **Content Filtering** - HTML escaping, length limits, and truncation detection

This approach keeps the AI responsive while filtering actually harmful content, unlike traditional guardrails that often over-refuse legitimate requests.

## Migration from Old Version

If you have an existing `PollinationsClient` import, just change:
```python
from client import PollinationsClient  # Old

from client import MultiProviderClient  # New (drop-in replacement)
```

The `PollinationsClient` alias is kept for backward compatibility.

## License

MIT
