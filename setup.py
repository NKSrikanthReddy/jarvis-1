#!/usr/bin/env python3
"""JARVIS interactive TUI setup wizard.

Collects all API keys / mail credentials inside the terminal UI and writes
a local `.env` file. Run via `./install.sh` or directly:

    python setup.py            # interactive wizard
    python setup.py --check    # validate existing .env / credentials

No fake data is ever written — placeholders from `.env.example` are rejected.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
except ImportError:
    print("setup.py requires 'rich'. Install with: pip install -r requirements.txt")
    sys.exit(1)

console = Console()

BANNER = """
[bold cyan]   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗[/bold cyan]
[bold cyan]   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝[/bold cyan]
[bold cyan]   ██║███████║██████╔╝██║   ██║██║███████╗[/bold cyan]
[bold cyan]██╗██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║[/bold cyan]
[bold cyan]╚████║██║  ██║██║  ██║ ╚████╔╝ ██║███████║[/bold cyan]
[bold cyan] ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝[/bold cyan]
[dim cyan]      Just A Rather Very Intelligent System — Setup Wizard[/dim cyan]
"""

PLACEHOLDER_PATTERNS = ("your_", "xxxx", "changeme", "placeholder", "example")


def is_placeholder(value: str) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return True
    return any(p in v for p in PLACEHOLDER_PATTERNS)


def load_existing_env() -> dict:
    """Read existing .env (if any) without importing config (no dotenv hard dep)."""
    data: dict = {}
    try:
        from dotenv import dotenv_values  # type: ignore
        data = {k: v for k, v in dotenv_values(ENV_PATH).items() if v is not None}
        return data
    except Exception:
        pass
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            data[k.strip()] = v.strip().strip('"').strip("'")
    # Fall back to live environment for defaults
    for k in list(os.environ.keys()):
        if k.startswith(("GEMINI_", "GOOGLE_", "GMAIL_", "IMAP_", "JARVIS_", "DEFAULT_", "CHECK_", "ENABLE_", "VOICE_")):
            data.setdefault(k, os.environ[k])
    return data


def ask_secret(prompt_text: str, default: str = "") -> str:
    """Password-style prompt that works in bash/zsh terminals."""
    suffix = f" [current: ••••••{len(default)} chars]" if default and not is_placeholder(default) else ""
    console.print(f"[bold cyan]?[/] {prompt_text}{suffix} [dim](input hidden)[/dim]")
    try:
        val = getpass.getpass("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        raise KeyboardInterrupt
    if not val:
        return default
    return val


def ask_text(prompt_text: str, default: str = "", allow_empty: bool = False) -> str:
    while True:
        val = Prompt.ask(f"[bold cyan]?[/] {prompt_text}", default=default or None, show_default=bool(default))
        val = (val or "").strip()
        if val or allow_empty or default:
            return val or default
        console.print("[yellow]Value cannot be empty.[/yellow]")


def valid_email(addr: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", addr.strip()))


def test_gemini_key(api_key: str, model: str) -> tuple[bool, str]:
    """Optional live check: minimal Gemini call. Returns (ok, message)."""
    try:
        from google import genai  # modern SDK
        client = genai.Client(api_key=api_key)
        from google.genai import types
        resp = client.models.generate_content(
            model=model,
            contents="Reply with exactly: JARVIS-OK",
            config=types.GenerateContentConfig(temperature=0),
        )
        text = (resp.text or "").strip()
        if text:
            return True, f"Gemini responded ({len(text)} chars)."
        return False, "Gemini returned an empty response."
    except ImportError:
        pass
    try:
        import google.generativeai as gai  # legacy SDK fallback
        gai.configure(api_key=api_key)
        m = gai.GenerativeModel(model_name=model)
        resp = m.generate_content("Reply with exactly: JARVIS-OK")
        if (resp.text or "").strip():
            return True, "Gemini responded via legacy SDK."
        return False, "Gemini returned an empty response."
    except Exception as e:
        return False, str(e)[:300]
    return False, "google-genai SDK not installed; skipping live test."


def test_imap_login(user: str, password: str, server: str, port: int) -> tuple[bool, str]:
    import imaplib
    try:
        client = imaplib.IMAP4_SSL(server, port)
        client.login(user, password)
        try:
            client.logout()
        except Exception:
            pass
        return True, "IMAP login succeeded."
    except Exception as e:
        return False, str(e)[:300]


def check_credentials_json(path_str: str) -> tuple[bool, str]:
    p = (BASE_DIR / path_str) if not os.path.isabs(path_str) else Path(path_str)
    if not p.exists():
        return False, f"File not found: {p}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"Invalid JSON: {e}"
    if "installed" in data or "web" in data:
        return True, "OAuth client secrets look valid."
    return False, "JSON lacks 'installed' or 'web' OAuth client section."


def build_oauth_client_json(client_id: str, client_secret: str, project_id: str = "") -> dict:
    """Build a Desktop-app credentials.json dict from raw OAuth details."""
    return {
        "installed": {
            "client_id": client_id.strip(),
            "project_id": project_id.strip(),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret.strip(),
            "redirect_uris": ["http://localhost"],
        }
    }


def write_credentials_file(path_str: str, data: dict) -> Path:
    """Write credentials.json (chmod 600) and return its path."""
    p = (BASE_DIR / path_str) if not os.path.isabs(path_str) else Path(path_str)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass
    return p


def read_pasted_json() -> tuple[dict | None, str]:
    """Read multi-line pasted JSON from stdin, terminated by END on its own line."""
    console.print("[dim]Paste the JSON content below. When done, type [bold]END[/bold] on its own line and press Enter.[/dim]")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt
        if line.strip() == "END":
            break
        lines.append(line)
    raw = "\n".join(lines).strip()
    if not raw:
        return None, "Nothing was pasted."
    try:
        data = json.loads(raw)
    except Exception as e:
        return None, f"That is not valid JSON: {e}"
    if not isinstance(data, dict) or ("installed" not in data and "web" not in data):
        return None, "JSON lacks 'installed' or 'web' OAuth client section."
    return data, "ok"


def run_gmail_oauth_now(creds_path: str, token_path: str) -> tuple[bool, str]:
    """Run the one-time browser OAuth flow immediately, saving token.json."""
    try:
        from modules.email_reader import GmailAPIReader
    except Exception as e:
        return False, f"Could not load email module: {e}"
    try:
        reader = GmailAPIReader(
            credentials_path=(BASE_DIR / creds_path) if not os.path.isabs(creds_path) else Path(creds_path),
            token_path=(BASE_DIR / token_path) if not os.path.isabs(token_path) else Path(token_path),
        )
        ok = reader.authenticate()
        return (True, "Authenticated — token.json saved.") if ok else (False, "Authentication did not complete.")
    except Exception as e:
        return False, str(e)[:300]


def run_check() -> int:
    """Validate existing configuration; exit 0 if runnable, 1 otherwise."""
    console.print(Panel("JARVIS configuration check", style="cyan"))
    env = load_existing_env()
    table = Table(show_header=True, header_style="bold yellow", border_style="cyan", expand=True)
    table.add_column("Setting")
    table.add_column("Status")
    ok_all = True

    def row(name: str, ok: bool, detail: str):
        nonlocal ok_all
        if not ok:
            ok_all = False
        table.add_row(name, f"[green]OK[/green] {detail}" if ok else f"[red]MISSING/INVALID[/red] {detail}")

    user = env.get("JARVIS_USER_NAME", "")
    row("JARVIS_USER_NAME", bool(user) and not is_placeholder(user), user or "—")

    key = env.get("GEMINI_API_KEY", "") or env.get("GOOGLE_API_KEY", "")
    row("GEMINI_API_KEY", bool(key) and not is_placeholder(key) and len(key.strip()) >= 10,
        f"{len(key.strip())} chars" if key and not is_placeholder(key) else "run `python setup.py`")

    model = env.get("GEMINI_MODEL", "gemini-2.5-flash")
    row("GEMINI_MODEL", bool(model), model or "—")

    creds_path = env.get("GMAIL_CREDENTIALS_PATH", "credentials.json")
    ok_c, msg_c = check_credentials_json(creds_path)
    imap_user = env.get("GMAIL_USER", "")
    imap_pw = env.get("GMAIL_APP_PASSWORD", "")
    imap_ok = bool(imap_user) and not is_placeholder(imap_user) and valid_email(imap_user) \
        and bool(imap_pw) and not is_placeholder(imap_pw)
    row("Gmail OAuth (credentials.json)", ok_c, msg_c)
    row("IMAP (GMAIL_USER + APP_PASSWORD)", imap_ok,
        imap_user if imap_ok else "not configured (or placeholder)")

    console.print(table)
    if ok_c or imap_ok:
        console.print("[green]Email backend: configured.[/green]")
    else:
        console.print("[red]Email backend: NOT configured — run `python setup.py`.[/red]")
        ok_all = False
    if not ok_all:
        console.print("\n[yellow]Fix with:[/yellow] python setup.py")
        return 1
    console.print("\n[green]All required settings look good. Try: python main.py --mock (test) or python main.py[/green]")
    return 0


def main() -> None:
    if "--check" in sys.argv or "--validate" in sys.argv:
        sys.exit(run_check())
    if "--help" in sys.argv or "-h" in sys.argv:
        console.print(Panel("Usage:\n  python setup.py           interactive wizard\n  python setup.py --check   validate .env / credentials", title="JARVIS Setup"))
        return

    console.print(BANNER)
    console.print(Panel(
        "This wizard collects your [bold]Gemini API key[/bold] and [bold]mail credentials[/bold] "
        "and writes them to a local [bold].env[/bold] file (chmod 600, never committed).\n"
        "Nothing is sent anywhere — values stay on this machine.",
        title="[bold yellow]⚡ JARVIS Setup[/bold yellow]", border_style="cyan",
    ))

    existing = load_existing_env()
    if ENV_PATH.exists():
        console.print(f"[dim]Found existing .env — values shown as defaults. Leave blank + Enter to keep.[/dim]")
        if not Confirm.ask("Continue (overwrite .env at the end)?", default=True):
            console.print("Aborted. No changes written.")
            return

    # ---- 1. User persona ----
    console.print("\n[bold yellow]── Step 1/4 · Identity ──[/bold yellow]")
    default_user = existing.get("JARVIS_USER_NAME", "Sir")
    user_name = ask_text("How should JARVIS address you", default=default_user)

    # ---- 2. Gemini API key ----
    console.print("\n[bold yellow]── Step 2/4 · Gemini API key (required — no placeholder output otherwise) ──[/bold yellow]")
    console.print("[dim]Get a key at https://aistudio.google.com/ → Get API Key. It stays in local .env only.[/dim]")
    default_model = existing.get("GEMINI_MODEL", "gemini-2.5-flash")
    existing_key = existing.get("GEMINI_API_KEY", "") or existing.get("GOOGLE_API_KEY", "")
    if is_placeholder(existing_key):
        existing_key = ""
    while True:
        api_key = ask_secret("Paste GEMINI_API_KEY", default=existing_key)
        if is_placeholder(api_key):
            console.print("[red]A real API key is required. Placeholder text is not accepted.[/red]")
            continue
        if len(api_key.strip()) < 10:
            console.print("[red]That key looks too short. Paste the full key from AI Studio.[/red]")
            continue
        break
    model = ask_text("Gemini model", default=default_model)
    if Confirm.ask("Test the Gemini key now (one tiny API call)?", default=False):
        console.print("[dim]Testing…[/dim]")
        ok, msg = test_gemini_key(api_key.strip(), model.strip())
        console.print(f"[green]✔ {msg}[/green]" if ok else f"[red]✖ Key test failed: {msg}[/red]")
        if not ok and not Confirm.ask("Keep this key anyway?", default=True):
            console.print("Aborted. No changes written.")
            return

    # ---- 3. Email backend ----
    console.print("\n[bold yellow]── Step 3/4 · Email backend ──[/bold yellow]")
    console.print("  [bold]1[/bold]  Gmail OAuth  (recommended — just a credentials.json file, NO app password needed)")
    console.print("  [bold]2[/bold]  IMAP App Password  (optional alternative — only pick this if you want it)")
    console.print("  [bold]3[/bold]  Mock only  (testing with fake emails — real runs will refuse without creds)")
    console.print("[dim]App Password is ONLY needed for option 2. Default (1) never asks for it.[/dim]")
    choice = Prompt.ask("Choose backend", choices=["1", "2", "3"], default="1")

    creds_path = existing.get("GMAIL_CREDENTIALS_PATH", "credentials.json")
    token_path = existing.get("GMAIL_TOKEN_PATH", "token.json")
    gmail_user = existing.get("GMAIL_USER", "")
    gmail_pw = existing.get("GMAIL_APP_PASSWORD", "")
    if is_placeholder(gmail_user):
        gmail_user = ""
    if is_placeholder(gmail_pw):
        gmail_pw = ""
    imap_server = existing.get("IMAP_SERVER", "imap.gmail.com")
    imap_port = existing.get("IMAP_PORT", "993")
    imap_folder = existing.get("IMAP_FOLDER", "INBOX")

    if choice == "1":
        console.print("[dim]The wizard builds credentials.json for you — just copy 2 strings from[/dim]")
        console.print("[dim]Google Cloud Console → enable Gmail API → OAuth client (Desktop app).[/dim]")
        creds_path = ask_text("Where to save credentials.json", default=creds_path)
        token_path = ask_text("OAuth token file", default=token_path)

        have_valid = False
        ok_c, msg_c = check_credentials_json(creds_path)
        if ok_c:
            console.print(f"[green]✔ Found valid credentials file: {msg_c}[/green]")
            if Confirm.ask("Keep it and skip entering details?", default=True):
                have_valid = True

        if not have_valid:
            console.print("How do you want to provide the OAuth client?")
            console.print("  [bold]1[/bold]  Paste the downloaded JSON content (easiest if you have it)")
            console.print("  [bold]2[/bold]  Type Client ID + Client Secret (wizard builds the file)")
            console.print("  [bold]3[/bold]  Skip for now (add credentials.json later)")
            how = Prompt.ask("Choose", choices=["1", "2", "3"], default="1")
            if how == "1":
                while True:
                    try:
                        data, msg = read_pasted_json()
                    except KeyboardInterrupt:
                        raise
                    if data is None:
                        console.print(f"[red]{msg}[/red]")
                        if Confirm.ask("Try pasting again?", default=True):
                            continue
                        console.print("[yellow]Skipped — Gmail runs will fail until credentials.json exists.[/yellow]")
                        break
                    p = write_credentials_file(creds_path, data)
                    console.print(f"[green]✔ Saved OAuth client to {p}[/green]")
                    break
            elif how == "2":
                while True:
                    cid = ask_text("OAuth Client ID (ends with .apps.googleusercontent.com)", default="")
                    if not cid:
                        console.print("[red]Client ID is required.[/red]")
                        continue
                    if not cid.strip().endswith(".apps.googleusercontent.com"):
                        console.print("[yellow]That doesn't look like a Google Client ID (should end with .apps.googleusercontent.com).[/yellow]")
                        if not Confirm.ask("Use it anyway?", default=False):
                            continue
                    break
                csec = ask_secret("OAuth Client Secret")
                while not csec or is_placeholder(csec):
                    console.print("[red]Client Secret is required (placeholder not accepted).[/red]")
                    csec = ask_secret("OAuth Client Secret")
                pid = ask_text("Google Cloud Project ID", default="", allow_empty=True)
                p = write_credentials_file(creds_path, build_oauth_client_json(cid, csec, pid))
                console.print(f"[green]✔ Generated {p} from your Client ID + Secret.[/green]")
            else:
                console.print("[yellow]Skipped — drop credentials.json in later; Gmail runs will fail until then.[/yellow]")

        ok_c, msg_c = check_credentials_json(creds_path)
        console.print(f"[green]✔ {msg_c}[/green]" if ok_c else f"[yellow]⚠ {msg_c} — Gmail runs will fail until fixed.[/yellow]")
        if ok_c and Confirm.ask("Log in with Google now (opens browser, saves token.json)?", default=False):
            console.print("[dim]Opening browser for one-time Google login…[/dim]")
            ok_a, msg_a = run_gmail_oauth_now(creds_path, token_path)
            console.print(f"[green]✔ {msg_a}[/green]" if ok_a else f"[yellow]⚠ {msg_a}[/yellow]")
        # Still collect IMAP as optional fallback?
        if Confirm.ask("Also configure IMAP App Password as fallback?", default=False):
            choice = "12"  # both
        else:
            gmail_user, gmail_pw = "", ""
    if choice in ("2", "12"):
        console.print("[dim]Google Account → Security → 2-Step Verification ON → App passwords → generate → 16-char code.[/dim]")
        while True:
            gmail_user = ask_text("Gmail address (GMAIL_USER)", default=gmail_user)
            if valid_email(gmail_user):
                break
            console.print("[red]Enter a valid email address.[/red]")
        while True:
            gmail_pw = ask_secret("Gmail App Password (16 chars, spaces OK)", default=gmail_pw)
            compact = gmail_pw.replace(" ", "").replace("-", "")
            if is_placeholder(gmail_pw) or len(compact) < 12:
                console.print("[red]Paste the full App Password (16 characters). Placeholder not accepted.[/red]")
                continue
            break
        imap_server = ask_text("IMAP server", default=imap_server)
        while True:
            port_raw = ask_text("IMAP port", default=str(imap_port))
            if port_raw.isdigit() and 1 <= int(port_raw) <= 65535:
                imap_port = port_raw
                break
            console.print("[red]Port must be 1-65535.[/red]")
        imap_folder = ask_text("IMAP folder", default=imap_folder)
        if Confirm.ask("Test IMAP login now?", default=True):
            console.print("[dim]Testing IMAP login…[/dim]")
            ok, msg = test_imap_login(gmail_user.strip(), gmail_pw.strip(), imap_server.strip(), int(imap_port))
            console.print(f"[green]✔ {msg}[/green]" if ok else f"[red]✖ IMAP test failed: {msg}[/red]")
            if not ok and not Confirm.ask("Save these IMAP settings anyway?", default=True):
                console.print("Aborted. No changes written.")
                return
    if choice == "3":
        gmail_user, gmail_pw = "", ""
        console.print("[yellow]Mock-only: no real email configured. `python main.py` (auto) will refuse; use `python main.py --mock` for tests.[/yellow]")

    # ---- 4. Operational defaults ----
    console.print("\n[bold yellow]── Step 4/4 · Defaults ──[/bold yellow]")
    default_limit = existing.get("DEFAULT_EMAIL_LIMIT", "5")
    default_interval = existing.get("CHECK_INTERVAL_SECONDS", "300")
    default_voice = existing.get("ENABLE_VOICE", "false")
    default_rate = existing.get("VOICE_RATE", "185")
    limit = ask_text("Default emails per briefing (DEFAULT_EMAIL_LIMIT)", default=str(default_limit))
    interval = ask_text("Watch interval seconds (CHECK_INTERVAL_SECONDS)", default=str(default_interval))
    voice = "true" if Confirm.ask("Enable voice briefings by default?", default=str(default_voice).lower() in ("1", "true", "yes")) else "false"
    rate = ask_text("Voice rate (VOICE_RATE)", default=str(default_rate))

    # ---- Write .env ----
    lines = [
        "# JARVIS Personal Assistant — generated by `python setup.py`. Do not commit.",
        f"JARVIS_USER_NAME={user_name}",
        "",
        "# Gemini LLM",
        f"GEMINI_API_KEY={api_key.strip()}",
        f"GEMINI_MODEL={model.strip()}",
        "",
        "# Gmail OAuth",
        f"GMAIL_CREDENTIALS_PATH={creds_path}",
        f"GMAIL_TOKEN_PATH={token_path}",
        "",
        "# IMAP fallback",
        f"GMAIL_USER={gmail_user.strip()}",
        f"GMAIL_APP_PASSWORD={gmail_pw.strip()}",
        f"IMAP_SERVER={imap_server.strip()}",
        f"IMAP_PORT={imap_port}",
        f"IMAP_FOLDER={imap_folder.strip()}",
        "",
        "# Operational defaults",
        f"DEFAULT_EMAIL_LIMIT={limit.strip()}",
        f"CHECK_INTERVAL_SECONDS={interval.strip()}",
        f"ENABLE_VOICE={voice}",
        f"VOICE_RATE={rate.strip()}",
        "",
    ]
    try:
        ENV_PATH.write_text("\n".join(lines), encoding="utf-8")
        try:
            os.chmod(ENV_PATH, 0o600)
        except Exception:
            pass
    except KeyboardInterrupt:
        raise
    except Exception as e:
        console.print(f"[red]Failed to write .env: {e}[/red]")
        sys.exit(1)

    # ---- Summary ----
    summary = Table(show_header=False, border_style="cyan", expand=True)
    summary.add_column("k", style="bold yellow")
    summary.add_column("v")
    summary.add_row("Config file", str(ENV_PATH))
    summary.add_row("User", user_name)
    summary.add_row("Model", model.strip())
    summary.add_row("Gemini key", f"saved ({len(api_key.strip())} chars)")
    if choice == "1":
        summary.add_row("Email", f"Gmail OAuth ({creds_path})")
    elif choice == "12":
        summary.add_row("Email", f"Gmail OAuth ({creds_path}) + IMAP ({gmail_user.strip()})")
    elif choice == "2":
        summary.add_row("Email", f"IMAP ({gmail_user.strip()} @ {imap_server.strip()})")
    else:
        summary.add_row("Email", "mock-only (testing)")
    console.print()
    console.print(Panel(summary, title="[bold green]✔ Setup complete[/bold green]", border_style="green"))
    console.print("[dim]Validate anytime:[/dim] python setup.py --check")
    console.print("[dim]Test (fake mail, real key):[/dim] python main.py --mock -n 2")
    console.print("[dim]Real run:[/dim] python main.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled. No changes written (unless .env was already saved).[/yellow]")
        sys.exit(130)
