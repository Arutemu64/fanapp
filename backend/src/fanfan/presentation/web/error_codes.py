"""Discovery of the error `code` values a client can receive over HTTP.

A single source of truth for two consumers:

* the OpenAPI generator, which stamps these codes onto ``ErrorMessage.code`` as an
  ``enum`` so the frontend gets a typed union (and can check its copy is complete);
* the status-map completeness test.
"""

import importlib
import pkgutil

import fanfan.core.exceptions as exceptions_pkg
from fanfan.core.exceptions.base import AppException
from fanfan.presentation.web.exceptions import (
    EXCEPTION_STATUS_MAP,
    HTTP_ERROR_CODE,
    INTERNAL_ERROR_CODE,
)
from fanfan.presentation.web.schemas.error import VALIDATION_ERROR_CODE

# Domain exceptions also live in a couple of adapter packages; import them so
# their subclasses are registered for discovery.
_EXTRA_EXCEPTION_MODULES = (
    "fanfan.adapters.api.cosplay2.exceptions",
    "fanfan.adapters.api.ticketscloud.exceptions",
)


def _import_all_exception_modules() -> None:
    for module in pkgutil.iter_modules(exceptions_pkg.__path__):
        importlib.import_module(f"{exceptions_pkg.__name__}.{module.name}")
    for name in _EXTRA_EXCEPTION_MODULES:
        importlib.import_module(name)


def _subclasses(cls: type[AppException]) -> set[type[AppException]]:
    direct = cls.__subclasses__()
    result: set[type[AppException]] = set(direct)
    for sub in direct:
        result |= _subclasses(sub)
    return result


def all_concrete_exceptions() -> set[type[AppException]]:
    """Every raisable domain exception (overrides ``code``); skips bases/markers."""
    _import_all_exception_modules()
    return {cls for cls in _subclasses(AppException) if cls.code != AppException.code}


def resolves_to_status(cls: type[AppException]) -> bool:
    """True if the exception maps to a client-facing status via a marker.

    Client-facing means a 4xx or the 502 upstream-failure marker — anything with a
    reason the client can act on. Exceptions with no marker resolve to a generic
    500 and are treated as internal-only.
    """
    return any(base in EXCEPTION_STATUS_MAP for base in cls.__mro__)


def client_facing_error_codes() -> set[str]:
    """Every error ``code`` a client can receive over HTTP.

    Domain exceptions that resolve to a status marker, plus the codes the handlers
    synthesize (validation, generic HTTP, unexpected). Internal-only exceptions
    (those that resolve to 500) are excluded.
    """
    codes = {cls.code for cls in all_concrete_exceptions() if resolves_to_status(cls)}
    codes.update({VALIDATION_ERROR_CODE, HTTP_ERROR_CODE, INTERNAL_ERROR_CODE})
    return codes
