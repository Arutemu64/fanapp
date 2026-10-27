"""FestEngine webhook config and Standard Webhooks signature check.

The spec: https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md
Hand-rolled instead of the ``standardwebhooks`` package: it is a dozen lines.
"""

import base64
import binascii
import hashlib
import hmac
from dataclasses import dataclass

from pydantic import BaseModel, SecretStr, field_validator

# Standard Webhooks marks a base64 signing key with this prefix.
KEY_PREFIX = "whsec_"
SIGNATURE_VERSION = "v1"
TIMESTAMP_TOLERANCE_SECONDS = 5 * 60


def _decode_secret(secret: str) -> bytes:
    return base64.b64decode(secret.removeprefix(KEY_PREFIX), validate=True)


class FestEngineConfig(BaseModel):
    """Unset ``webhook_secret`` turns the endpoint off: it answers 404."""

    webhook_secret: SecretStr | None = None

    @field_validator("webhook_secret", mode="after")
    @classmethod
    def _check_base64(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        try:
            _decode_secret(value.get_secret_value())
        except binascii.Error as exc:
            msg = "FESTENGINE__WEBHOOK_SECRET must be whsec_ followed by base64"
            raise ValueError(msg) from exc
        return value


@dataclass(frozen=True, slots=True, kw_only=True)
class SignedRequest:
    msg_id: str | None
    timestamp: str | None
    signatures: str | None
    body: bytes


def sign(secret: str, msg_id: str, timestamp: str, body: bytes) -> str:
    """The ``v1,<base64>`` signature of one request."""
    signed = f"{msg_id}.{timestamp}.".encode() + body
    digest = hmac.new(_decode_secret(secret), signed, hashlib.sha256).digest()
    return f"{SIGNATURE_VERSION},{base64.b64encode(digest).decode()}"


def verify_signature(secret: str, request: SignedRequest, now: float) -> bool:
    """True when one of the request's signatures matches and it is recent.

    The timestamp window stops a captured request from being replayed later.
    """
    if not (request.msg_id and request.timestamp and request.signatures):
        return False
    try:
        timestamp = int(request.timestamp)
    except ValueError:
        return False
    if abs(now - timestamp) > TIMESTAMP_TOLERANCE_SECONDS:
        return False

    expected = sign(secret, request.msg_id, request.timestamp, request.body)
    expected_bytes = expected.encode()
    # The header holds space-separated signatures, e.g. during key rotation.
    return any(
        hmac.compare_digest(candidate.encode(), expected_bytes)
        for candidate in request.signatures.split(" ")
    )
