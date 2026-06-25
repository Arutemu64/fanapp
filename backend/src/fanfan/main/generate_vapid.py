from pathlib import Path

from webpush.vapid import VAPID

# Repo root: backend/src/fanfan/main/ -> parents[4]. Mirrors generate_openapi.py.
SECRETS_DIR = Path(__file__).resolve().parents[4] / "secrets"

PRIVATE_KEY_NAME = "private_key.pem"
PUBLIC_KEY_NAME = "public_key.pem"


def generate_vapid_keys() -> tuple[bytes, bytes, str]:
    """Generate a VAPID keypair.

    Returns (private_key_pem, public_key_pem, application_server_key). The third
    value is the base64url-encoded (unpadded) public key the frontend uses to
    subscribe to Web Push. This is the single import site for the webpush API,
    so a future webpush change only touches this module.
    """
    return VAPID.generate_keys()


def write_vapid_keys(secrets_dir: Path) -> str:
    """Generate a keypair, write the PEM files into `secrets_dir`, and return
    the application server key. Overwrites any existing keys, so callers that
    must stay idempotent (e.g. bootstrap) check for existing keys first.
    """
    private_pem, public_pem, application_server_key = generate_vapid_keys()

    secrets_dir.mkdir(parents=True, exist_ok=True)
    private_key_path = secrets_dir / PRIVATE_KEY_NAME
    private_key_path.write_bytes(private_pem)
    (secrets_dir / PUBLIC_KEY_NAME).write_bytes(public_pem)

    # Private key is a secret — restrict to owner read/write (best-effort on Windows).
    private_key_path.chmod(0o600)

    return application_server_key


def main() -> None:
    application_server_key = write_vapid_keys(SECRETS_DIR)
    print(f"keys written to {SECRETS_DIR}")
    print(f"application_server_key={application_server_key}")


if __name__ == "__main__":
    main()
