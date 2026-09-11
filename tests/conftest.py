"""Test isolation: neutralize ambient .env/environment so tests are hermetic.

Without this, a developer's real `.env` (API keys, custom limits, IMAP creds)
would leak into tests — e.g. `test_cli_parser_defaults` would see a custom
`DEFAULT_EMAIL_LIMIT`, or no-key tests would pick up a real `GEMINI_API_KEY`
and hit the live API. Every test therefore runs against pure `config.py`
fallbacks; `monkeypatch` restores the environment afterwards.
"""

import pytest

from config import Config

_TRACKED_VARS = [
    "JARVIS_USER_NAME",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_MODEL",
    "GMAIL_CREDENTIALS_PATH",
    "GMAIL_TOKEN_PATH",
    "GMAIL_USER",
    "GMAIL_APP_PASSWORD",
    "IMAP_SERVER",
    "IMAP_PORT",
    "IMAP_FOLDER",
    "DEFAULT_EMAIL_LIMIT",
    "CHECK_INTERVAL_SECONDS",
    "ENABLE_VOICE",
    "VOICE_RATE",
]


@pytest.fixture(autouse=True)
def _isolated_config(monkeypatch, tmp_path):
    for var in _TRACKED_VARS:
        monkeypatch.delenv(var, raising=False)
    # Nonexistent file -> load_dotenv is a no-op -> pure config.py fallbacks.
    Config.reload(env_file=tmp_path / ".env.test")
    yield
