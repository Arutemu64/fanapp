import pytest

from fanfan.presentation.web.error_codes import (
    all_concrete_exceptions,
    resolves_to_status,
)

pytestmark = pytest.mark.unit

# Concrete exceptions that intentionally resolve to HTTP 500 (no 4xx marker):
# they are raised in non-HTTP contexts (Telegram/NATS/scheduler), caught and
# re-raised as a flow-specific error, or signal a server misconfiguration. If
# one of these ever needs to surface to an HTTP client, give it a semantic
# marker instead of adding it here.
INTERNAL_ONLY: set[str] = {
    # Notification delivery — handled inside the NATS consumer, never HTTP.
    "NOTIFICATION_NOT_FOUND",
    "MAILING_NOT_FOUND",
    "MAILING_CANCELLED",
    "USER_NOT_REACHABLE",
    "NOTIFICATION_CHANNEL_UNAVAILABLE",
    "NOTIFICATION_RETRY_AFTER",
    # Rate-limit guards — caught and re-raised as a flow-specific RateLimited.
    "RATE_LOCK_COOLDOWN",
    "RATE_LOCK_IN_USE",
    # Missing vendor integration config — a server misconfiguration (500).
    "COSPLAY2_CONFIG_NOT_PROVIDED",
    "TCLOUD_CONFIG_NOT_PROVIDED",
}


def test_every_concrete_exception_resolves_or_is_internal():
    unmapped = {
        cls.code for cls in all_concrete_exceptions() if not resolves_to_status(cls)
    }

    assert unmapped == INTERNAL_ONLY, (
        "Mismatch between exceptions that resolve to HTTP 500 and INTERNAL_ONLY.\n"
        f"  Newly unmapped (give them a semantic marker, or add to INTERNAL_ONLY): "
        f"{sorted(unmapped - INTERNAL_ONLY)}\n"
        f"  Stale INTERNAL_ONLY entries (now mapped or removed): "
        f"{sorted(INTERNAL_ONLY - unmapped)}"
    )
