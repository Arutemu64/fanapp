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
#   * codegraph - Code-intelligence CLI used to navigate this 550+ file codebase
#           with fewer tokens (symbol search, call graph, change-impact) instead
#           of reading whole files. Not preinstalled and not a project dependency
#           (it is an agent tool, not frontend/backend runtime code), so we add it
#           globally via pnpm and build its index. We use the CLI rather than the
#           MCP server on purpose: the CLI costs zero context until invoked, while
#           an always-on MCP server would add tool definitions to every session.
#           Usage is documented in AGENTS.md. The index lives in .codegraph/ and
#           is kept out of git by .codegraph/.gitignore.
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

# codegraph is a global pnpm package. pnpm needs a global bin directory; point
# it at the standard PNPM_HOME and add that to PATH so the `codegraph` binary is
# reachable here and for the rest of the session. Pinned for reproducible
# sessions; bump this version deliberately when you want a newer codegraph.
echo "[session-start] Installing codegraph (code-intelligence CLI)..."
export PNPM_HOME="$HOME/.local/share/pnpm"
export PATH="$PNPM_HOME:$PATH"
pnpm add -g @colbymchenry/codegraph@0.9.9

# Build (or refresh) the code index so symbol/call-graph queries are ready. The
# .codegraph/ database is gitignored, so a fresh container has no db and needs a
# full `init`; if a db is already present (re-run/resume) an incremental `sync`
# is enough.
echo "[session-start] Building codegraph index..."
if [ -f "$REPO_ROOT/.codegraph/codegraph.db" ]; then
  codegraph sync "$REPO_ROOT"
else
  codegraph init "$REPO_ROOT"
fi

# Persist PATH additions so the upgraded uv (~/.local/bin) and the codegraph
# binary ($PNPM_HOME) are used throughout the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export PATH="$HOME/.local/bin:$HOME/.local/share/pnpm:$PATH"' >> "$CLAUDE_ENV_FILE"
fi

echo "[session-start] Setup complete."
