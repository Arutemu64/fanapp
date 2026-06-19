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

# Note: project dependency installs (uv sync / pnpm install) deliberately live
# in the SessionStart hook, not here. The setup script only re-runs when the
# environment config changes or the cache expires (~7 days), so it would not
# pick up a pyproject.toml / package.json bump on the branch. Running the syncs
# each session keeps deps in step with the code; they are near-instant when the
# lockfile is unchanged and only fetch the delta after a real bump (the uv/pnpm
# caches persist in the snapshot).

# codegraph is a global pnpm package. pnpm needs a global bin directory; point
# it at the standard PNPM_HOME. We track @latest so each rebuild gets upstream
# fixes for this fast-moving (pre-1.0) tool. Best-effort: a bad upstream release
# or transient network error must not fail environment creation.
echo "[setup] Installing codegraph (code-intelligence CLI)..."
export PNPM_HOME="$HOME/.local/share/pnpm"
export PATH="$PNPM_HOME:$PATH"
pnpm add -g @colbymchenry/codegraph@latest \
  || echo "[setup] WARN: codegraph install failed; continuing without it."

# Prepull the external Docker images the project uses. Image layers are files,
# so a pull here persists in the cached snapshot and every session starts with
# them on disk; only the daemon (a process) is restarted per session by the
# SessionStart hook. We start dockerd here purely to pull - it is not expected
# to survive the snapshot.
#
# Best-effort: a rate-limited or unreachable image must not fail environment
# creation, so the block runs under `if` (suppresses set -e) and each failed
# pull degrades to a lazy pull at first use. Docker Hub caps anonymous pulls
# (~100 / 6h per egress IP), so the integration-test images are listed first -
# the test path stays cached even if a later pull hits the cap. (In this env no
# image 403s; the allowlist already permits the Docker Hub / GHCR blob CDNs -
# see docs/testing.md. The project's own ghcr.io/arutemu64/fanapp-* images and
# the locally built fanapp-* compose images are intentionally not prepulled.)
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
    # Format: "<image>  # comment". `read img _` keeps the image, drops the rest.
    PREPULL_IMAGES="
      postgres:18.2                                    # testcontainers (integration tests)
      redis:6.2.13-alpine                              # testcontainers (integration tests)
      postgres:18-alpine                               # docker-compose: db
      nats:2.14-alpine                                 # docker-compose: nats
      valkey/valkey:9.1-alpine                         # docker-compose: redis/valkey
      prodrigestivill/postgres-backup-local:18-alpine  # docker-compose: db backup
      ghcr.io/astral-sh/uv:0.11.19-trixie-slim         # backend Dockerfile: builder
      debian:trixie-slim                               # backend Dockerfile: runtime
      node:22.22-alpine                                # frontend Dockerfile: base
      nginx:1.27-alpine                                # frontend Dockerfile: prod
    "
    echo "$PREPULL_IMAGES" | while read -r img _; do
      [ -z "$img" ] && continue
      if docker pull "$img" >/dev/null 2>&1; then
        echo "[setup]   pulled $img"
      else
        echo "[setup]   WARN: could not prepull $img (will lazy-pull at first use)"
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

echo "[setup] Setup complete."
