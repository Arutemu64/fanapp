"""Standard Webhooks signature check for incoming FestEngine events.

Spec: https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md
"""

import base64
import hashlib
import hmac
from datetime import datetime, timedelta

SECRET_PREFIX = "whsec_"  # noqa: S105 - a format marker, not a secret
SIGNATURE_VERSION = "v1"
# The spec's suggested tolerance; also bounds how long a captured request replays.
TIMESTAMP_TOLERANCE = timedelta(minutes=5)


def _signing_key(secret: str) -> bytes:
    encoded = secret.removeprefix(SECRET_PREFIX)
    return base64.b64decode(encoded)


def sign(secret: str, msg_id: str, timestamp: int, body: bytes) -> str:
    to_sign = f"{msg_id}.{timestamp}.".encode() + body
    digest = hmac.new(_signing_key(secret), to_sign, hashlib.sha256).digest()
    return f"{SIGNATURE_VERSION},{base64.b64encode(digest).decode('ascii')}"


def verify_signature(  # noqa: PLR0913, PLR0917
    secret: str,
    msg_id: str | None,
    timestamp: str | None,
    signature_header: str | None,
    body: bytes,
    now: datetime,
) -> bool:
    """Whether one of the header's signatures matches and the timestamp is fresh."""
    if not msg_id or not timestamp or not signature_header:
        return False
    try:
        sent_at = int(timestamp)
        expected = sign(secret, msg_id, sent_at, body)
    except ValueError:  # also a malformed secret: binascii.Error is one
        return False
    if abs(now.timestamp() - sent_at) > TIMESTAMP_TOLERANCE.total_seconds():
        return False
    # Space-delimited; several during a secret rotation.
    return any(
        hmac.compare_digest(candidate.encode(), expected.encode())
        for candidate in signature_header.split(" ")
    )
