"""Tests for EmailSummarizer pipeline and prompt formulation."""

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


def test_offline_fallback_briefing():
    reader = MockEmailReader()
    emails = reader.fetch_unread_emails(limit=2)

    summarizer = EmailSummarizer(api_key=None)
    briefing = summarizer._generate_offline_fallback_briefing(emails)

    assert isinstance(briefing, JarvisBriefing)
    assert briefing.total_emails_processed == 2
    assert "JARVIS Executive Summary" in briefing.raw_response
    assert emails[0].subject in briefing.raw_response


def test_system_prompt_personalization():
    formatted = JARVIS_SYSTEM_INSTRUCTION.format(user_name="Mr. Stark")
    assert "Mr. Stark" in formatted
    assert "J.A.R.V.I.S." in formatted
