#!/usr/bin/env bash
# JARVIS installer — compatible with both bash and zsh.
# Usage:
#   ./install.sh                  # full install + interactive TUI setup
#   bash install.sh               # same (bash)
#   zsh install.sh                # same (zsh)
#   ./install.sh --skip-setup     # install deps only, no setup wizard
#   ./install.sh --check          # install deps + validate config (no prompts)
#   ./install.sh --reinstall      # wipe .venv and reinstall
#   ./install.sh --help           # this help
#
# What it does:
#   1. Checks python3 >= 3.10
#   2. Creates .venv, installs requirements.txt
#   3. Runs the TUI setup wizard (setup.py) to collect API/mail inputs -> .env
#   4. Creates a ./jarvis launcher (activates venv, runs main.py)

set -eu
# pipefail where supported (bash + modern zsh); ignore error otherwise
set -o pipefail 2>/dev/null || true

SKIP_SETUP=0
CHECK_ONLY=0
REINSTALL=0

for arg in "$@"; do
  case "$arg" in
    --skip-setup) SKIP_SETUP=1 ;;
    --check) CHECK_ONLY=1 ;;
    --reinstall) REINSTALL=1 ;;
    --help|-h)
      echo "Usage: ./install.sh [--skip-setup] [--check] [--reinstall]"
      echo "  Works with: bash install.sh | zsh install.sh | ./install.sh"
      exit 0
      ;;
    *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

# Always operate from the script's directory (the project root)
if [ -n "${ZSH_VERSION:-}" ]; then
  # zsh: %x = script path
  SCRIPT_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
else
  # bash/sh: $0 = script path
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
cd "$SCRIPT_DIR"

say() { printf '%s\n' "$*"; }
die() { printf '✖ %s\n' "$*" >&2; exit 1; }
ok()  { printf '✔ %s\n' "$*"; }

say "⚡ JARVIS installer — project: $SCRIPT_DIR"
say "   Shell: ${ZSH_VERSION:+zsh }${BASH_VERSION:+bash }(${0:-unknown})"

# ---- 1. Python check ----
if ! command -v python3 >/dev/null 2>&1; then
  die "python3 not found. Install Python 3.10+ then re-run ./install.sh"
fi
PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
say "● Found python3 ($PY_VER)"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  die "Python 3.10+ required (found $PY_VER)"
fi

# ---- 2. Virtualenv ----
if [ "$REINSTALL" = 1 ] && [ -d ".venv" ]; then
  say "● Removing existing .venv (--reinstall)…"
  rm -rf ".venv"
fi
if [ ! -d ".venv" ]; then
  say "● Creating virtual environment (.venv)…"
  python3 -m venv .venv || die "Failed to create .venv"
else
  say "● Reusing existing .venv"
fi
if [ ! -x ".venv/bin/python" ]; then
  die ".venv/bin/python missing — delete .venv and re-run"
fi
say "● Upgrading pip…"
".venv/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || say "  (pip upgrade warning — continuing)"

say "● Installing requirements…"
".venv/bin/python" -m pip install -r requirements.txt || die "pip install failed"
ok "Dependencies installed"

# ---- 3. Setup wizard (TUI collects API + mail inputs -> .env) ----
if [ "$SKIP_SETUP" = 1 ]; then
  say "● Skipping setup wizard (--skip-setup). Run later: ./.venv/bin/python setup.py"
elif [ "$CHECK_ONLY" = 1 ]; then
  say "● Validating existing config (setup.py --check)…"
  ".venv/bin/python" setup.py --check || die "Config check failed — run ./.venv/bin/python setup.py"
else
  if [ ! -t 0 ]; then
    say "⚠ No interactive terminal detected — skipping wizard."
    say "  Run later: ./.venv/bin/python setup.py"
  else
    say "● Launching TUI setup wizard (API keys + mail credentials → .env)…"
    ".venv/bin/python" setup.py || die "Setup wizard failed"
  fi
fi

# ---- 4. Launcher ----
cat > "$SCRIPT_DIR/jarvis" <<'LAUNCHER'
#!/usr/bin/env sh
# JARVIS launcher — activates .venv and runs main.py (works in bash/zsh/sh)
set -eu
D="$(cd "$(dirname "$0")" && pwd)"
exec "$D/.venv/bin/python" "$D/main.py" "$@"
LAUNCHER
chmod +x "$SCRIPT_DIR/jarvis"
ok "Launcher created: ./jarvis"

say ""
ok "Install complete."
say "  Validate config : ./.venv/bin/python setup.py --check"
say "  Test (fake mail): ./jarvis --mock -n 2        (needs real GEMINI_API_KEY)"
say "  Real run        : ./jarvis"
say "  Reconfigure     : ./.venv/bin/python setup.py"
say ""
say "Notes:"
say "  • No placeholder output: without creds/API key the app errors clearly instead of faking a briefing."
say "  • Mock mode is explicit only (--mock). Auto mode never uses fake emails."
say "  • Secrets live in .env (chmod 600, git-ignored)."
