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
# Steps that must run EVERY session (the Docker daemon process, per-session env
# vars) live in .claude/hooks/session-start.sh instead, because processes and
# the per-session env file do not survive in the cached snapshot.
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
#   * node - The base web image ships Node 22 as the system Node (outside nvm,
#           at /opt/node22/bin). mise.toml now pins Node 24, so we install it
#           with nvm, which the image already has at $NVM_DIR - the official
#           nodejs.org/nvm-sh installers both pull from GitHub (403).
#   * npm  - Used as-is (bundled with Node 24) purely to install pnpm below.
#           Deliberately NOT self-upgraded: `npm install -g npm@latest` has a
#           known upstream bug where the live rebuild of its own module tree
#           loses `promise-retry` and aborts with MODULE_NOT_FOUND
#           (nodejs/node#62430, npm/cli#9151), and the bundled npm installs
#           pnpm fine on its own.
#
# Idempotent and safe to re-run: apt, pip, uv, nvm and pnpm all short-circuit
# when everything is already present.
set -euo pipefail

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

echo "[setup] Installing Node.js 24 (nvm)..."
export NVM_DIR="/opt/nvm"
# shellcheck disable=SC1091
. "$NVM_DIR/nvm.sh"
nvm install 24
nvm alias default 24
# `nvm alias default` only affects PATH once something calls `nvm use`; put
# Node 24's bin dir first now so the rest of this script picks it up instead
# of the base image's system Node 22 at /opt/node22/bin, which is earlier on
# PATH by default (/etc/profile.d/nodejs.sh). session-start.sh resolves the
# same "default" alias the same way each session.
export PATH="$(dirname "$(nvm which default)"):$PATH"

# Note: project dependency installs (uv sync / pnpm install) deliberately live
# in the SessionStart hook, not here. The setup script only re-runs when the
# environment config changes or the cache expires (~7 days), so it would not
# pick up a pyproject.toml / package.json bump on the branch. Running the syncs
# each session keeps deps in step with the code; they are near-instant when the
# lockfile is unchanged and only fetch the delta after a real bump (the uv/pnpm
# caches persist in the snapshot).

echo "[setup] Installing pnpm 11 (matches mise.toml / frontend/package.json)..."
npm install -g pnpm@11.11.0

# Prepull the Docker images the cloud flow needs. Image layers are files, so a
# pull here persists in the cached snapshot and every session starts with them
# on disk; only the daemon (a process) is restarted per session by the
# SessionStart hook. We start dockerd here purely to pull - it is not expected
# to survive the snapshot.
#
#   * postgres:18-alpine       - matches production (docker-compose.yml) and
#                                 the CI drift gate; used to autogenerate
#                                 Alembic migrations (`just backend-generate-auto`).
#   * postgres:18.4            - testcontainers image for `@pytest.mark.integration`
#   * valkey/valkey:9.1-alpine - testcontainers image for `@pytest.mark.integration`
#     (see backend/tests/fixtures/db_provider.py; both let `just backend-test` /
#     `backend-test-integration` run in-session instead of only in CI).
#
# Image builds (docker-publish.yml) and the rest of the compose stack (nats,
# db-backup) are still left to CI - not needed for either autogenerate or the
# test suite.
#
# Best-effort: a rate-limited or unreachable image must not fail environment
# creation, so the block runs under `if` (suppresses set -e) and a failed pull
# degrades to a lazy pull at first use. (In this env no image 403s; the
# allowlist already permits the Docker Hub blob CDN - see docs/claude-cloud.md.)
echo "[setup] Prepulling Docker images..."
if command -v dockerd >/dev/null 2>&1; then
  if ! docker info >/dev/null 2>&1; then
    $SUDO sh -c 'dockerd >/tmp/dockerd-setup.log 2>&1 &'
    for _ in $(seq 1 15); do
      if docker info >/dev/null 2>&1; then break; fi
      sleep 1
    done
  fi
  if docker info >/dev/null 2>&1; then
    # Authenticate to Docker Hub if credentials are provided as environment
    # variables (set in the cloud environment config). Anonymous pulls are
    # capped at ~100 / 6h per egress IP, which a shared cloud egress hits fast;
    # an authenticated account raises that substantially. The token is passed on
    # stdin (never on the command line), and the resulting ~/.docker/config.json
    # persists in the snapshot, so sessions' own lazy pulls are authenticated
    # too. Best-effort: a bad/expired token must not fail environment creation.
    if [ -n "${DOCKERHUB_USER:-}" ] && [ -n "${DOCKERHUB_TOKEN:-}" ]; then
      if printf '%s' "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin >/dev/null 2>&1; then
        echo "[setup] Authenticated to Docker Hub as $DOCKERHUB_USER."
      else
        echo "[setup] WARN: Docker Hub login failed; pulling anonymously (rate-limited)."
      fi
    else
      echo "[setup] Note: DOCKERHUB_USER/DOCKERHUB_TOKEN not set; pulling anonymously (rate-limited)."
    fi

    for image in postgres:18-alpine postgres:18.4 valkey/valkey:9.1-alpine; do
      if docker pull "$image" >/dev/null 2>&1; then
        echo "[setup]   pulled $image"
      else
        echo "[setup]   WARN: could not prepull $image (will lazy-pull at first use)"
      fi
    done
  else
    echo "[setup] WARN: dockerd did not start; skipping image prepull."
  fi
else
  echo "[setup] WARN: dockerd not found; skipping image prepull."
fi

# Set caveman default to lite mode (save tokens while keeping explanations readable).
mkdir -p "$HOME/.config/caveman"
echo '{"defaultMode": "lite"}' > "$HOME/.config/caveman/config.json"

# Record the hash of the repo's setup.sh so the SessionStart hook can detect
# drift: this script is pasted into the cloud environment UI by hand, and
# nothing else notices when the repo copy moves ahead of the snapshot. The
# repo is cloned before the setup script runs, but cwd is not guaranteed to
# be inside it, so fall through the same candidates the hook uses.
# Best-effort: skipping the hash only disables the drift warning.
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
if [ -f "$REPO_ROOT/.claude/setup.sh" ]; then
  mkdir -p "$HOME/.cache"
  sha256sum "$REPO_ROOT/.claude/setup.sh" | awk '{print $1}' > "$HOME/.cache/fanfan-setup.hash"
  echo "[setup] Recorded setup.sh hash for drift detection."
else
  echo "[setup] Note: repo setup.sh not found from cwd; drift detection disabled."
fi

echo "[setup] Setup complete."
