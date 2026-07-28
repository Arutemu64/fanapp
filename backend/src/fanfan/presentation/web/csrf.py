import logging

from fastapi import HTTPException, Request, status

from fanfan.presentation.web.config import WebConfig

logger = logging.getLogger(__name__)

# Fetch Metadata values that mean the request was not initiated by a foreign
# page. `none` covers user-initiated navigations (address bar, bookmark), which
# no other site can forge.
_TRUSTED_FETCH_SITES = frozenset({"same-origin", "none"})


def _is_trusted_origin(request: Request, config: WebConfig) -> bool:
    # Fetch Metadata is set by the browser itself and page script cannot forge
    # it, so it is checked first. OWASP marks the Origin fallback mandatory for
    # the browsers that predate Sec-Fetch-Site (widely available since 2023).
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None:
        return fetch_site in _TRUSTED_FETCH_SITES

    origin = request.headers.get("origin")
    return origin is not None and origin in config.cors_origins()


def ensure_trusted_origin(request: Request, config: WebConfig) -> None:
    """Reject a state-changing request that a foreign site could have triggered.

    Guards the OAuth flow-start endpoints. Those used to be plain GETs, which any
    site can trigger through an `<img>`, an iframe or a link prefetch — the class
    of bug behind CVE-2015-9284 in OmniAuth, and why OmniAuth 2.0 and
    django-allauth both moved flow initiation to POST. POST alone does not close
    it (a cross-origin HTML form still submits), so the initiator is verified
    here as well.

    Neither header present means the request did not come from a browser whose
    initiator we can establish. OWASP recommends blocking, and nothing legitimate
    reaches these endpoints except a form submit from our own pages.
    """
    if _is_trusted_origin(request, config):
        return

    # Attacker-path traffic — worth seeing, but only the initiator, never the
    # session. The request id is bound by middleware.
    logger.warning(
        "Rejected cross-origin request to an OAuth flow-start endpoint",
        extra={
            "path": request.url.path,
            "sec_fetch_site": request.headers.get("sec-fetch-site"),
            "origin": request.headers.get("origin"),
        },
    )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
