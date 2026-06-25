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
# backend venv (`uv run --project backend python scripts/bootstrap.py`) so the
# `fanfan` import below resolves.
import secrets
import shutil
from pathlib import Path

from fanfan.main.generate_vapid import (
    PRIVATE_KEY_NAME,
    PUBLIC_KEY_NAME,
    write_vapid_keys,
)

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
SECRETS_DIR = ROOT / "secrets"


def set_if_placeholder(key: str, placeholder: str, value: str) -> None:
    """Replace `key=placeholder` with `key=value`, but only while the line still
    holds the exact placeholder. Keeps the script idempotent — a real secret is
    never overwritten on a re-run.
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
    # --- 1. Create .env from the template (never clobber an existing one) -----
    if ENV_FILE.exists():
        print(f"✓ {ENV_FILE.name} exists — keeping it")
    else:
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print(f"✓ created {ENV_FILE.name} from {ENV_EXAMPLE.name}")

    # --- 2. Generate secrets -------------------------------------------------
    set_if_placeholder("DB__PASSWORD", "change-me-db-password", gen_secret())
    set_if_placeholder("REDIS__PASSWORD", "change-me-redis-password", gen_secret())
    set_if_placeholder("NATS__PASSWORD", "change-me-nats-password", gen_secret())
    set_if_placeholder("WEB__SECRET_KEY", "change-me-long-random-string", gen_secret())

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
