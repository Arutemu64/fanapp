#!/bin/bash
#
# Environment setup script for Claude Code on the web.
#
# This runs ONCE when the environment is created; the resulting filesystem is
# baked into the cached snapshot every web session starts from. Put slow,
# filesystem-persistent installs here so they are NOT repeated each session.
#
# Register this file as the environment's Setup Script in the Claude Code web
# UI (Environments -> Setup script). It is tracked in git only so it can be
# reviewed and pasted/referenced; Claude Code does not auto-run it from the repo
# the way it runs .claude/hooks/session-start.sh.
#
# Steps that must run EVERY session (the Docker daemon process, the codegraph
# index refresh, per-session env vars) live in .claude/hooks/session-start.sh
# instead, because processes and the per-session env file do not survive in the
# cached snapshot.
#
# Install-channel notes (this environment blocks GitHub release downloads):
#   * uv  - The base web image ships uv in ~/.local/bin, but it is too old to
#           know about stable Python 3.14 (its list stops at 3.14.0rc2, which
#           the backend's pydantic stack crashes on). It cannot self-update
#           (GitHub API rate limit / astral.sh installer 403) and is not in apt,
#           so we upgrade it from PyPI - the one channel that works here.
#   * just - The repo drives every workflow through `just`, which is not
#           preinstalled. Its official installer pulls from GitHub (403), so we
#           use the native Ubuntu package (`apt-get install just`).
#   * codegraph - Code-intelligence CLI used to navigate this 550+ file codebase
#           with fewer tokens. Not a project dependency (it is an agent tool),
#           so we add it globally via pnpm. We install the binary here; the
#           per-session index build lives in the SessionStart hook because the
#           .codegraph/ db is gitignored and the code is pulled fresh each
#           session. Usage is documented in AGENTS.md.
#
# Idempotent and safe to re-run: apt, pip, uv and pnpm all short-circuit when
# everything is already present.
set -euo pipefail

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# The image's uv lives in ~/.local/bin; keep it (and pip --user installs)
# reachable for the rest of this script.
export PATH="$HOME/.local/bin:$PATH"

# Run apt/sudo correctly whether or not we are already root.
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

echo "[setup] Installing just (apt)..."
if ! command -v just >/dev/null 2>&1; then
  $SUDO apt-get install -y -qq just \
    || { $SUDO apt-get update -qq && $SUDO apt-get install -y -qq just; }
fi

echo "[setup] Upgrading uv (for stable Python 3.14 support)..."
python3 -m pip install --quiet --upgrade --user uv

echo "[setup] Installing stable Python 3.14..."
uv python install 3.14

echo "[setup] Installing backend dependencies (uv sync)..."
(cd "$REPO_ROOT/backend" && uv sync --all-groups)

echo "[setup] Installing frontend dependencies (pnpm install)..."
(cd "$REPO_ROOT/frontend" && pnpm install)

# codegraph is a global pnpm package. pnpm needs a global bin directory; point
# it at the standard PNPM_HOME. We track @latest so each rebuild gets upstream
# fixes for this fast-moving (pre-1.0) tool. Best-effort: a bad upstream release
# or transient network error must not fail environment creation.
echo "[setup] Installing codegraph (code-intelligence CLI)..."
export PNPM_HOME="$HOME/.local/share/pnpm"
export PATH="$PNPM_HOME:$PATH"
pnpm add -g @colbymchenry/codegraph@latest \
  || echo "[setup] WARN: codegraph install failed; continuing without it."

# Set caveman default to lite mode (save tokens while keeping explanations readable).
mkdir -p "$HOME/.config/caveman"
echo '{"defaultMode": "lite"}' > "$HOME/.config/caveman/config.json"

echo "[setup] Setup complete."
