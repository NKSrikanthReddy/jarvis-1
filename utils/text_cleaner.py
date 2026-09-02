"""Utilities for cleaning, sanitizing, and decoding email content."""

import re
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup


def decode_mime_words(header_value: Optional[str]) -> str:
    """Decode MIME-encoded header fields (e.g. Subject, From)."""
    if not header_value:
        return ""
    
    decoded_fragments = []
    try:
        parts = decode_header(header_value)
        for text, encoding in parts:
            if isinstance(text, bytes):
                encoding = encoding or "utf-8"
                try:
                    decoded_fragments.append(text.decode(encoding, errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    decoded_fragments.append(text.decode("latin1", errors="replace"))
            else:
                decoded_fragments.append(str(text))
        return "".join(decoded_fragments).strip()
    except Exception:
        return str(header_value)


def parse_email_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse standard RFC 2822 email date strings into Python datetime objects."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def clean_html_to_text(html_content: str) -> str:
    """Strip HTML tags and convert structure to clean readable plain text."""
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "head", "meta", "noscript", "svg"]):
            element.decompose()
            
        # Replace line-breaking elements with line breaks
        for br in soup.find_all(["br", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"]):
            br.insert_after("\n")
            
        text = soup.get_text()
        
        # Normalize whitespace and excessive blank lines
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return text.strip()
    except Exception:
        # Fallback to simple regex if BeautifulSoup fails
        clean = re.sub(r"<[^>]+>", " ", html_content)
        return re.sub(r"\s+", " ", clean).strip()


def sanitize_text(text: str, max_chars: Optional[int] = 8000) -> str:
    """Sanitize, normalize whitespace, and truncate text to prevent LLM context overflow."""
    if not text:
        return ""
    
    # Remove control characters except standard newlines and tabs
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or (ord(ch) >= 32 and ord(ch) != 127))
    
    # Compress excessive line breaks
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    
    if max_chars and len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + f"\n\n[... truncated {len(cleaned) - max_chars} characters by JARVIS ...]"
        
    return cleaned
