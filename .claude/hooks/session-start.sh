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
# The cloud-missing tooling (just, uv, Python 3.14, Node 24 via nvm) lives in
# .claude/setup.sh, which runs once at environment creation and is baked into
# the snapshot this hook starts from. Keep the two in sync: this hook assumes
# setup.sh already ran.
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

# Activate the Node 24 setup.sh installed via nvm, so the `pnpm install` below
# (and anything else this session runs) uses it instead of the base image's
# system Node 22 at /opt/node22/bin, which is otherwise earlier on PATH
# (/etc/profile.d/nodejs.sh). nvm.sh alone doesn't switch PATH - only `nvm use`
# does - so resolve and prepend Node 24's bin dir explicitly.
export NVM_DIR="/opt/nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  export PATH="$(dirname "$(nvm which default)"):$PATH"
fi

# Run sudo correctly whether or not we are already root.
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# Drift check: setup.sh is pasted into the cloud environment UI by hand, so the
# branch's copy can silently move ahead of what this environment's snapshot was
# built from. setup.sh records its own hash at environment creation; compare it
# against the repo copy and nag until the UI copy is refreshed. A missing hash
# file also means the snapshot predates the recording step - same remedy.
SETUP_HASH_FILE="$HOME/.cache/fanfan-setup.hash"
if [ -f "$REPO_ROOT/.claude/setup.sh" ]; then
  if [ ! -f "$SETUP_HASH_FILE" ] || [ "$(sha256sum "$REPO_ROOT/.claude/setup.sh" | awk '{print $1}')" != "$(cat "$SETUP_HASH_FILE")" ]; then
    echo "[session-start] WARN: .claude/setup.sh differs from what this environment ran at creation - refresh the Setup script field in the cloud environment UI to rebuild the snapshot (see docs/claude-cloud.md)."
  fi
fi

# Sync project dependencies against the current branch code. These are fast when
# the lockfile is unchanged (uv/pnpm short-circuit) and only fetch the delta
# after a real bump, since the caches persist in the snapshot. Kept here rather
# than in setup.sh so a dependency change is picked up without an env rebuild.
echo "[session-start] Syncing backend dependencies (uv sync)..."
(cd "$REPO_ROOT/backend" && uv sync --all-groups)

# Seed the root .env so `$env/static/public` types generate during the
# svelte-kit sync that pnpm's `prepare` runs below (the frontend reads env from
# the repo root — see frontend/svelte.config.js). Without it, every PUBLIC_*
# import is untyped and `pnpm check`/`pnpm lint` error in the cloud container,
# which has no .env. Placeholder values suffice: the typecheck only needs the
# keys to exist, not real secrets. .env is gitignored, so nothing leaks.
if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "[session-start] Seeding .env from .env.example..."
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
fi

echo "[session-start] Syncing frontend dependencies (pnpm install)..."
(cd "$REPO_ROOT/frontend" && pnpm install)

# Refresh the CodeGraph index so code-navigation queries (AGENTS.md "Code
# Navigation") reflect the current branch. The binary is installed by setup.sh
# and persists in the snapshot; the index (.codegraph/, gitignored) is
# per-branch project state that must track the code - like node_modules above -
# so it is (re)built here, not baked into the snapshot. `sync` updates the
# seeded index incrementally (near-instant when unchanged); a session whose
# snapshot predates the seed has no index yet, so fall back to a full `init`.
# Best-effort: navigation is a convenience, so a failure must not abort session
# setup (the `if`/`||` keep set -e from tripping).
if command -v codegraph >/dev/null 2>&1; then
  if [ -f "$REPO_ROOT/.codegraph/codegraph.db" ]; then
    echo "[session-start] Syncing CodeGraph index..."
    (cd "$REPO_ROOT" && codegraph sync >/dev/null 2>&1) \
      || echo "[session-start] WARN: codegraph sync failed; run 'codegraph index' to rebuild."
  else
    echo "[session-start] Building CodeGraph index (first run)..."
    (cd "$REPO_ROOT" && codegraph init >/dev/null 2>&1) \
      || echo "[session-start] WARN: codegraph init failed; code navigation falls back to grep/read."
  fi
else
  echo "[session-start] Note: codegraph not installed; skipping index (grep/read still available)."
fi

# Start the Docker daemon: `just backend-generate-auto` boots a throwaway
# Postgres against it to autogenerate Alembic migrations, and
# `@pytest.mark.integration` tests boot Postgres + Valkey via testcontainers
# (see docs/testing.md). The daemon is not started by the base image and does
# not survive between sessions, so we (re)start it each time. (Image builds
# are still left to docker-publish.yml - see docs/claude-cloud.md.)
# Best-effort: warn and keep going rather than abort session setup (so `if`
# suppresses `set -e`).
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
    echo "[session-start] WARN: Docker daemon did not start (see /tmp/dockerd.log); Alembic autogenerate (just backend-generate-auto) unavailable."
  fi
else
  echo "[session-start] WARN: dockerd not found; Alembic autogenerate (just backend-generate-auto) unavailable."
fi

# Persist PATH additions so the upgraded uv (~/.local/bin) and nvm's Node 24
# are used throughout the session, not just in this hook's own shell. Also
# disable the testcontainers Ryuk reaper, matching CI (.github/workflows/ci.yml):
# the integration test fixtures already stop their own containers in `finally`
# blocks (backend/tests/fixtures/db_provider.py), and dockerd itself is
# restarted fresh every session, so Ryuk's crash-cleanup role isn't needed here
# - skipping it avoids pulling/running an extra container per test session. The
# hook re-runs on resume against the same env file, so guard with a marker line
# to avoid stacking duplicate entries.
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

echo "[session-start] Setup complete."
