"""Tests for text cleaning, MIME decoding, and HTML parsing."""

from utils.text_cleaner import clean_html_to_text, decode_mime_words, sanitize_text, parse_email_date


def test_clean_html_to_text():
    html = """
    <html>
        <head><title>Test</title><style>.hidden { display: none; }</style></head>
        <body>
            <h1>Stark Industries Status Report</h1>
            <p>The <b>Arc Reactor</b> is running at 100% capacity.<br>No issues detected.</p>
            <script>alert('malicious');</script>
        </body>
    </html>
    """
    text = clean_html_to_text(html)
    assert "Stark Industries Status Report" in text
    assert "Arc Reactor is running at 100% capacity." in text
    assert "alert" not in text
    assert "<style>" not in text


def test_decode_mime_words():
    # Test encoded subject header: =?UTF-8?B?SGVsbG8gV29ybGQ=?=
    encoded = "=?UTF-8?B?SGVsbG8gV29ybGQ=?="
    decoded = decode_mime_words(encoded)
    assert decoded == "Hello World"

    plain = "Simple Subject Line"
    assert decode_mime_words(plain) == "Simple Subject Line"
    assert decode_mime_words(None) == ""


def test_sanitize_text():
    raw = "Hello\n\n\n\n\nWorld\x00\x01with extra lines."
    cleaned = sanitize_text(raw, max_chars=100)
    assert "Hello\n\nWorld" in cleaned
    assert "\x00" not in cleaned


def test_parse_email_date():
    date_str = "Wed, 02 Sep 2026 09:30:00 +0000"
    dt = parse_email_date(date_str)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 2
