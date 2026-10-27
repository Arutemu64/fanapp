#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

echo "[setup] Installing just (apt)..."
if ! command -v just >/dev/null 2>&1; then
  $SUDO apt-get install -y -qq just \
    || { $SUDO apt-get update -qq && $SUDO apt-get install -y -qq just; } \
    || echo "[setup]   WARN: just install failed."
fi

echo "[setup] Installing pinned uv (for stable Python 3.14 support)..."
python3 -m pip install --quiet --user "uv==0.13.0" \
  || echo "[setup]   WARN: uv install failed (PyPI unreachable, or pip refused the --user install)."

echo "[setup] Installing stable Python 3.14..."
uv python install 3.14 || echo "[setup]   WARN: Python 3.14 install failed; the backend's uv sync will try again per session."

NODE_VERSION=24.21.0
echo "[setup] Installing Node.js $NODE_VERSION (nvm)..."
export NVM_DIR="/opt/nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  nvm install "$NODE_VERSION" && nvm alias default "$NODE_VERSION" \
    || echo "[setup]   WARN: Node $NODE_VERSION install failed; the image's system Node 22 stays in use."
  node_path="$(nvm which default 2>/dev/null || true)"
  if [ -n "$node_path" ]; then
    export PATH="$(dirname "$node_path"):$PATH"
  fi
else
  echo "[setup]   WARN: nvm not found at $NVM_DIR; skipping Node $NODE_VERSION."
fi

echo "[setup] Installing pnpm 11..."
npm install -g pnpm@12.10.1 || echo "[setup]   WARN: pnpm install failed."

CODEGRAPH_VERSION=1.6.2
echo "[setup] Installing CodeGraph $CODEGRAPH_VERSION (npm)..."
if npm install -g "@colbymchenry/codegraph@$CODEGRAPH_VERSION" >/dev/null 2>&1; then
  CG_BIN="$(command -v codegraph || true)"
  if [ -n "$CG_BIN" ]; then
    $SUDO ln -sf "$CG_BIN" /usr/local/bin/codegraph 2>/dev/null || true
  fi
  echo "[setup]   CodeGraph installed; the SessionStart hook builds the index."
else
  echo "[setup]   WARN: CodeGraph install failed; code navigation falls back to grep/read."
fi

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
    for image in postgres:18.6-alpine valkey/valkey:9.1-alpine hadolint/hadolint:v2.15.1; do
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

MISSING_TOOLS=""
for tool in just uv node pnpm hadolint; do
  command -v "$tool" >/dev/null 2>&1 || MISSING_TOOLS="$MISSING_TOOLS $tool"
done

if [ -n "$MISSING_TOOLS" ]; then
  echo "[setup] WARN: setup finished, but these tools are missing:$MISSING_TOOLS"
else
  echo "[setup] Setup complete."
fi
