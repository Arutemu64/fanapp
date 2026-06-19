#!/usr/bin/env bash
#
# One-command local setup: create .env from the template, fill every generated
# secret (DB / Redis / NATS passwords, WEB__SECRET_KEY), and generate the Web
# Push VAPID keys (config/*.pem + PUBLIC_VAPID_KEY). Driven by `just bootstrap`.
#
# Idempotent: re-running never clobbers an existing .env value or existing VAPID
# keys — it only fills placeholders that are still untouched. Real third-party
# credentials (Telegram bot token, SMTP) stay manual and are listed at the end.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE=".env"

# --- 1. Create .env from the template (never clobber an existing one) --------
if [[ -f "$ENV_FILE" ]]; then
  echo "✓ $ENV_FILE exists — keeping it"
else
  cp .env.example "$ENV_FILE"
  echo "✓ created $ENV_FILE from .env.example"
fi

# Replace KEY=<placeholder> with KEY=<value>, but only while the line still
# holds the exact placeholder. Keeps the script idempotent — a real secret is
# never overwritten on a re-run.
set_if_placeholder() {
  local key="$1" placeholder="$2" value="$3"
  if grep -qxF "${key}=${placeholder}" "$ENV_FILE"; then
    awk -v old="${key}=${placeholder}" -v new="${key}=${value}" \
      '$0 == old { print new; next } { print }' "$ENV_FILE" > "$ENV_FILE.tmp"
    mv "$ENV_FILE.tmp" "$ENV_FILE"
    echo "✓ generated ${key}"
  else
    echo "• ${key} already set — skipping"
  fi
}

# --- 2. Generate secrets -----------------------------------------------------
if ! command -v openssl >/dev/null 2>&1; then
  echo "error: openssl is required to generate secrets" >&2
  exit 1
fi

gen_secret() { openssl rand -hex 32; }

set_if_placeholder DB__PASSWORD    "change-me-db-password"     "$(gen_secret)"
set_if_placeholder REDIS__PASSWORD "change-me-redis-password"  "$(gen_secret)"
set_if_placeholder NATS__PASSWORD  "change-me-nats-password"   "$(gen_secret)"
set_if_placeholder WEB__SECRET_KEY "change-me-long-random-string" "$(gen_secret)"

# --- 3. VAPID keys for Web Push ----------------------------------------------
mkdir -p config
if [[ -f config/private_key.pem && -f config/public_key.pem ]]; then
  echo "• VAPID keys exist — skipping"
else
  # vapid-gen writes private_key.pem/public_key.pem into the current directory
  # and prints application_server_key='<base64url>'. Run it in a temp dir, then
  # move the keys into config/. vapid-gen lives in the backend's uv environment.
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  vapid_out="$(cd "$tmp_dir" && uv run --project "$ROOT/backend" vapid-gen 2>&1)"
  mv "$tmp_dir/private_key.pem" config/private_key.pem
  mv "$tmp_dir/public_key.pem" config/public_key.pem
  chmod 600 config/private_key.pem
  echo "✓ generated VAPID keys in config/"

  app_key="$(echo "$vapid_out" | sed -n "s/^application_server_key='\(.*\)'$/\1/p")"
  if [[ -n "$app_key" ]]; then
    set_if_placeholder PUBLIC_VAPID_KEY "" "$app_key"
  else
    echo "! could not parse application_server_key — set PUBLIC_VAPID_KEY by hand" >&2
  fi
fi

# --- 4. Remaining manual steps ----------------------------------------------
cat <<'EOF'

Bootstrap complete. Still set by hand in .env (real credentials, can't generate):
  • BOT__TOKEN / BOT__CLIENT_ID / BOT__CLIENT_SECRET — create a bot via @BotFather
  • MAIL__*       — SMTP credentials (defaults point at Mailtrap sandbox)
  • PUSH__SUBSCRIBER — your contact email for Web Push

Then start the full environment:
  just run-dev
EOF
