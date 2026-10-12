#!/bin/bash
#
# Async SessionStart hook for Claude Code on the web: starts the Docker daemon
# and logs in to Docker Hub.
#
# Split from session-start.sh because nothing in the session needs Docker at
# startup (only `just backend-generate-auto`, the integration suite and the
# hadolint shim do), so it runs in the background instead of delaying the first
# response. Hooks in one matcher group run in parallel, which is also why this
# script touches nothing the sync hook produces (node_modules, .venv, .env).
#
# Registered with `asyncRewake`: exit 2 wakes Claude with stderr as a system
# reminder, so a daemon that never came up is reported instead of surfacing as a
# confusing `just backend-generate-auto` failure later. Every other outcome
# (including a failed or skipped login) exits 0 - pulls just stay anonymous.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Run sudo correctly whether or not we are already root.
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# The daemon is not started by the base image and does not survive between
# sessions, so it is (re)started each time.
if ! docker info >/dev/null 2>&1; then
  if ! command -v dockerd >/dev/null 2>&1; then
    echo "[session-start-docker] dockerd not found; Alembic autogenerate (just backend-generate-auto) and the hadolint shim are unavailable." >&2
    exit 2
  fi
  # dockerd is a long-running root process; launch it detached and poll the
  # socket (it usually comes up in ~1s). Logs go to a file for inspection.
  $SUDO sh -c 'dockerd >/tmp/dockerd.log 2>&1 &'
  for _ in $(seq 1 15); do
    if docker info >/dev/null 2>&1; then break; fi
    sleep 1
  done
  if ! docker info >/dev/null 2>&1; then
    echo "[session-start-docker] Docker daemon did not start (see /tmp/dockerd.log); Alembic autogenerate (just backend-generate-auto) and the hadolint shim are unavailable." >&2
    exit 2
  fi
fi

# Authenticate to Docker Hub so this session's pulls are not capped by the
# anonymous limit (~100 / 6h per egress IP), which a shared cloud egress hits
# quickly. This deliberately lives in a hook and NOT in setup.sh: the cloud
# environment's variables are injected only into the session, never into the
# setup-script phase, so DOCKERHUB_USER/DOCKERHUB_TOKEN read as empty there
# (anthropics/claude-code#63541). That also means the login cannot be baked into
# the snapshot - ~/.docker/config.json is written per session, after dockerd is
# up (docker login authenticates through the daemon). The token goes in on stdin,
# never on the command line.
if [ -n "${DOCKERHUB_USER:-}" ] && [ -n "${DOCKERHUB_TOKEN:-}" ]; then
  if ! printf '%s' "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin >/dev/null 2>&1; then
    echo "[session-start-docker] WARN: Docker Hub login failed; pulls are anonymous and rate-limited." >&2
  fi
fi
