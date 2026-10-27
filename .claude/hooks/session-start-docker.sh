#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

if ! docker info >/dev/null 2>&1; then
  if ! command -v dockerd >/dev/null 2>&1; then
    echo "[session-start-docker] dockerd not found; Alembic autogenerate (just backend-generate-auto) and the hadolint shim are unavailable." >&2
    exit 2
  fi
  for attempt in 1 2; do
    $SUDO sh -c 'dockerd >/tmp/dockerd.log 2>&1 &'
    for _ in $(seq 1 15); do
      if docker info >/dev/null 2>&1; then break; fi
      sleep 1
    done
    if docker info >/dev/null 2>&1; then break; fi
    if [ "$attempt" -eq 1 ]; then sleep 3; fi
  done
  if ! docker info >/dev/null 2>&1; then
    echo "[session-start-docker] Docker daemon did not start (see /tmp/dockerd.log); Alembic autogenerate (just backend-generate-auto) and the hadolint shim are unavailable." >&2
    exit 2
  fi
fi

if [ -n "${DOCKERHUB_USER:-}" ] && [ -n "${DOCKERHUB_TOKEN:-}" ]; then
  if ! printf '%s' "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin >/dev/null 2>&1; then
    echo "[session-start-docker] WARN: Docker Hub login failed; pulls are anonymous and rate-limited." >&2
  fi
fi
