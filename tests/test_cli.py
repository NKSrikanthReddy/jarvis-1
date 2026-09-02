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
    assistant = JarvisAssistant(backend="mock", quiet=True)
    assert assistant.initialize() is True
    summary = assistant.run_cycle(limit=2)
    assert summary is not None
    assert len(summary) > 0
