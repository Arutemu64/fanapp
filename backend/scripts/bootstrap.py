#!/usr/bin/env python3
#
# One-command local setup: create .env from the template, fill every generated
# secret (DB / Redis / NATS passwords, WEB__SECRET_KEY), and generate the Web
# Push VAPID keys (secrets/*.pem + PUBLIC_VAPID_KEY). Driven by `just bootstrap`.
#
# Idempotent: re-running never clobbers an existing .env value or existing VAPID
# keys — it only fills placeholders that are still untouched. Real third-party
# credentials (Telegram bot token, SMTP) stay manual and are listed at the end.
#
# Pure Python (stdlib + the backend's webpush dep) so setup runs the same on
# Linux, macOS and Windows — no bash/openssl/awk/sed required. Run it through the
# backend venv (`just bootstrap`, i.e. `cd backend && uv run python
# scripts/bootstrap.py`) so the `fanfan` import below resolves.
import secrets
import shutil
from pathlib import Path

from fanfan.main.generate_vapid import (
    PRIVATE_KEY_NAME,
    PUBLIC_KEY_NAME,
    write_vapid_keys,
)

# This file lives at backend/scripts/bootstrap.py; the repo root (home of .env
# and secrets/) is three levels up.
ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
SECRETS_DIR = ROOT / "secrets"

# Keys bootstrap auto-fills with a generated secret, mapped to the exact
# placeholder they carry in .env.example. This is the ONLY thing bootstrap owns:
# which keys are generated vs. set by hand. The template stays the single source
# of truth for structure — check_template_drift() below fails loud if any of
# these placeholders no longer matches the template, so a renamed placeholder can
# never silently skip its secret.
GENERATED_SECRETS = {
    "DB__PASSWORD": "change-me-db-password",
    "REDIS__PASSWORD": "change-me-redis-password",
    "NATS__PASSWORD": "change-me-nats-password",
    "WEB__SECRET_KEY": "change-me-long-random-string",
}


def check_template_drift() -> None:
    """Fail fast if .env.example drifted from what bootstrap expects to fill.

    set_if_placeholder() couples to the template by exact `key=placeholder`
    match; without this guard a placeholder edit in .env.example would make
    bootstrap silently print "already set" and ship an unfilled secret.
    """
    template = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [
        f"{key}={placeholder}"
        for key, placeholder in GENERATED_SECRETS.items()
        if f"{key}={placeholder}" not in template
    ]
    if missing:
        raise SystemExit(
            "bootstrap: .env.example drifted — these expected lines are gone:\n"
            + "\n".join(f"  {line}" for line in missing)
            + "\nUpdate GENERATED_SECRETS in this script or restore the template."
        )


def set_if_placeholder(key: str, placeholder: str, value: str) -> None:
    """Replace ``key=placeholder`` with ``key=value``, placeholder lines only.

    Rewrites the line only while it still holds the exact placeholder, which
    keeps the script idempotent — a real secret is never overwritten on a
    re-run.
    """
    target = f"{key}={placeholder}"
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines(keepends=True)

    for i, line in enumerate(lines):
        if line.rstrip("\n") == target:
            newline = "\n" if line.endswith("\n") else ""
            lines[i] = f"{key}={value}{newline}"
            ENV_FILE.write_text("".join(lines), encoding="utf-8")
            print(f"✓ generated {key}")
            return

    print(f"• {key} already set — skipping")


def gen_secret() -> str:
    # 32 bytes of hex — matches the previous `openssl rand -hex 32`.
    return secrets.token_hex(32)


def main() -> None:
    # --- 0. Guard against template drift before touching anything ------------
    check_template_drift()

    # --- 1. Create .env from the template (never clobber an existing one) -----
    if ENV_FILE.exists():
        print(f"✓ {ENV_FILE.name} exists — keeping it")
    else:
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print(f"✓ created {ENV_FILE.name} from {ENV_EXAMPLE.name}")

    # --- 2. Generate secrets -------------------------------------------------
    for key, placeholder in GENERATED_SECRETS.items():
        set_if_placeholder(key, placeholder, gen_secret())

    # --- 3. VAPID keys for Web Push ------------------------------------------
    private_key = SECRETS_DIR / PRIVATE_KEY_NAME
    public_key = SECRETS_DIR / PUBLIC_KEY_NAME
    if private_key.exists() and public_key.exists():
        print("• VAPID keys exist — skipping")
    else:
        application_server_key = write_vapid_keys(SECRETS_DIR)
        print("✓ generated VAPID keys in secrets/")
        set_if_placeholder("PUBLIC_VAPID_KEY", "", application_server_key)

    # --- 4. Remaining manual steps -------------------------------------------
    print(
        "\n"
        "Bootstrap complete. Still set by hand in .env "
        "(real credentials, can't generate):\n"
        "  • BOT__TOKEN / BOT__CLIENT_ID / BOT__CLIENT_SECRET — "
        "create a bot via @BotFather\n"
        "  • PUSH__SUBSCRIBER — your contact email for Web Push\n"
        "\n"
        "Optional:\n"
        "  • MAIL__* — SMTP credentials. Unset = emails are logged, not sent (email\n"
        "    login/confirmation codes appear in the app logs).\n"
        "\n"
        "Then start the full environment:\n"
        "  just run-dev"
    )


if __name__ == "__main__":
    main()
