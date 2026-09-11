"""Tests for EmailSummarizer pipeline and prompt formulation."""

import pytest

from modules.summarizer import EmailSummarizer, JARVIS_SYSTEM_INSTRUCTION
from modules.email_reader import MockEmailReader
from utils.models import JarvisBriefing


def test_summarizer_prompt_construction():
    reader = MockEmailReader()
    emails = reader.fetch_unread_emails(limit=2)

    summarizer = EmailSummarizer(api_key=None)
    prompt = summarizer._build_prompt(emails)

    assert "Pepper Potts" in prompt
    assert "Avionics Telemetry" in prompt
    assert "EMAIL #1" in prompt
    assert "EMAIL #2" in prompt


def test_summarizer_empty_emails():
    summarizer = EmailSummarizer(api_key=None)
    briefing = summarizer.execute([])
    assert isinstance(briefing, JarvisBriefing)
    assert briefing.total_emails_processed == 0
    assert "clear" in briefing.executive_summary.lower()


def test_missing_api_key_raises_no_placeholder():
    """No API key must raise — never return fake/placeholder briefing text."""
    reader = MockEmailReader()
    emails = reader.fetch_unread_emails(limit=2)

    summarizer = EmailSummarizer(api_key=None)
    # Ensure env doesn't leak a real key into this test
    summarizer.api_key = None
    summarizer.is_initialized = False
    import os
    old_gemini = os.environ.pop("GEMINI_API_KEY", None)
    old_google = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            summarizer.execute(emails)
    finally:
        if old_gemini is not None:
            os.environ["GEMINI_API_KEY"] = old_gemini
        if old_google is not None:
            os.environ["GOOGLE_API_KEY"] = old_google


def test_api_failure_raises_no_placeholder(monkeypatch):
    """API errors must raise — never fall back to placeholder text."""
    reader = MockEmailReader()
    emails = reader.fetch_unread_emails(limit=2)

    summarizer = EmailSummarizer(api_key="test-key-invalid")
    summarizer.is_initialized = True
    summarizer._sdk_type = "genai"
    monkeypatch.setattr(summarizer, "_call_llm", lambda prompt: (_ for _ in ()).throw(Exception("boom")))
    with pytest.raises(RuntimeError, match="Gemini API call failed"):
        summarizer.execute(emails)


def test_success_path_returns_real_briefing(monkeypatch):
    """Monkeypatched LLM success returns the real model text verbatim."""
    reader = MockEmailReader()
    emails = reader.fetch_unread_emails(limit=2)

    summarizer = EmailSummarizer(api_key="test-key")
    summarizer.is_initialized = True
    monkeypatch.setattr(summarizer, "_call_llm", lambda prompt: "REAL BRIEFING TEXT")
    briefing = summarizer.execute(emails)
    assert isinstance(briefing, JarvisBriefing)
    assert briefing.total_emails_processed == 2
    assert briefing.raw_response == "REAL BRIEFING TEXT"


def test_system_prompt_personalization():
    formatted = JARVIS_SYSTEM_INSTRUCTION.format(user_name="Mr. Stark")
    assert "Mr. Stark" in formatted
    assert "J.A.R.V.I.S." in formatted
