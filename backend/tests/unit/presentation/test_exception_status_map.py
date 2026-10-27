import pytest

from fanfan.presentation.web.error_codes import (
    all_concrete_exceptions,
    resolves_to_status,
)

pytestmark = pytest.mark.unit

INTERNAL_ONLY: set[str] = {
    "NOTIFICATION_NOT_FOUND",
    "USER_NOT_REACHABLE",
    "NOTIFICATION_CHANNEL_UNAVAILABLE",
    "NOTIFICATION_RETRY_AFTER",
    "NOTIFICATION_EXPIRED",
    "NOTIFICATION_SUPERSEDED",
    "COOLDOWN_ACTIVE",
    "COSPLAY2_CONFIG_NOT_PROVIDED",
    "TCLOUD_CONFIG_NOT_PROVIDED",
}


def test_every_concrete_exception_resolves_or_is_internal() -> None:
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
