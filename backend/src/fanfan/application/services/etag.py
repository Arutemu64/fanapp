import hashlib


def compute_strong_etag(payload: str) -> str:
    # Strong validator (no W/ prefix): the payload is byte-stable, so a matching
    # ETag guarantees byte-identical content. Quoted per RFC 9110 §8.8.3. Strong
    # also matters for If-Match, which RFC 9110 §13.1.1 compares strongly, so a
    # weak tag could never authorize a write.
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f'"{digest}"'
