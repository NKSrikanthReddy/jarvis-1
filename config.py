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
    """Central configuration class."""
    
    # User Persona & Addressing
    USER_NAME: str = os.getenv("JARVIS_USER_NAME", "Sir")
    
    # LLM Settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Gmail API OAuth Settings
    GMAIL_CREDENTIALS_PATH: Path = Path(os.getenv("GMAIL_CREDENTIALS_PATH", BASE_DIR / "credentials.json"))
    GMAIL_TOKEN_PATH: Path = Path(os.getenv("GMAIL_TOKEN_PATH", BASE_DIR / "token.json"))
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
    DEFAULT_EMAIL_LIMIT: int = int(os.getenv("DEFAULT_EMAIL_LIMIT", "5"))
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
    
    # Voice Settings
    ENABLE_VOICE: bool = os.getenv("ENABLE_VOICE", "false").lower() in ("true", "1", "yes")
    VOICE_RATE: int = int(os.getenv("VOICE_RATE", "185"))

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
