import pytest
from aiosmtplib.errors import SMTPServerDisconnected
from fastapi_mail import MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import NameEmail

from fanfan.adapters.mail.email_sender import FastEmailSender, _encode_display_name
from fanfan.application.ports.email_sender import EmailMessage, EmailRecipient
from fanfan.core.exceptions.email import EmailDeliveryFailed

pytestmark = pytest.mark.unit


def _rendered_to_header(name: str) -> str:
    """Reproduce how fastapi-mail flattens a recipient into the To header."""
    recipient = NameEmail(name=_encode_display_name(name), email="user@example.com")
    message = MessageSchema(
        subject="x",
        recipients=[recipient],
        body="b",
        subtype=MessageType.plain,
    )
    return ", ".join(str(r) for r in message.recipients)


@pytest.mark.parametrize(
    "display_name",
    [
        "Аня",  # Cyrillic — the production failure case (all usernames are Cyrillic)
        "Ваня, лучший",  # Cyrillic with a comma
        "O'Brien, Sam",  # ASCII with a comma that must stay quoted
        "Иван <hack@evil.com>",  # header-injection attempt folded into the name
        "",  # empty username
    ],
)
def test_display_name_keeps_to_header_ascii(display_name: str):
    # Yandex Postbox rejects a non-ASCII To header with "email address parse
    # failed (To)"; the display name must be RFC 2047-encoded to pure ASCII.
    header = _rendered_to_header(display_name)
    assert header.isascii()
    # The real recipient address must survive intact and remain the only address.
    assert header.endswith("<user@example.com>")


def test_plain_ascii_name_is_left_readable():
    # A simple ASCII name needs no encoding and stays human-readable.
    assert _encode_display_name("Ivan") == "Ivan"


class _FailingFastMail:
    def __init__(self, error: Exception):
        self._error = error

    async def send_message(self, message: object) -> None:
        _ = message
        raise self._error


def _message() -> EmailMessage:
    return EmailMessage(
        subject="x",
        recipients=[EmailRecipient(name="Ivan", email="user@example.com")],
        html_body="<p>hi</p>",
    )


@pytest.mark.parametrize(
    "error",
    [
        # fastapi-mail wraps connection setup failures in ConnectionErrors...
        ConnectionErrors("connect failed"),
        # ...and aiosmtplib errors bubble from the send itself (the production case).
        SMTPServerDisconnected("Unexpected EOF received"),
    ],
)
async def test_smtp_failure_becomes_domain_error(error: Exception):
    # A relay outage must surface as a domain error (mapped to 502) instead of an
    # unhandled exception, so the caller reports it and it stays out of Sentry.
    sender = FastEmailSender(_FailingFastMail(error))  # type: ignore[arg-type]
    with pytest.raises(EmailDeliveryFailed):
        await sender.send(_message())
