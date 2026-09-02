"""Tests for EmailReader module and IMAP/MIME parsing."""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from modules.email_reader import EmailReader, MockEmailReader, IMAPEmailReader
from utils.models import EmailMessage


def test_mock_email_reader():
    reader = MockEmailReader()
    emails = reader.fetch_unread_emails(limit=3)
    assert len(emails) == 3
    assert all(isinstance(em, EmailMessage) for em in emails)
    assert emails[0].sender.startswith("Pepper Potts")
    assert emails[0].is_unread is True

    # Test mark as read
    msg_id = emails[0].id
    assert reader.mark_as_read(msg_id) is True
    remaining = reader.fetch_unread_emails(limit=5)
    assert len(remaining) == 3
    assert not any(em.id == msg_id for em in remaining)


def test_imap_mime_parser():
    imap_reader = IMAPEmailReader()

    # Construct synthetic MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Test Mission Briefing"
    msg["From"] = "Jarvis Core <jarvis@stark.ai>"
    msg["To"] = "tony@starkindustries.com"
    msg["Date"] = "Wed, 02 Sep 2026 10:00:00 +0000"

    plain_part = MIMEText("This is a plain text briefing.\nAction: authorize flight plan.", "plain", "utf-8")
    html_part = MIMEText("<html><body><p>This is a plain text briefing.<br><b>Action:</b> authorize flight plan.</p></body></html>", "html", "utf-8")
    msg.attach(plain_part)
    msg.attach(html_part)

    # Attach a mock PDF
    pdf_attachment = MIMEApplication(b"%PDF-1.4 mock content", Name="flight_plan.pdf")
    pdf_attachment["Content-Disposition"] = 'attachment; filename="flight_plan.pdf"'
    msg.attach(pdf_attachment)

    raw_bytes = msg.as_bytes()
    parsed = imap_reader._parse_mime_bytes("999", raw_bytes)

    assert parsed is not None
    assert parsed.id == "999"
    assert parsed.subject == "Test Mission Briefing"
    assert "jarvis@stark.ai" in parsed.sender
    assert "authorize flight plan" in parsed.body_text
    assert len(parsed.attachments) == 1
    assert parsed.attachments[0].filename == "flight_plan.pdf"


def test_email_reader_auto_initialization():
    reader = EmailReader(backend="mock")
    assert reader.initialize() is True
    emails = reader.execute(limit=2)
    assert len(emails) == 2
    assert emails[0].source == "mock"
