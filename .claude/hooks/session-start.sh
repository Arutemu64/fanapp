#!/bin/bash
#
# SessionStart hook for Claude Code on the web.
#
# This runs at the start of EVERY web session (startup + resume). It does the
# work that must run each session rather than once at environment creation:
#   * project dependency syncs (uv sync / pnpm install) - the setup script only
#     re-runs on config change or cache expiry, so it would miss a dependency
#     bump on the branch; running the syncs here keeps deps in step with the
#     code. They are near-instant when the lockfile is unchanged.
#   * the Docker daemon - a process; never survives between sessions. Used to
#     boot a throwaway Postgres for Alembic autogenerate (not for testing).
#   * per-session environment variables (PATH) written to $CLAUDE_ENV_FILE
#
# The cloud-missing tooling (just, uv, Python 3.14) lives in .claude/setup.sh,
# which runs once at environment creation and is baked into the snapshot this
# hook starts from. Keep the two in sync: this hook assumes setup.sh already ran.
set -euo pipefail

# Only do remote setup in the Claude Code web environment. Local developers
# already have their own toolchains.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Fall back through git, then pwd, so a non-repo cwd can't abort the hook under
# `set -e` (CLAUDE_PROJECT_DIR is normally set by Claude Code).
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Make the snapshot's upgraded uv reachable for the steps below.
export PATH="$HOME/.local/bin:$PATH"

# Run sudo correctly whether or not we are already root.
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# Sync project dependencies against the current branch code. These are fast when
# the lockfile is unchanged (uv/pnpm short-circuit) and only fetch the delta
# after a real bump, since the caches persist in the snapshot. Kept here rather
# than in setup.sh so a dependency change is picked up without an env rebuild.
echo "[session-start] Syncing backend dependencies (uv sync)..."
(cd "$REPO_ROOT/backend" && uv sync --all-groups)

# Seed frontend/.env so `$env/static/public` types generate during the
# svelte-kit sync that pnpm's `prepare` runs below. Without it, every PUBLIC_*
# import is untyped and `pnpm check`/`pnpm lint` error in the cloud container,
# which has no .env. Placeholder values suffice: the typecheck only needs the
# keys to exist, not real secrets. frontend/.env is gitignored, so nothing leaks.
if [ ! -f "$REPO_ROOT/frontend/.env" ]; then
  echo "[session-start] Seeding frontend/.env from .env.example..."
  cp "$REPO_ROOT/frontend/.env.example" "$REPO_ROOT/frontend/.env"
fi

echo "[session-start] Syncing frontend dependencies (pnpm install)..."
(cd "$REPO_ROOT/frontend" && pnpm install)

# Start the Docker daemon so `just backend-generate-auto` can boot a throwaway
# Postgres to autogenerate Alembic migrations against. The daemon is not started
# by the base image and does not survive between sessions, so we (re)start it
# each time. (Integration tests and image builds are left to CI - see
# docs/claude-cloud.md.) Best-effort: warn and keep going rather than abort
# session setup (so `if` suppresses `set -e`).
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
  echo "[session-start] WARN: dockerd not found; Alembic autogenerate (just backend-generate-auto) unavailable."
fi

# Persist PATH additions so the upgraded uv (~/.local/bin) is used throughout
# the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$CLAUDE_ENV_FILE"
fi

echo "[session-start] Setup complete."
