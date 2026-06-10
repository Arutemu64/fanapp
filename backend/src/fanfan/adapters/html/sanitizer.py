import re

import nh3

from fanfan.application.ports.html_sanitizer import HtmlSanitizer

# Inline formatting tags that are safe to keep. This set is intentionally the
# intersection of what Telegram's HTML parse mode accepts and what the web UI
# can render, so a single stored body works for every delivery channel.
ALLOWED_TAGS: set[str] = {
    "b",
    "strong",
    "i",
    "em",
    "u",
    "s",
    "a",
    "code",
    "pre",
    "blockquote",
}
ALLOWED_ATTRIBUTES: dict[str, set[str]] = {"a": {"href"}}
# Schemes allowed in links. "javascript:" and friends are rejected.
ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto", "tg"}

_BR_TAG = re.compile(r"(?i)<br\s*/?>")
_PARAGRAPH_BREAK = re.compile(r"(?i)</p\s*>\s*<p[^>]*>")
_PARAGRAPH_TAG = re.compile(r"(?i)</?p[^>]*>")


class Nh3HtmlSanitizer(HtmlSanitizer):
    def sanitize(self, text: str) -> str:
        # Telegram HTML uses plain "\n" for line breaks (no <br>/<p>), and the
        # web UI renders the same "\n" via CSS `white-space: pre-line`. So we
        # turn block/break tags into newlines before stripping everything else.
        text = _BR_TAG.sub("\n", text)
        text = _PARAGRAPH_BREAK.sub("\n\n", text)
        text = _PARAGRAPH_TAG.sub("", text)
        return nh3.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            url_schemes=ALLOWED_URL_SCHEMES,
            # No rel="noopener" needed: notification links render inline without
            # target="_blank", and keeping the markup minimal stays Telegram-safe.
            link_rel=None,
        ).strip()
