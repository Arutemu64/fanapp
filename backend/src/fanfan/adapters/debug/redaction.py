import re

# TicketsCloud can only authenticate its webhook with a secret path segment
# (docs/api.md "Inbound webhooks"), so anything that records a URL redacts it.
_SECRET_PATH = re.compile(r"(/webhooks/tcloud/)[^/?#\s]+")
REDACTED = "[Filtered]"


def redact_secret_paths(text: str) -> str:
    return _SECRET_PATH.sub(rf"\g<1>{REDACTED}", text)
