from typing import Protocol


class HtmlSanitizer(Protocol):
    def sanitize(self, text: str) -> str:
        r"""Sanitize notification text down to a small, safe HTML subset.

        The result is the canonical stored form of a notification body: it keeps
        only the inline formatting tags that every delivery channel can handle
        (Telegram HTML messages, the web UI, OS push), with line breaks expressed
        as plain "\n" characters. Everything else is stripped.
        """
        ...
