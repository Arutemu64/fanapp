"""Conditional-request headers (RFC 9110 §13) for the routes that honour them."""


def _listed_entity_tags(header: str) -> list[str]:
    return [value.strip() for value in header.split(",")]


def if_none_match_hits(header: str | None, etag: str) -> bool:
    """Whether a conditional GET already holds this exact representation.

    Clients echo the ETag back verbatim in ``If-None-Match``; the header may carry
    several comma-separated validators, so match against any of them. ``*`` matches
    any current representation (RFC 9110).
    """
    if header is None:
        return False
    candidates = _listed_entity_tags(header)
    return "*" in candidates or etag in candidates


def parse_if_match(header: str) -> frozenset[str] | None:
    """The entity-tags an ``If-Match`` header accepts, or None when it is ``*``.

    ``*`` matches any current representation (RFC 9110 §13.1.1), so for a resource
    that always exists it makes the write unconditional. A weak ``W/`` tag is kept
    as is: If-Match compares strongly, so it simply never matches.
    """
    candidates = _listed_entity_tags(header)
    if "*" in candidates:
        return None
    return frozenset(candidates)
