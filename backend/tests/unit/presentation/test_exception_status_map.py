import importlib
import pkgutil

import pytest

import fanfan.core.exceptions as exceptions_pkg
from fanfan.core.exceptions.base import AppException
from fanfan.presentation.web.exceptions import EXCEPTION_STATUS_MAP

pytestmark = pytest.mark.unit

# Concrete exceptions that intentionally resolve to HTTP 500 (no 4xx marker):
# they are raised in non-HTTP contexts (Telegram/NATS/scheduler), caught and
# re-raised as a flow-specific error, or signal a server misconfiguration. If
# any of these ever needs to surface to an HTTP client, give it a semantic
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

# Domain exceptions also live in a couple of adapter packages; import them so
# their subclasses are registered for discovery below.
_EXTRA_EXCEPTION_MODULES = (
    "fanfan.adapters.api.cosplay2.exceptions",
    "fanfan.adapters.api.ticketscloud.exceptions",
)


def _import_all_exception_modules() -> None:
    for module in pkgutil.iter_modules(exceptions_pkg.__path__):
        importlib.import_module(f"{exceptions_pkg.__name__}.{module.name}")
    for name in _EXTRA_EXCEPTION_MODULES:
        importlib.import_module(name)


def _all_subclasses(cls: type) -> set[type]:
    result = set(cls.__subclasses__())
    for sub in cls.__subclasses__():
        result |= _all_subclasses(sub)
    return result


def _resolves_to_status(cls: type[AppException]) -> bool:
    return any(base in EXCEPTION_STATUS_MAP for base in cls.__mro__)


def test_every_concrete_exception_resolves_or_is_internal():
    _import_all_exception_modules()

    # A concrete, raisable domain error overrides `code`; abstract bases and
    # semantic markers keep the inherited "UNKNOWN" and are skipped.
    concrete = {
        cls for cls in _all_subclasses(AppException) if cls.code != AppException.code
    }

    unclassified = sorted(
        cls.__name__
        for cls in concrete
        if not _resolves_to_status(cls) and cls.code not in INTERNAL_ONLY
    )

    assert not unclassified, (
        "These exceptions resolve to HTTP 500. Give each one a semantic marker "
        "(NotFound/Conflict/ConstraintViolation/RateLimited/AccessDenied/"
        "AuthenticationError) or, if it never reaches an HTTP client, add its "
        f"code to INTERNAL_ONLY: {unclassified}"
    )
