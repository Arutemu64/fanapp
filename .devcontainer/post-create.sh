#!/usr/bin/env bash
#
# Dev Container provisioning for the FAN FAN monorepo (GitHub Codespaces).
#
# Runs once, after the container is created. It installs the pinned toolchain
# with mise (honouring mise.toml), syncs backend + frontend dependencies, and
# seeds .env / secrets via `just bootstrap` — leaving a Codespace ready for
# `just run-dev` (full Docker stack) or `just backend-dev` / `just frontend-dev`.
#
# Idempotent: mise, uv, pnpm and bootstrap all short-circuit when nothing
# changed, so re-running ("Rebuild Container") is safe.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# mise installs to ~/.local/bin and exposes tools through ~/.local/share/mise/shims.
# Put both on PATH for this non-interactive script before mise is activated.
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"

echo "[post-create] Installing mise..."
if ! command -v mise >/dev/null 2>&1; then
  curl -fsSL https://mise.run | sh
fi

# Install the exact runtimes pinned in mise.toml (Python, Node, pnpm, uv, just).
# `trust` is required because mise refuses to load an unauthorised config.
echo "[post-create] Installing toolchain (mise install)..."
mise trust
mise install
# Regenerate shims so the freshly installed tools resolve on PATH below.
mise reshim

# Activate mise in interactive shells so the terminal sees the same toolchain.
if ! grep -q 'mise activate bash' "$HOME/.bashrc" 2>/dev/null; then
  echo 'eval "$(mise activate bash)"' >> "$HOME/.bashrc"
fi

echo "[post-create] Syncing backend dependencies (uv sync)..."
(cd backend && uv sync --all-groups)

echo "[post-create] Syncing frontend dependencies (pnpm install)..."
(cd frontend && pnpm install)

# Seed frontend/.env for `just frontend-dev` ($env/static/public types + runtime
# PUBLIC_* reads). Placeholder values are fine; the file is gitignored.
if [ ! -f frontend/.env ]; then
  echo "[post-create] Seeding frontend/.env from template..."
  cp frontend/.env.example frontend/.env
fi

# Create root .env, generate DB/Redis/NATS/WEB secrets, and the VAPID keys.
# Idempotent — never clobbers values you have already set.
echo "[post-create] Bootstrapping .env and secrets (just bootstrap)..."
just bootstrap

cat <<'EOF'

[post-create] Done. Next steps:

  Full stack (Postgres + Redis + NATS + app, hot reload):
    just run-dev

  Or run the app processes natively (infra still via Docker):
    just backend-dev      # FastAPI on :8000
    just frontend-dev     # SvelteKit on :3000

  Real credentials still need filling in .env by hand (Telegram bot token,
  PUSH__SUBSCRIBER email) — see the bootstrap output above.
EOF
