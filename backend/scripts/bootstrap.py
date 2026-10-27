#!/usr/bin/env python3
import secrets
import shutil
from pathlib import Path

from fanfan.main.generate_vapid import (
    PRIVATE_KEY_NAME,
    PUBLIC_KEY_NAME,
    write_vapid_keys,
)

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
SECRETS_DIR = ROOT / "secrets"

GENERATED_SECRETS = {
    "DB__PASSWORD": "change-me-db-password",
    "REDIS__PASSWORD": "change-me-redis-password",
    "NATS__PASSWORD": "change-me-nats-password",
    "WEB__SECRET_KEY": "change-me-long-random-string",
    "ALTCHA__HMAC_KEY": "change-me-altcha-hmac-key",
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
    return secrets.token_hex(32)


def main() -> None:
    check_template_drift()

    if ENV_FILE.exists():
        print(f"✓ {ENV_FILE.name} exists — keeping it")
    else:
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print(f"✓ created {ENV_FILE.name} from {ENV_EXAMPLE.name}")

    for key, placeholder in GENERATED_SECRETS.items():
        set_if_placeholder(key, placeholder, gen_secret())

    private_key = SECRETS_DIR / PRIVATE_KEY_NAME
    public_key = SECRETS_DIR / PUBLIC_KEY_NAME
    if private_key.exists() and public_key.exists():
        print("• VAPID keys exist — skipping")
    else:
        application_server_key = write_vapid_keys(SECRETS_DIR)
        print("✓ generated VAPID keys in secrets/")
        set_if_placeholder("PUBLIC_VAPID_KEY", "", application_server_key)

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
