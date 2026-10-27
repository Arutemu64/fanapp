#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

export PATH="$HOME/.local/bin:$PATH"

export NVM_DIR="/opt/nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  export PATH="$(dirname "$(nvm which default)"):$PATH"
fi

ENV_MARKER="# fanfan session-start PATH"
if [ -n "${CLAUDE_ENV_FILE:-}" ] && ! grep -qsF "$ENV_MARKER" "$CLAUDE_ENV_FILE"; then
  {
    echo "$ENV_MARKER"
    echo 'export PATH="$HOME/.local/bin:$PATH"'
    echo 'export NVM_DIR="/opt/nvm"'
    echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && export PATH="$(dirname "$(nvm which default)"):$PATH"'
    echo 'export TESTCONTAINERS_RYUK_DISABLED="true"'
  } >> "$CLAUDE_ENV_FILE"
fi

if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "[session-start] Seeding .env from .env.example..."
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
else
  missing_env=$(awk -F= '
    FNR==NR { if ($0 ~ /^[A-Za-z_][A-Za-z0-9_]*=/) seen[$1]=1; next }
    /^[A-Za-z_][A-Za-z0-9_]*=/ && !($1 in seen)
  ' "$REPO_ROOT/.env" "$REPO_ROOT/.env.example")
  if [ -n "$missing_env" ]; then
    echo "[session-start] Backfilling .env with keys added to .env.example..."
    {
      echo ""
      echo "# Backfilled by session-start: declared in .env.example, absent here."
      printf '%s\n' "$missing_env"
    } >> "$REPO_ROOT/.env"
  fi
fi

SYNC_LOG="$(mktemp -t session-start-sync.XXXXXX)"
trap 'rm -f "$SYNC_LOG"' EXIT

echo "[session-start] Syncing backend dependencies (uv sync)..."
if ! (cd "$REPO_ROOT/backend" && uv sync --all-groups) >"$SYNC_LOG" 2>&1; then
  tail -n 20 "$SYNC_LOG"
  echo "[session-start] WARN: backend uv sync failed; run 'just backend-install' before backend work."
fi

echo "[session-start] Syncing frontend dependencies (pnpm install)..."
if ! (cd "$REPO_ROOT/frontend" && pnpm install) >"$SYNC_LOG" 2>&1; then
  tail -n 20 "$SYNC_LOG"
  exit 1
fi

echo "[session-start] Installing Playwright's Chromium for the pinned version..."
(cd "$REPO_ROOT/frontend" && pnpm exec playwright install --only-shell --no-progress chromium >/dev/null) \
  || echo "[session-start] WARN: Playwright Chromium install failed; run 'pnpm --dir frontend exec playwright install --only-shell chromium' before E2E work."

if command -v codegraph >/dev/null 2>&1; then
  if [ -f "$REPO_ROOT/.codegraph/codegraph.db" ]; then
    echo "[session-start] Syncing CodeGraph index..."
    (cd "$REPO_ROOT" && codegraph sync >/dev/null 2>&1) \
      || echo "[session-start] WARN: codegraph sync failed; run 'codegraph index' to rebuild."
  else
    echo "[session-start] Building CodeGraph index..."
    (cd "$REPO_ROOT" && codegraph init >/dev/null 2>&1) \
      || echo "[session-start] WARN: codegraph init failed; code navigation falls back to grep/read."
  fi
else
  echo "[session-start] Note: codegraph not installed; skipping index (grep/read still available)."
fi

echo "[session-start] Setup complete."
