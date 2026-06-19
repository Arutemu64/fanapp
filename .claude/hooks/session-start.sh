#!/bin/bash
#
# SessionStart hook for Claude Code on the web.
#
# This runs at the start of EVERY web session (startup + resume). It only does
# the work that does NOT survive in the cached environment snapshot:
#   * the Docker daemon - a process; never survives between sessions
#   * the codegraph index - .codegraph/ is gitignored and the code is pulled
#     fresh each session, so the index must be (re)built/synced here
#   * per-session environment variables (PATH, testcontainers) written to
#     $CLAUDE_ENV_FILE
#
# The slow, filesystem-persistent installs (just, uv, Python 3.14, backend +
# frontend deps, the codegraph binary) live in .claude/setup.sh, which runs once
# at environment creation and is baked into the snapshot this hook starts from.
# Keep the two in sync: this hook assumes setup.sh already ran.
set -euo pipefail

# Only do remote setup in the Claude Code web environment. Local developers
# already have their own toolchains.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# Make the snapshot's upgraded uv (~/.local/bin) and the global codegraph binary
# ($PNPM_HOME) reachable for the steps below.
export PATH="$HOME/.local/bin:$HOME/.local/share/pnpm:$PATH"

# Run sudo correctly whether or not we are already root.
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# Start the Docker daemon so integration tests (testcontainers) can run. The
# daemon is not started by the base image and does not survive between sessions,
# so we (re)start it each time. Best-effort: warn and keep going rather than
# abort session setup (so `if` suppresses `set -e`).
echo "[session-start] Starting Docker daemon..."
if docker info >/dev/null 2>&1; then
  echo "[session-start] Docker daemon already running."
elif command -v dockerd >/dev/null 2>&1; then
  # dockerd is a long-running root process; launch it detached and poll the
  # socket (it usually comes up in ~1s). Logs go to a file for inspection.
  $SUDO sh -c 'dockerd >/tmp/dockerd.log 2>&1 &'
  for _ in $(seq 1 15); do
    if docker info >/dev/null 2>&1; then break; fi
    sleep 1
  done
  if docker info >/dev/null 2>&1; then
    echo "[session-start] Docker daemon ready."
  else
    echo "[session-start] WARN: Docker daemon did not start (see /tmp/dockerd.log); integration tests unavailable."
  fi
else
  echo "[session-start] WARN: dockerd not found; integration tests unavailable."
fi

# testcontainers' Ryuk reaper container is unreliable in this sandbox (it needs
# the docker socket and elevated privileges), so disable it for the session.
# Containers are still torn down by the fixtures' own finally: blocks.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export TESTCONTAINERS_RYUK_DISABLED=true' >> "$CLAUDE_ENV_FILE"
fi

# Build (or refresh) the codegraph index so symbol/call-graph queries are ready.
# The binary is installed by setup.sh; only the index lives here because the
# .codegraph/ db is gitignored and the code is pulled fresh each session. A
# present db means a resume - an incremental `sync` is enough; otherwise a full
# `init`. Best-effort: never abort session setup on failure.
if command -v codegraph >/dev/null 2>&1; then
  echo "[session-start] Building codegraph index..."
  if [ -f "$REPO_ROOT/.codegraph/codegraph.db" ]; then
    codegraph sync "$REPO_ROOT" || echo "[session-start] WARN: codegraph sync failed; skipping."
  else
    codegraph init "$REPO_ROOT" || echo "[session-start] WARN: codegraph init failed; skipping."
  fi
else
  echo "[session-start] WARN: codegraph not found (setup.sh may not have run); skipping index."
fi

# Persist PATH additions so the upgraded uv (~/.local/bin) and the codegraph
# binary ($PNPM_HOME) are used throughout the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export PATH="$HOME/.local/bin:$HOME/.local/share/pnpm:$PATH"' >> "$CLAUDE_ENV_FILE"
fi

echo "[session-start] Setup complete."
