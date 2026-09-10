# 🤖 J.A.R.V.I.S. — Personal AI Email Intelligence Assistant


> *"Just A Rather Very Intelligent System"* — A modular, local personal assistant in Python that fetches, analyzes, and delivers executive intelligence briefings for your unread emails using **Google GenAI SDK (Gemini 2.5 Flash)** and **Stark-grade terminal HUDs**.


---

## ⚡ Highlights

- **Modular Architecture**: Clean, decoupled architecture under `modules/` for effortless integration of future agents (Voice TTS, Google Calendar, Web Scrapers, Slack/Discord bots).
- **Dual Email Backends with Auto-Fallback**:
  - **Gmail API (OAuth2)**: Official Google API client with automatic token refreshing (`credentials.json` ➔ `token.json`).
  - **IMAP Fallback**: SSL IMAP reader (`imaplib`) for quick Gmail App Password or custom email servers.
  - **Mock Mode**: Built-in realistic synthetic email simulation for testing without credentials.
- **Gemini 2.5 Flash LLM Pipeline**:
  - Powered by the modern `google-genai` SDK.
  - Tony Stark / JARVIS persona: crisp, razor-sharp, zero-fluff, surfacing critical action items, deadlines, and high-priority senders.
- **Tactical Terminal HUD**: Built with `rich` for Stark Industries console styling, email queue tables, executive panels, and JSON export.
- **Continuous Monitoring**: Run on-demand or in a background polling loop (`--interval 300` or `--watch`).
- **Voice Synthesis Support**: Built-in voice narration via native macOS `say` or `pyttsx3`.

---

## 🏗️ Project Architecture

```
jarvis/
├── .env.example              # Template for API keys and configuration
├── .gitignore                # Security filters (ignores tokens, keys, venv)
├── requirements.txt          # Python dependencies
├── README.md                 # Complete documentation and setup guide
├── config.py                 # Centralized configuration & environment loader
├── main.py                   # CLI entry point, scheduler loop, & HUD renderer
├── modules/                  # Pluggable Agent & Module Architecture
│   ├── __init__.py
│   ├── base.py               # Abstract BaseModule interface for custom extensions
│   ├── email_reader.py       # Gmail API (OAuth2) + IMAP4_SSL + Mock reader
│   ├── summarizer.py         # Gemini 2.5 Flash LLM summarization pipeline
│   ├── voice.py              # Text-to-Speech synthesizer (macOS 'say' / pyttsx3)
│   └── calendar_agent.py     # Modular calendar agent example for future expansion
├── utils/                    # Shared Utilities
│   ├── __init__.py
│   ├── models.py             # Pydantic data models (EmailMessage, JarvisBriefing, etc.)
│   ├── text_cleaner.py       # HTML stripper, MIME decoder, date parser, text sanitizer
│   └── logger.py             # Rich console themes, ASCII banners, tables, and HUD panels
└── tests/                    # Pytest Suite
    ├── __init__.py
    ├── test_email_reader.py  # Tests for IMAP/MIME parsing, Mock reader, backends
    ├── test_summarizer.py    # Tests for prompt construction & offline fallback
    ├── test_text_cleaner.py  # Tests for MIME decoding & HTML sanitization
    └── test_cli.py           # CLI argument parsing and execution tests
```

---

## 🚀 Quickstart

### 1. Clone or Open the Repository
```bash
cd jarvis
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the template file to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your API keys:
```env
# User name used in briefings
JARVIS_USER_NAME=Sir

# Gemini API Key (from https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

---

## 🔑 Email Authentication Setup

JARVIS automatically detects which email backend to use in the following order:

```
[Auto Backend Resolution]
       │
       ▼
 1. credentials.json / token.json found? ───► YES ───► [Gmail API (OAuth 2.0)]
       │ (No / Failed)
       ▼
 2. GMAIL_USER & GMAIL_APP_PASSWORD set? ──► YES ───► [IMAP4_SSL (imap.gmail.com)]
       │ (No / Failed)
       ▼
 3. No credentials configured? ─────────────► YES ───► [Mock Simulation Mode]
```

### Option A: Gmail API with OAuth 2.0 (Recommended)
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `JARVIS-Assistant`).
3. Enable the **Gmail API** in **APIs & Services > Library**.
4. Configure the **OAuth Consent Screen** (User Type: *External*, add your email as a *Test User*).
5. Go to **APIs & Services > Credentials** > **Create Credentials** > **OAuth client ID**.
6. Select **Desktop App** as the Application Type.
7. Download the JSON file, rename it to `credentials.json`, and place it in the `jarvis/` root directory.
8. On the first run, JARVIS will open a browser window for a one-time Google login and save `token.json`.

---

### Option B: Gmail IMAP with App Password (Fastest Real Setup)
If you prefer not to create a Google Cloud OAuth project:
1. Ensure **2-Step Verification** is enabled on your Google Account: [Google Security Settings](https://myaccount.google.com/security).
2. Generate an **App Password** at: [Google App Passwords](https://myaccount.google.com/apppasswords).
3. Set the name to `JARVIS` and copy the generated 16-character password.
4. Add the following to your `.env` file:
```env
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
```

---

### Option C: Mock Mode (Instant Test without Credentials)
You can run JARVIS immediately using simulated emails:
```bash
python main.py --mock
```

---

## 💻 CLI Usage & Commands

### Basic Run (Summarize latest 5 unread emails)
```bash
python main.py
```

### Summarize latest 10 emails
```bash
python main.py -n 10
```

### Run in Continuous Monitoring Loop (Poll every 60 seconds)
```bash
python main.py --interval 60
# Or using the default 5-minute watch mode:
python main.py --watch
```

### Explicitly Select Backend
```bash
# Force Gmail API
python main.py --backend gmail

# Force IMAP
python main.py --backend imap

# Force Mock Simulation
python main.py --mock
```

### Mark Processed Emails as Read
```bash
python main.py --mark-read
```

### Enable Spoken Audio Briefing (Voice)
```bash
python main.py --voice
```

### Export Structured JSON Output
```bash
python main.py --json
```

### Filter by Custom Gmail Query
```bash
python main.py --query "is:unread label:important"
```

---

## 🛠️ Command-Line Arguments Reference

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-n, --limit` | Maximum unread emails to fetch & summarize | `5` |
| `-i, --interval` | Continuous polling interval in seconds | `None` (one-shot) |
| `-w, --watch` | Run continuous loop with default 300s interval | `False` |
| `-b, --backend` | Email backend (`auto`, `gmail`, `imap`, `mock`) | `auto` |
| `-q, --query` | Search query / filter | `is:unread` |
| `--mark-read` | Mark processed emails as read | `False` |
| `-v, --voice` | Read briefing out loud via TTS | `False` |
| `--mock` | Force mock mode for testing without credentials | `False` |
| `--model` | Gemini model name | `gemini-2.5-flash` |
| `--json` | Output briefing & email data as JSON | `False` |
| `--quiet` | Suppress decorative banner and tables | `False` |

---

## 🧩 Extending JARVIS with New Modules

JARVIS uses an extensible `BaseModule` architecture (`modules/base.py`). To add a new capability (e.g. Google Calendar, Web Scraper, Voice Input):

1. Create a new file under `modules/` (e.g. `modules/web_scraper.py`):
```python
from modules.base import BaseModule
from utils.logger import print_status

class WebScraperModule(BaseModule):
    def __init__(self):
        super().__init__(name="WebScraper", description="Extracts web intelligence")

    def initialize(self) -> bool:
        self.is_initialized = True
        return True

    def execute(self, url: str, **kwargs):
        # Scraping logic here
        return {"url": url, "data": "Sample extracted content"}
```

2. Expose the new module in `modules/__init__.py` and invoke it from `main.py` or agent orchestrators.

---

## 🧪 Running Automated Tests

Run the complete test suite with `pytest`:
```bash
pytest -v
```

All unit tests covering MIME parsing, HTML sanitization, mock readers, summarizer prompt logic, and CLI commands will execute.

---

## 🔒 Security & Privacy

- All email fetching and processing happens **locally** on your machine.
- Your credentials (`credentials.json`, `token.json`, and `.env`) are ignored by `.gitignore` and never transmitted anywhere other than the official Google API endpoints.
- Email contents sent to Gemini are processed in accordance with Google Cloud / AI Studio privacy terms.
