# ChatOff v2.2

Offline AI chatbot with PDF knowledge base. Uses Ollama, MySQL, and CustomTkinter.

## Quick start

```powershell
.\setup.ps1          # install deps, DB, models
python app.py        # launch app
```

Or manually: `pip install -r requirements.txt`, copy `.env.example` to `.env`, import `schema.sql`, `ollama pull llama3.2:3b`.

**Admin login:** `admin` / `admin123` (forced password change on first login). Use **Preview User Chat** in the admin sidebar to test the user UI.

## Project layout

```
ChatOff/
├── app.py                 # Application entry point
├── GUI.py                 # Re-export: from GUI import OfflineChatbot
├── login.py               # Login / sign-up windows
├── auth.py                # MySQL auth, chat history, topics
├── chatbot.py             # Ollama chat streaming
├── rag.py                 # Knowledge base (RAG)
├── rag_index.py           # Fast vector search
├── pdf_utils.py           # PDF extraction + chunking
├── change_password.py     # Password change dialog
├── password_utils.py      # bcrypt hashing
├── paths.py               # App directory + .env loading
├── json_utils.py          # JSON repair for Topic Builder
│
├── gui/                   # UI modules
│   ├── app.py             # Main window controller
│   ├── chat.py            # Chat screen
│   ├── admin.py           # Admin dashboard
│   ├── admin_embedded.py  # Topic Builder, Manage Topics
│   ├── dialogs.py         # Pop-up dialogs
│   ├── home.py            # Home + Info screens
│   ├── sidebar.py         # Session sidebar
│   ├── processing.py      # Loading overlay
│   └── theme.py           # Dark theme
│
├── scripts/               # Dev / QA tools
│   ├── system_test.py     # Full smoke test
│   ├── release_check.py   # Pre-release checks
│   └── benchmark_ollama.py  # Performance benchmark
│
├── migrations/            # SQL migrations for existing DBs
├── schema.sql             # Fresh database schema
├── requirements.txt       # Core dependencies
├── requirements-ocr.txt   # Optional OCR (scanned PDFs)
├── setup.ps1              # First-time setup
├── build.ps1              # Build exe + installer
└── ChatOff_Setup.iss      # Inno Setup script
```

## Testing & release

```powershell
python test.py              # quick GUI import test
python system_test.py       # full smoke test
python release_check.py     # pre-release checks
python benchmark_ollama.py  # performance benchmark
.\build.ps1                 # rebuild dist\app.exe + installer
```

Manual QA: see `QA_CHECKLIST.txt`.

## Performance defaults

| Setting | Default | Why |
|---------|---------|-----|
| `OLLAMA_MODEL` | `llama3.2:3b` | Faster than `llama3` on 8GB RAM |
| `OLLAMA_NUM_PREDICT` | `256` | Shorter replies, faster finish |
| `RAG_TOP_K` | `2` | Fewer PDF chunks injected |
| `RAG_MAX_CONTEXT_CHARS` | `3000` | Caps document context size |

Keep models loaded: `setx OLLAMA_KEEP_ALIVE "30m"` then restart Ollama.

For higher quality (slower): `OLLAMA_MODEL=llama3`, `OLLAMA_NUM_PREDICT=512`.

## Troubleshooting

- **DB errors** — import `schema.sql`, check `.env` `DB_PASSWORD`
- **Ollama errors** — restart Ollama; try `llama3.2:3b`
- **Short PDF answers** — re-upload PDFs after embed model change
- **Scanned PDFs** — `pip install -r requirements-ocr.txt`, install [Tesseract](https://github.com/tesseract-ocr/tesseract), set `RAG_OCR_ENABLED=true`
