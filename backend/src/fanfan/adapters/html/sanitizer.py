import re
from typing import override

import nh3

from fanfan.application.ports.html_sanitizer import HtmlSanitizer

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
ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto", "tg"}

_BR_TAG = re.compile(r"(?i)<br\s*/?>")
_PARAGRAPH_BREAK = re.compile(r"(?i)</p\s*>\s*<p[^>]*>")
_PARAGRAPH_TAG = re.compile(r"(?i)</?p[^>]*>")


class Nh3HtmlSanitizer(HtmlSanitizer):
    @override
    def sanitize(self, text: str) -> str:
        text = _BR_TAG.sub("\n", text)
        text = _PARAGRAPH_BREAK.sub("\n\n", text)
        text = _PARAGRAPH_TAG.sub("", text)
        return nh3.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            url_schemes=ALLOWED_URL_SCHEMES,
            link_rel=None,
        ).strip()
