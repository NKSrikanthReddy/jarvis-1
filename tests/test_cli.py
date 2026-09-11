"""Tests for CLI argument parsing and orchestrator initialization."""

from main import build_cli_parser, JarvisAssistant


def test_cli_parser_defaults():
    parser = build_cli_parser()
    args = parser.parse_args([])
    assert args.limit == 5
    assert args.interval is None
    assert args.backend == "auto"
    assert args.mock is False
    assert args.voice is False
    assert args.mark_read is False


def test_cli_parser_custom_args():
    parser = build_cli_parser()
    args = parser.parse_args(["-n", "10", "--interval", "120", "--mock", "--voice", "--mark-read", "--backend", "imap"])
    assert args.limit == 10
    assert args.interval == 120
    assert args.mock is True
    assert args.voice is True
    assert args.mark_read is True
    assert args.backend == "imap"


def test_jarvis_assistant_mock_execution():
    """Mock backend initializes, but without a Gemini key run_cycle must
    return None (real error) — never a placeholder briefing."""
    import os
    old_gemini = os.environ.pop("GEMINI_API_KEY", None)
    old_google = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        assistant = JarvisAssistant(backend="mock", quiet=True)
        # Force no-key state regardless of ambient env
        assistant.summarizer.api_key = None
        assistant.summarizer.is_initialized = False
        assert assistant.initialize() is True
        summary = assistant.run_cycle(limit=2)
        assert summary is None
    finally:
        if old_gemini is not None:
            os.environ["GEMINI_API_KEY"] = old_gemini
        if old_google is not None:
            os.environ["GOOGLE_API_KEY"] = old_google


def test_jarvis_assistant_mock_success_with_stubbed_llm():
    """With a stubbed LLM, mock backend returns the real briefing text."""
    assistant = JarvisAssistant(backend="mock", quiet=True)
    assert assistant.initialize() is True
    assistant.summarizer.is_initialized = True
    assistant.summarizer._call_llm = lambda prompt: "STUBBED BRIEFING"
    summary = assistant.run_cycle(limit=2)
    assert summary == "STUBBED BRIEFING"


def test_auto_backend_fails_without_credentials():
    """Auto mode must fail clearly without creds — never silent mock data."""
    import os
    from pathlib import Path
    # Point Config at nonexistent credential files for this test
    from config import Config
    orig_creds = Config.GMAIL_CREDENTIALS_PATH
    orig_token = Config.GMAIL_TOKEN_PATH
    orig_user = Config.GMAIL_USER
    orig_pw = Config.GMAIL_APP_PASSWORD
    Config.GMAIL_CREDENTIALS_PATH = Path("/nonexistent-credentials.json")
    Config.GMAIL_TOKEN_PATH = Path("/nonexistent-token.json")
    Config.GMAIL_USER = None
    Config.GMAIL_APP_PASSWORD = None
    try:
        assistant = JarvisAssistant(backend="auto", quiet=True)
        assert assistant.initialize() is False
        assert assistant.email_reader.active_backend is None
    finally:
        Config.GMAIL_CREDENTIALS_PATH = orig_creds
        Config.GMAIL_TOKEN_PATH = orig_token
        Config.GMAIL_USER = orig_user
        Config.GMAIL_APP_PASSWORD = orig_pw
