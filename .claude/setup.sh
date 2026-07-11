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
#   * npm  - Self-upgrading npm via itself (`npm install -g npm@latest`) is
#           best-effort: Node 22.22.2's bundled npm 10.9.7 has a known upstream
#           bug where the live rebuild of its own module tree loses
#           `promise-retry`, aborting with MODULE_NOT_FOUND before it ever
#           reaches the pnpm install below (nodejs/node#62430, npm/cli#9151).
#           The bundled npm installs pnpm fine on its own, so a failed
#           self-upgrade must not fail environment creation.
#
# Idempotent and safe to re-run: apt, pip, uv and pnpm all short-circuit when
# everything is already present.
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

echo "[setup] Upgrading npm to latest..."
npm install -g npm@latest \
  || echo "[setup] WARN: npm self-upgrade failed (see install-channel notes above); continuing with bundled npm $(npm --version)."

# Note: project dependency installs (uv sync / pnpm install) deliberately live
# in the SessionStart hook, not here. The setup script only re-runs when the
# environment config changes or the cache expires (~7 days), so it would not
# pick up a pyproject.toml / package.json bump on the branch. Running the syncs
# each session keeps deps in step with the code; they are near-instant when the
# lockfile is unchanged and only fetch the delta after a real bump (the uv/pnpm
# caches persist in the snapshot).

echo "[setup] Upgrading pnpm to latest..."
npm install -g pnpm@latest

# Prepull the single Docker image the cloud flow needs: a Postgres matching
# production (postgres:18-alpine), used to autogenerate Alembic migrations
# against a throwaway database (see `just backend-generate-auto`). Image layers
# are files, so a pull here persists in the cached snapshot and every session
# starts with it on disk; only the daemon (a process) is restarted per session
# by the SessionStart hook. We start dockerd here purely to pull - it is not
# expected to survive the snapshot.
#
# Integration-test and image-build deps are deliberately NOT prepulled: the
# cloud agent flow relies on CI (.github/workflows/ci.yml) to run the full test
# suite and docker-publish.yml to build images. Local fast checks (ruff, ty)
# need no containers and still run per AGENTS.md.
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

    # Single image: production-matching Postgres for Alembic autogenerate.
    if docker pull postgres:18-alpine >/dev/null 2>&1; then
      echo "[setup]   pulled postgres:18-alpine"
    else
      echo "[setup]   WARN: could not prepull postgres:18-alpine (will lazy-pull at first use)"
    fi
  else
    echo "[setup] WARN: dockerd did not start; skipping image prepull."
  fi
else
  echo "[setup] WARN: dockerd not found; skipping image prepull."
fi

# Set caveman default to lite mode (save tokens while keeping explanations readable).
mkdir -p "$HOME/.config/caveman"
echo '{"defaultMode": "lite"}' > "$HOME/.config/caveman/config.json"

echo "[setup] Setup complete."
