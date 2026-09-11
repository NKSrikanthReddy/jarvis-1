"""Configuration management for JARVIS Personal Assistant."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Central configuration class.

    Precedence (highest wins):
      1. Explicit CLI flags (e.g. ``-n 10``)
      2. ``.env`` file / environment variables (e.g. ``DEFAULT_EMAIL_LIMIT``)
      3. Fallback defaults below in ``config.py``

    So: to change the max mails, edit ``DEFAULT_EMAIL_LIMIT`` in ``.env``
    (or re-run ``python setup.py`` step 4) — editing the fallback below
    only matters when ``.env`` does not set the value. Call
    ``Config.reload()`` to pick up ``.env`` edits without restarting.
    """

    # User Persona & Addressing
    USER_NAME: str = os.getenv("JARVIS_USER_NAME", "Sir")

    # LLM Settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv(
        "GOOGLE_API_KEY"
    )
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Gmail API OAuth Settings
    GMAIL_CREDENTIALS_PATH: Path = Path(
        os.getenv("GMAIL_CREDENTIALS_PATH", BASE_DIR / "credentials.json")
    )
    GMAIL_TOKEN_PATH: Path = Path(
        os.getenv("GMAIL_TOKEN_PATH", BASE_DIR / "token.json")
    )
    GMAIL_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    # IMAP Fallback Settings
    GMAIL_USER: Optional[str] = os.getenv("GMAIL_USER")
    GMAIL_APP_PASSWORD: Optional[str] = os.getenv("GMAIL_APP_PASSWORD")
    IMAP_SERVER: str = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    IMAP_FOLDER: str = os.getenv("IMAP_FOLDER", "INBOX")

    # Operational Defaults
    DEFAULT_EMAIL_LIMIT: int = int(os.getenv("DEFAULT_EMAIL_LIMIT", "10"))
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

    # Voice Settings
    ENABLE_VOICE: bool = os.getenv("ENABLE_VOICE", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    VOICE_RATE: int = int(os.getenv("VOICE_RATE", "185"))

    @classmethod
    def reload(cls) -> None:
        """Re-read ``.env`` + environment into every setting.

        Picks up ``.env`` edits at runtime (no restart needed). Values not
        present in ``.env``/environment fall back to ``config.py`` defaults.
        """
        load_dotenv(BASE_DIR / ".env", override=True)
        cls.USER_NAME = os.getenv("JARVIS_USER_NAME", "Sir")
        cls.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv(
            "GOOGLE_API_KEY"
        )
        cls.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        cls.GMAIL_CREDENTIALS_PATH = Path(
            os.getenv("GMAIL_CREDENTIALS_PATH", BASE_DIR / "credentials.json")
        )
        cls.GMAIL_TOKEN_PATH = Path(
            os.getenv("GMAIL_TOKEN_PATH", BASE_DIR / "token.json")
        )
        cls.GMAIL_USER = os.getenv("GMAIL_USER")
        cls.GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
        cls.IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
        cls.IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
        cls.IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")
        cls.DEFAULT_EMAIL_LIMIT = int(os.getenv("DEFAULT_EMAIL_LIMIT", "10"))
        cls.CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
        cls.ENABLE_VOICE = os.getenv("ENABLE_VOICE", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        cls.VOICE_RATE = int(os.getenv("VOICE_RATE", "185"))

    @classmethod
    def validate_llm(cls) -> bool:
        """Check if LLM API key is configured."""
        return bool(cls.GEMINI_API_KEY and len(cls.GEMINI_API_KEY.strip()) > 0)

    @classmethod
    def has_gmail_credentials(cls) -> bool:
        """Check if Gmail OAuth credentials exist."""
        return cls.GMAIL_CREDENTIALS_PATH.exists() or cls.GMAIL_TOKEN_PATH.exists()

    @classmethod
    def has_imap_credentials(cls) -> bool:
        """Check if IMAP credentials exist."""
        return bool(cls.GMAIL_USER and cls.GMAIL_APP_PASSWORD)
