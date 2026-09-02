"""JARVIS Pluggable Modules and Agents."""

from modules.base import BaseModule
from modules.email_reader import EmailReader, GmailAPIReader, IMAPEmailReader, MockEmailReader
from modules.summarizer import EmailSummarizer
from modules.voice import VoiceModule
from modules.calendar_agent import CalendarAgent

__all__ = [
    "BaseModule",
    "EmailReader",
    "GmailAPIReader",
    "IMAPEmailReader",
    "MockEmailReader",
    "EmailSummarizer",
    "VoiceModule",
    "CalendarAgent",
]
