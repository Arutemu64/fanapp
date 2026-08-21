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
# the way it runs .claude/hooks/session-start.sh. Repaste it after every change
# here, which also rebuilds the environment's cached snapshot.
#
# Every install here is best-effort. The setup script's exit status decides
# whether a session starts at all ("If the script exits non-zero, the session
# fails to start" - Claude Code on the web docs), and the result is cached, so
# one transient apt/PyPI/npm failure would otherwise break every future session
# in this environment. Failures are reported by the verification block at the
# bottom instead; the session comes up and the missing tool can be installed
# in-session.
#
# Steps that must run EVERY session (the Docker daemon process, the Docker Hub
# login, per-session env vars) live in .claude/hooks/session-start.sh instead,
# because processes and the per-session env file do not survive in the cached
# snapshot - and because the environment's variables are not injected into this
# script at all (see the prepull block below).
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
#           at /opt/node22/bin). We install the mise-pinned Node with nvm, which
#           the image already has at $NVM_DIR - the official nodejs.org/nvm-sh
#           installers both pull from GitHub (403). The exact version tracks the
#           mise pin via Renovate's "node" group (docs/dependencies.md).
#   * hadolint - Ships only as a GitHub release binary (403 here) and is not in
#           apt, so we install a shim that runs the pinned Docker image instead
#           (Docker Hub is on the allowlist). Keeps `just dockerfile-lint`,
#           `just ci` and the pre-commit hook working with the plain `hadolint`
#           command, exactly as they do on a laptop with mise.
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
    || { $SUDO apt-get update -qq && $SUDO apt-get install -y -qq just; } \
    || echo "[setup]   WARN: just install failed."
fi

echo "[setup] Installing pinned uv (for stable Python 3.14 support)..."
# Pinned to match mise.toml, backend/pyproject.toml [tool.uv], and
# backend/Dockerfile - bump all four together. An unpinned `--upgrade` would
# grab whatever is newest on PyPI, which drifts from the repo's pin and makes
# `uv sync`/`uv run` fail its own required-version check.
#
# The --user install works because the base image ships no PEP 668
# EXTERNALLY-MANAGED marker for its Python 3.11, despite being Ubuntu 24.04. If
# a future image restores that marker this call starts failing - hence the
# guard, and hence the verification block at the bottom that names `uv` as
# missing rather than letting the environment build silently broken.
python3 -m pip install --quiet --user "uv==0.12.3" \
  || echo "[setup]   WARN: uv install failed (PyPI unreachable, or pip refused the --user install)."

echo "[setup] Installing stable Python 3.14..."
uv python install 3.14 || echo "[setup]   WARN: Python 3.14 install failed; the backend's uv sync will try again per session."

# Pinned to match the other node sites (mise.toml, frontend/Dockerfile, CI
# setup-node); the renovate.json "node" group keeps them together via a
# customManager (docs/dependencies.md). One literal, referenced twice, so the
# install and the default alias cannot drift apart on a bump.
NODE_VERSION=24.19.0
echo "[setup] Installing Node.js $NODE_VERSION (nvm)..."
export NVM_DIR="/opt/nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  nvm install "$NODE_VERSION" && nvm alias default "$NODE_VERSION" \
    || echo "[setup]   WARN: Node $NODE_VERSION install failed; the image's system Node 22 stays in use."
  # `nvm alias default` only affects PATH once something calls `nvm use`; put
  # Node's bin dir first now so the rest of this script picks it up instead
  # of the base image's system Node 22 at /opt/node22/bin, which is earlier on
  # PATH by default (/etc/profile.d/nodejs.sh). session-start.sh resolves the
  # same "default" alias the same way each session.
  node_path="$(nvm which default 2>/dev/null || true)"
  if [ -n "$node_path" ]; then
    export PATH="$(dirname "$node_path"):$PATH"
  fi
else
  echo "[setup]   WARN: nvm not found at $NVM_DIR; skipping Node $NODE_VERSION."
fi

# Note: project dependency installs (uv sync / pnpm install) deliberately live
# in the SessionStart hook, not here. The setup script only re-runs when the
# environment config changes or the cache expires (~7 days), so it would not
# pick up a pyproject.toml / package.json bump on the branch. Running the syncs
# each session keeps deps in step with the code; they are near-instant when the
# lockfile is unchanged and only fetch the delta after a real bump (the uv/pnpm
# caches persist in the snapshot).

# Pinned to match the other pnpm sites (mise.toml, frontend/package.json
# "packageManager", frontend/Dockerfile); the renovate.json "pnpm" group keeps
# them together via a customManager (docs/dependencies.md). Without that manager
# this line is invisible to Renovate and drifts behind the other pnpm sites.
echo "[setup] Installing pnpm 11..."
npm install -g pnpm@11.22.0 || echo "[setup]   WARN: pnpm install failed."

# CodeGraph - the code-navigation knowledge graph (see AGENTS.md "Code
# Navigation"). Installed from the npm registry, NOT the project's recommended
# curl|sh installer: that pulls a bundled runtime from GitHub releases, which
# this environment blocks (the same reason just/uv/node above skip their GitHub
# installers). The tool is 100% local - bundled SQLite, no network at runtime -
# so it runs fine in the sandbox.
#
# Only the global binary is installed here (it persists in the snapshot); the
# index itself is NOT seeded here. A snapshot is reused across sessions on
# different branches/commits, so an index baked in at environment-creation time
# would reflect whatever ref happened to be checked out then, not the branch a
# later session actually runs on. The SessionStart hook builds/refreshes the
# index every session instead, against the code that session actually has.
#
# Best-effort: CodeGraph is a navigation convenience, so a failed install must
# not fail environment creation - it just leaves code navigation to grep/read.
echo "[setup] Installing CodeGraph (npm)..."
if npm install -g @colbymchenry/codegraph >/dev/null 2>&1; then
  # Expose codegraph on the base PATH via /usr/local/bin so the project's
  # .mcp.json server (bare `command: codegraph`) starts regardless of PATH:
  # Claude Code may spawn MCP servers with a PATH that predates the
  # SessionStart hook's nvm/Node-24 additions, and the npm global bin lives
  # under nvm's versioned dir (off the base PATH). /usr/local/bin is on the
  # base PATH and already has `node`, which the launcher shim needs. The target
  # is version-specific (nvm Node 24); setup.sh re-runs and refreshes it on a
  # Node bump. Best-effort: a failed link just falls back to CLI-only use.
  CG_BIN="$(command -v codegraph || true)"
  if [ -n "$CG_BIN" ]; then
    $SUDO ln -sf "$CG_BIN" /usr/local/bin/codegraph 2>/dev/null || true
  fi
  echo "[setup]   CodeGraph installed; the SessionStart hook builds the index."
else
  echo "[setup]   WARN: CodeGraph install failed; code navigation falls back to grep/read."
fi

# Prepull the Docker images the cloud flow needs. Image layers are files, so a
# pull here persists in the cached snapshot and every session starts with them
# on disk; only the daemon (a process) is restarted per session by the
# SessionStart hook. We start dockerd here purely to pull - it is not expected
# to survive the snapshot.
#
#   * postgres:18.4-alpine     - pinned to match production (docker-compose.yml)
#                                 exactly; used both to autogenerate Alembic
#                                 migrations (`just backend-generate-auto`) and
#                                 by the testcontainers integration suite (see
#                                 backend/tests/fixtures/db_provider.py).
#   * valkey/valkey:9.1-alpine - testcontainers image for `@pytest.mark.integration`
#     (both let `just backend-test` / `backend-test-integration` run in-session
#     instead of only in CI).
#   * hadolint/hadolint       - backs the `hadolint` shim installed below; pinned
#                                to match mise.toml and the .pre-commit-config.yaml
#                                rev (docs/dependencies.md).
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
    # These pulls are anonymous and cannot be otherwise: the cloud environment's
    # variables (DOCKERHUB_USER/DOCKERHUB_TOKEN) are injected only into the
    # session, never into this setup-script phase, so a `docker login` here would
    # always read empty credentials (anthropics/claude-code#63541). The login
    # lives in .claude/hooks/session-start.sh instead, which covers every pull a
    # session makes; only these three prepulls stay subject to the anonymous cap
    # (~100 / 6h per egress IP), and they degrade to a lazy pull at first use.
    for image in postgres:18.4-alpine valkey/valkey:9.1-alpine hadolint/hadolint:v2.15.1; do
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

# hadolint is the one gate in `just ci` that has no native install channel here:
# upstream ships GitHub release binaries (403 in this environment) and Ubuntu
# does not package it. Install a shim that runs the pinned image prepulled above,
# so `just dockerfile-lint`, `just ci` and the pre-commit `hadolint` hook all
# invoke a plain `hadolint` exactly as they do on a laptop, where mise supplies
# the real binary.
#
# The mount makes the container behave like the native binary: hadolint resolves
# relative Dockerfile arguments and discovers .hadolint.yaml from its working
# directory, so bind-mounting the caller's cwd at the same path (read-only) and
# matching the caller's uid/gid keeps both working unchanged.
#
# Keep the tag in sync with mise.toml and the .pre-commit-config.yaml rev
# (docs/dependencies.md); the renovate.json "hadolint" group covers this site
# via a customManager.
echo "[setup] Installing hadolint shim (Docker-backed)..."
if $SUDO tee /usr/local/bin/hadolint >/dev/null <<'HADOLINT_SHIM'
#!/bin/sh
exec docker run --rm -i \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:$PWD:ro" -w "$PWD" \
  hadolint/hadolint:v2.15.1 hadolint "$@"
HADOLINT_SHIM
then
  $SUDO chmod +x /usr/local/bin/hadolint || echo "[setup]   WARN: could not make the hadolint shim executable."
else
  echo "[setup]   WARN: could not write the hadolint shim; just dockerfile-lint will not run in-session."
fi

# Because every install above is best-effort, reaching this line does not mean
# the toolchain is there - so name anything missing. The environment still comes
# up; the gap is visible in the setup log and the tool can be installed
# in-session. CodeGraph is deliberately not checked (a navigation convenience
# that degrades to grep/read); hadolint is, because `just ci` gates on it.
MISSING_TOOLS=""
for tool in just uv node pnpm hadolint; do
  command -v "$tool" >/dev/null 2>&1 || MISSING_TOOLS="$MISSING_TOOLS $tool"
done

if [ -n "$MISSING_TOOLS" ]; then
  echo "[setup] WARN: setup finished, but these tools are missing:$MISSING_TOOLS"
else
  echo "[setup] Setup complete."
fi
