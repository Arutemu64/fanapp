#!/bin/bash
#
# SessionStart hook for Claude Code on the web.
#
# Prepares the container so the backend (Python 3.14 / FastAPI) and the OpenAPI
# codegen chain (`just frontend-generate-api`) work out of the box.
#
# Install-channel notes (this environment blocks GitHub release downloads):
#   * uv  - The base web image already ships uv in ~/.local/bin, but it is too
#           old to know about the stable Python 3.14 (its bundled list stops at
#           3.14.0rc2, which the backend's pydantic stack crashes on). It cannot
#           self-update: `uv self update` hits the GitHub API rate limit and the
#           standalone installer (astral.sh/uv/install.sh) is blocked (HTTP 403).
#           uv is not in the Ubuntu apt repos either, so we upgrade it in place
#           from PyPI - the one channel that works here.
#   * just - The repo drives every workflow through `just`, which is not
#           preinstalled. Its official installer also pulls from GitHub (403),
#           so we use the native Ubuntu package instead (`apt-get install just`).
#
# The hook is idempotent and safe to re-run: apt, pip, uv and pnpm all
# short-circuit when everything is already present (and the container caches
# this state after the first run).
set -euo pipefail

# Only do heavy setup in the Claude Code remote (web) environment. Local
# developers already have their own toolchains.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# The image's uv lives in ~/.local/bin; keep it (and any pip --user installs)
# reachable for the rest of this script.
export PATH="$HOME/.local/bin:$PATH"

# Run apt/sudo correctly whether or not we are already root.
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

echo "[session-start] Installing just (apt)..."
if ! command -v just >/dev/null 2>&1; then
  $SUDO apt-get install -y -qq just \
    || { $SUDO apt-get update -qq && $SUDO apt-get install -y -qq just; }
fi

echo "[session-start] Upgrading uv (for stable Python 3.14 support)..."
python3 -m pip install --quiet --upgrade --user uv

echo "[session-start] Installing stable Python 3.14..."
uv python install 3.14

echo "[session-start] Installing backend dependencies (uv sync)..."
(cd "$REPO_ROOT/backend" && uv sync --all-groups)

echo "[session-start] Installing frontend dependencies (pnpm install)..."
(cd "$REPO_ROOT/frontend" && pnpm install)

# Persist ~/.local/bin on PATH so the upgraded uv is used in the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$CLAUDE_ENV_FILE"
fi

echo "[session-start] Setup complete."
