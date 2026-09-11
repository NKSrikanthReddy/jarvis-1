# 🤖 J.A.R.V.I.S. — Personal AI Email Intelligence Assistant


> *"Just A Rather Very Intelligent System"* — A modular, local personal assistant in Python that fetches, analyzes, and delivers executive intelligence briefings for your unread emails using **Google GenAI SDK (Gemini 2.5 Flash)** and **Stark-grade terminal HUDs**.


---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| Language | Python 3.10+ | Core runtime |
| LLM | Google Gemini 2.5 Flash (`google-genai` ≥ 2.0, `google-generativeai` ≥ 0.8 fallback) | Executive email briefings with JARVIS persona |
| Gmail API | `google-api-python-client` ≥ 2.120, `google-auth-oauthlib` ≥ 1.2, `google-auth-httplib2` ≥ 0.2 | OAuth2 unread-mail fetch + mark-as-read |
| IMAP fallback | stdlib `imaplib` / `email` | SSL mailbox read via App Password / custom servers |
| Config | `python-dotenv` ≥ 1.0.1 | `.env` loading via `config.py` |
| Data models | `pydantic` ≥ 2.7 | `EmailMessage`, `JarvisBriefing`, attachments, actions |
| HTML parsing | `beautifulsoup4` ≥ 4.12.3 | HTML → text, script/style stripping |
| Terminal UI | `rich` ≥ 13.7.1 | Stark HUD: banner, tables, briefing panels, setup wizard |
| TTS (optional) | macOS `say` / `pyttsx3` | Spoken briefings (`--voice`) |
| Testing | `pytest` ≥ 8.1.0 | 18-test suite (readers, summarizer, CLI, cleaners) |
| Install | `install.sh` (bash + zsh) + `setup.py` TUI | venv bootstrap, dep install, interactive `.env` setup |

> Design rule: **no placeholder output.** Missing creds/API key is a hard, actionable error — never fake emails or a fake briefing. Mock data is explicit-only (`--mock`).

---

## ⚡ Highlights

- **Modular Architecture**: Clean, decoupled architecture under `modules/` for effortless integration of future agents (Voice TTS, Google Calendar, Web Scrapers, Slack/Discord bots).
- **Dual Email Backends (explicit, no silent fakes)**:
  - **Gmail API (OAuth2)**: Official Google API client with automatic token refreshing (`credentials.json` ➔ `token.json`).
  - **IMAP**: SSL IMAP reader (`imaplib`) for quick Gmail App Password or custom email servers.
  - **Mock Mode (explicit only)**: `--mock` / `--backend mock` returns synthetic mail for testing. `auto` mode **never** uses mock — it errors and points to `python setup.py`.
- **Gemini 2.5 Flash LLM Pipeline**:
  - Powered by the modern `google-genai` SDK (with `google-generativeai` fallback).
  - Tony Stark / JARVIS persona: crisp, razor-sharp, zero-fluff, surfacing critical action items, deadlines, and high-priority senders.
  - Missing/invalid key or API failure = clear `RuntimeError`, never an "offline placeholder" briefing.
- **Tactical Terminal HUD**: Built with `rich` for Stark Industries console styling, email queue tables, executive panels, and JSON export.
- **TUI Setup Wizard (`setup.py`)**: Rich-powered interactive setup — collects Gemini key, Gmail/IMAP creds, and defaults, validates them (optional live API + IMAP login tests), and writes a chmod-600 `.env`.
- **One-shot installer (`install.sh`)**: bash/zsh-compatible — creates `.venv`, installs deps, launches the setup wizard, and drops a `./jarvis` launcher.
- **Continuous Monitoring**: Run on-demand or in a background polling loop (`--interval 300` or `--watch`).
- **Voice Synthesis Support**: Built-in voice narration via native macOS `say` or `pyttsx3`.

---

## 🏗️ Project Architecture

```
jarvis/
├── install.sh                  # bash/zsh installer (venv + deps + setup wizard + ./jarvis launcher)
├── setup.py                    # Rich TUI setup wizard (API keys + mail creds → .env) + --check
├── jarvis                      # Generated launcher (created by install.sh; git-ignored)
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
└── tests/                    # Pytest Suite (18 tests)
    ├── __init__.py
    ├── test_email_reader.py  # Tests for IMAP/MIME parsing, Mock reader, backends
    ├── test_summarizer.py    # Tests for prompt construction + no-placeholder guarantees
    ├── test_text_cleaner.py  # Tests for MIME decoding & HTML sanitization
    └── test_cli.py           # CLI parsing, mock success/failure, auto-without-creds tests
```

---

## 🛠️ Prerequisites

- Python **3.10+** (`python3 --version`)
- A Gemini API key → https://aistudio.google.com/
- For real mail: **either** `credentials.json` (Gmail OAuth) **or** Gmail address + App Password (IMAP)
- Works in **bash or zsh**, macOS or Linux

---

## 🚀 Quickstart (recommended: installer + TUI setup)

```bash
git clone https://github.com/NKSrikanthReddy/jarvis-1.git
cd jarvis-1

# Full install: venv + deps + interactive TUI setup (API + mail inputs → .env) + ./jarvis launcher
./install.sh
# (also works as: bash install.sh  |  zsh install.sh)

# Validate anytime (no prompts)
./.venv/bin/python setup.py --check

# Test end-to-end with fake mail but your REAL Gemini key
./jarvis --mock -n 2

# Real run (auto-detects Gmail OAuth → IMAP; errors clearly if unconfigured)
./jarvis
```

Installer flags:

| Flag | Effect |
| :--- | :--- |
| `./install.sh` | Full install + TUI wizard |
| `./install.sh --skip-setup` | Deps only, skip wizard (run `./.venv/bin/python setup.py` later) |
| `./install.sh --check` | Deps + validate config, no prompts |
| `./install.sh --reinstall` | Wipe `.venv` and reinstall |

Manual alternative (same result, no script):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py
python main.py --mock -n 2
```

### TUI setup wizard (`setup.py`)

All API/mail inputs happen **inside the TUI** — you never hand-edit `.env` by hand:

1. **Identity** — how JARVIS addresses you (`JARVIS_USER_NAME`)
2. **Gemini key** — hidden password prompt, placeholder rejected, optional live API test, model choice
3. **Email backend** — `1` Gmail OAuth (default, no app password — wizard builds `credentials.json` from pasted JSON or Client ID + Secret, then optionally logs you in to create `token.json`) / `2` IMAP App Password (optional, only if you pick it) / `3` mock-only
4. **Defaults** — email limit, watch interval, voice on/off + rate

Writes `.env` (chmod 600, git-ignored) and prints next steps.

---

## 🚀 Manual env reference (what the wizard writes)

> **Config precedence (highest wins):** CLI flag (`-n 10`) → `.env` / environment (`DEFAULT_EMAIL_LIMIT`)
> → `config.py` fallback. So to change the max mails, edit `DEFAULT_EMAIL_LIMIT` in `.env`
> (or re-run `python setup.py` step 4) — editing the fallback in `config.py` alone has no
> effect while `.env` sets the value. Long-running code can pick up `.env` edits via `Config.reload()`.

---

## 🔑 Email Authentication Setup

> Preferred path: run `python setup.py` — it prompts for everything below with validation.
> `auto` mode tries Gmail OAuth → IMAP, and **fails with setup instructions if neither is configured** (it never shows fake mock mail).

```
[Auto Backend Resolution]
       │
       ▼
 1. credentials.json / token.json found? ───► YES ───► [Gmail API (OAuth 2.0)]
       │ (No / Failed → try IMAP)
       ▼
 2. GMAIL_USER & GMAIL_APP_PASSWORD set? ──► YES ───► [IMAP4_SSL (imap.gmail.com)]
       │ (No / Failed)
       ▼
 3. No credentials configured? ─────────────► HARD ERROR (run `python setup.py`)
    Mock mail ONLY with explicit `--mock` / `--backend mock`
```

### Option A: Gmail API with OAuth 2.0 (Recommended)
> Easiest path: pick `1` in `python setup.py` — it builds `credentials.json` for you from pasted JSON or Client ID + Secret, and can log you in on the spot to create `token.json`. Manual steps below are only if you prefer doing it by hand.
1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create/select a project (e.g. `JARVIS-Assistant`).
2. Enable the **Gmail API**: [console.cloud.google.com/apis/library/gmail.googleapis.com](https://console.cloud.google.com/apis/library/gmail.googleapis.com).
3. Configure the **OAuth Consent Screen** ([credentials/consent](https://console.cloud.google.com/apis/credentials/consent)) — User Type: *External*, add your email as a *Test User*.
4. Create an **OAuth client ID** ([credentials](https://console.cloud.google.com/apis/credentials)) > **Create Credentials** > **OAuth client ID**.
5. Select **Desktop App** as the Application Type.
7. Either paste the Client ID + Secret into the setup wizard, or download the JSON file, rename it to `credentials.json`, and place it in the `jarvis/` root directory.
8. On the first run, JARVIS will open a browser window for a one-time Google login and save `token.json`.

> **Fix `Error 400: redirect_uri_mismatch`:** the app logs in via `http://localhost:8080/`.
> It happens when your OAuth client is the **Web application** type instead of **Desktop app**.
> Either recreate the client as **Desktop app** (no extra setup), or keep the Web client and add
> `http://localhost:8080/` under APIs & Services > Credentials > your client > **Authorized redirect URIs**.
> (Also add your Gmail as a **Test User** on the consent screen, or Google blocks the login.)

---

### Option B: Gmail IMAP with App Password (Optional Alternative)
Only needed if you skip OAuth and pick IMAP in the wizard. If you prefer not to create a Google Cloud OAuth project:
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

### Option C: Mock Mode (explicit test only — needs a real Gemini key)
Simulated Stark mail for pipeline testing. Mock never triggers implicitly:
```bash
./jarvis --mock
# or: python main.py --mock -n 10
```
Note: `--mock` still calls the real Gemini API, so `GEMINI_API_KEY` must be set (via `setup.py`). Without it you get a clear error, not a placeholder briefing.

---

## 💻 CLI Usage & Commands (all work via `./jarvis` too)

### Basic Run (Summarize latest 5 unread emails)
```bash
./jarvis
# or: python main.py
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

Run the complete test suite with `pytest` (18 tests):
```bash
./.venv/bin/python -m pytest -v
# or: pytest -v   (inside activated venv)
```

Covers MIME parsing, HTML sanitization, mock readers, summarizer prompt logic + **no-placeholder guarantees** (missing key / API failure must raise, auto-without-creds must fail), and CLI commands.

---

## 🔒 Security & Privacy

- All email fetching and processing happens **locally** on your machine.
- Your credentials (`credentials.json`, `token.json`, and `.env`) are ignored by `.gitignore` and never transmitted anywhere other than the official Google API endpoints.
- Email contents sent to Gemini are processed in accordance with Google Cloud / AI Studio privacy terms.
