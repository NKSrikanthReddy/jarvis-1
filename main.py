#!/usr/bin/env python3
"""JARVIS - Personal Assistant for Unread Email Intelligence & Summaries."""

import sys
import time
import argparse
import json
from typing import Optional
from datetime import datetime

from config import Config
from modules.email_reader import EmailReader
from modules.summarizer import EmailSummarizer
from modules.voice import VoiceModule
from utils.logger import (
    console,
    print_banner,
    print_status,
    print_success,
    print_warning,
    print_error,
    print_email_table,
    print_briefing_panel,
)


class JarvisAssistant:
    """Core JARVIS Assistant orchestrator."""

    def __init__(
        self,
        backend: str = "auto",
        model_name: str = Config.GEMINI_MODEL,
        enable_voice: bool = False,
        mark_read: bool = False,
        quiet: bool = False,
        json_output: bool = False,
    ):
        self.backend = backend
        self.mark_read = mark_read
        self.json_output = json_output
        self.quiet = quiet or json_output
        self.enable_voice = enable_voice or Config.ENABLE_VOICE
        
        self.email_reader = EmailReader(backend=self.backend)
        self.summarizer = EmailSummarizer(model_name=model_name)
        self.voice_module = VoiceModule() if self.enable_voice else None
        self.last_error: Optional[str] = None  # set when run_cycle fails (vs empty inbox)

    def initialize(self) -> bool:
        """Initialize all sub-modules.

        Returns True only if the email backend is ready. The Gemini
        summarizer is initialized lazily per-cycle so a missing API key
        produces a clear per-run error (never a placeholder briefing).
        """
        if not self.quiet:
            print_banner()
            print_status(f"Initializing JARVIS Core Systems for {Config.USER_NAME}...")

        # Initialize email reader (hard requirement — no silent mock fallback)
        reader_ok = self.email_reader.initialize()
        if not reader_ok:
            print_error("Email backend initialization failed. Run `python setup.py` to configure credentials.")
            return False

        # Pre-flight check for Gemini key so failures are explicit, not fake output.
        if not Config.validate_llm() and not self.summarizer.api_key:
            print_warning("GEMINI_API_KEY is not configured. Briefings will fail until you run `python setup.py`.")
            print_status("Tip: Get a key at https://aistudio.google.com/ — mock mode still needs a real key.")
        else:
            self.summarizer.initialize()

        # Initialize voice if enabled
        if self.voice_module:
            self.voice_module.initialize()

        return True

    def run_cycle(self, limit: int = Config.DEFAULT_EMAIL_LIMIT, query: str = "is:unread") -> Optional[str]:
        """Execute a single email intelligence cycle.

        Returns the briefing text on success, None on any failure.
        Failures print a real error — never a placeholder/fake briefing.
        Check `self.last_error` to distinguish errors from an empty inbox.
        """
        self.last_error = None
        if not self.quiet:
            print_status(f"Scanning unread emails [Limit: {limit}, Query: '{query}', Backend: {self.email_reader.active_backend}]...")

        try:
            # 1. Fetch unread emails
            emails = self.email_reader.execute(query=query, limit=limit)

            if not emails:
                # Distinguish "no mail" from "backend broken": execute() returns []
                # for both, but initialize() already gates misconfiguration.
                if not self.quiet:
                    if not self.email_reader.is_initialized or not self.email_reader.active_backend:
                        self.last_error = "Email backend is not initialized. Run `python setup.py`."
                        print_error(self.last_error)
                    else:
                        print_status(f"All clear, {Config.USER_NAME}. No unread messages in queue.")
                else:
                    if not self.email_reader.is_initialized or not self.email_reader.active_backend:
                        self.last_error = "Email backend is not initialized."
                return None

            if not self.quiet:
                print_email_table([e.model_dump() for e in emails])
                print_status("Engaging Gemini 2.5 Flash intelligence engine for executive briefing...")

            # 2. Generate JARVIS summary briefing (raises RuntimeError on missing key/API failure)
            try:
                briefing = self.summarizer.execute(emails)
            except RuntimeError as e:
                self.last_error = str(e)
                print_error(self.last_error)
                return None

            # 3. Render Output
            if self.json_output:
                output_data = {
                    "timestamp": datetime.now().isoformat(),
                    "total_unread": len(emails),
                    "emails": [e.model_dump(mode="json") for e in emails],
                    "briefing": briefing.model_dump(mode="json"),
                }
                print(json.dumps(output_data, indent=2, default=str))
            elif not self.quiet:
                print_briefing_panel(
                    briefing.raw_response,
                    title=f"JARVIS Briefing • {len(emails)} Unread Message(s)"
                )
            else:
                console.print(briefing.raw_response)

            # 4. Spoken Voice Output if enabled
            if self.voice_module and self.enable_voice:
                summary_speech = briefing.raw_response.split("##")[0] if "##" in briefing.raw_response else briefing.raw_response[:300]
                self.voice_module.execute(f"Briefing complete, {Config.USER_NAME}. {summary_speech}")

            # 5. Mark as read if configured
            if self.mark_read:
                print_status("Marking processed emails as read...")
                for email_msg in emails:
                    self.email_reader.mark_as_read(email_msg.id)
                print_success("Processed emails marked as read.")

            return briefing.raw_response

        except Exception as e:
            self.last_error = f"Error occurred during briefing cycle: {e}"
            print_error(self.last_error)
            return None

    def run_loop(self, interval_seconds: int, limit: int = Config.DEFAULT_EMAIL_LIMIT, query: str = "is:unread") -> None:
        """Run continuous monitoring loop at specified interval."""
        print_status(f"JARVIS continuous monitoring active. Polling every {interval_seconds}s (Press Ctrl+C to stop)...")
        
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                now_str = datetime.now().strftime("%H:%M:%S")
                console.print(f"\n[bold cyan]─── [Cycle #{cycle_count} • {now_str}] ───[/bold cyan]")
                
                self.run_cycle(limit=limit, query=query)
                
                console.print(f"[dim cyan]Sleeping for {interval_seconds} seconds until next scan...[/dim cyan]")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]⚡ JARVIS monitoring paused by user. Standing by.[/bold yellow]")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Cleanly shutdown modules."""
        if self.email_reader:
            self.email_reader.shutdown()
        if self.summarizer:
            self.summarizer.shutdown()


def build_cli_parser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="JARVIS - Personal AI Assistant for Email Intelligence & Executive Summaries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Summarize latest 5 unread emails (auto-detects Gmail API or IMAP)
  python main.py

  # Summarize latest 10 unread emails with mock simulation
  python main.py --mock -n 10

  # Run in continuous interval loop every 60 seconds
  python main.py --interval 60

  # Use IMAP backend explicitly and mark processed emails as read
  python main.py --backend imap --mark-read

  # Enable voice speech synthesis
  python main.py --voice
        """,
    )
    
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=Config.DEFAULT_EMAIL_LIMIT,
        help=f"Number of latest unread emails to summarize (default: {Config.DEFAULT_EMAIL_LIMIT})",
    )
    
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=None,
        help="Run in a recurring loop with the specified interval in seconds",
    )
    
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help=f"Continuous watch mode using default interval ({Config.CHECK_INTERVAL_SECONDS}s)",
    )
    
    parser.add_argument(
        "-b", "--backend",
        choices=["auto", "gmail", "imap", "mock"],
        default="auto",
        help="Email provider backend (default: auto)",
    )
    
    parser.add_argument(
        "-q", "--query",
        type=str,
        default="is:unread",
        help="Search query filter (default: 'is:unread' or 'UNSEEN')",
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force mock email reader mode for instant testing without real credentials",
    )
    
    parser.add_argument(
        "--mark-read",
        action="store_true",
        help="Mark processed emails as read",
    )
    
    parser.add_argument(
        "-v", "--voice",
        action="store_true",
        help="Enable spoken audio briefing via macOS 'say' / TTS",
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=Config.GEMINI_MODEL,
        help=f"Gemini model name (default: {Config.GEMINI_MODEL})",
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress banner and styling; print raw summary only",
    )

    return parser


def main():
    """Main CLI entry point."""
    parser = build_cli_parser()
    args = parser.parse_args()

    backend = "mock" if args.mock else args.backend
    interval = args.interval if args.interval is not None else (Config.CHECK_INTERVAL_SECONDS if args.watch else None)

    assistant = JarvisAssistant(
        backend=backend,
        model_name=args.model,
        enable_voice=args.voice,
        mark_read=args.mark_read,
        quiet=args.quiet,
        json_output=args.json,
    )

    if not assistant.initialize():
        print_error("Failed to initialize JARVIS assistant. Run `python setup.py` first.")
        sys.exit(1)

    if interval:
        assistant.run_loop(interval_seconds=interval, limit=args.limit, query=args.query)
    else:
        result = assistant.run_cycle(limit=args.limit, query=args.query)
        if result is None and assistant.last_error:
            # Real failure (bad creds/key/API) — exit non-zero so scripts detect it.
            # Empty inbox keeps exit 0.
            sys.exit(1)


if __name__ == "__main__":
    main()
