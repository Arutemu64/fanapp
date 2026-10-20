from email import message_from_bytes, policy
from email.headerregistry import AddressHeader

import pytest
from pydantic import NameEmail, SecretStr

from fanfan.adapters.mail.config import MailConfig
from fanfan.adapters.mail.email_sender import SmtpEmailSender, build_mime_message
from fanfan.application.ports.email_sender import EmailMessage, EmailRecipient
from fanfan.core.exceptions.email import EmailDeliveryFailed

pytestmark = pytest.mark.unit


def _config(port: int = 587) -> MailConfig:
    return MailConfig(
        username="robot",
        password=SecretStr("secret"),
        host="127.0.0.1",
        port=port,
        sender=NameEmail(name="ФАН-ФАН", email="noreply@fanfan.example"),
        timeout=1,
    )


def _message(name: str = "Ivan", text_body: str | None = None) -> EmailMessage:
    return EmailMessage(
        subject="Код входа",
        recipients=[EmailRecipient(name=name, email="user@example.com")],
        html_body="<p>Привет</p>",
        text_body=text_body,
    )


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
def test_to_header_is_ascii_with_one_address(display_name: str) -> None:
    # Yandex Postbox rejects a non-ASCII To header with "email address parse
    # failed (To)"; the display name must be RFC 2047-encoded to pure ASCII.
    wire = bytes(build_mime_message(_message(display_name), _config()))
    to_line = next(
        line for line in wire.decode("ascii").splitlines() if line.startswith("To:")
    )
    assert to_line.isascii()
    # The real recipient address must survive intact and remain the only address.
    parsed = message_from_bytes(wire, policy=policy.default)["To"]
    assert isinstance(parsed, AddressHeader)
    assert [address.addr_spec for address in parsed.addresses] == ["user@example.com"]
    assert parsed.addresses[0].display_name == display_name


def test_whole_message_is_seven_bit() -> None:
    # Relays without 8BITMIME may mangle raw UTF-8 bodies.
    mime = build_mime_message(_message("Аня", text_body="Привет"), _config())
    assert bytes(mime).isascii()


def test_plain_ascii_name_is_left_readable() -> None:
    # A simple ASCII name needs no encoding and stays human-readable.
    wire = bytes(build_mime_message(_message("Ivan"), _config())).decode("ascii")
    assert "To: Ivan <user@example.com>" in wire


def test_text_alternative_comes_before_html() -> None:
    # RFC 2046: clients render the LAST part they understand, so HTML goes last
    # or Gmail/Apple Mail show the plain-text version.
    mime = build_mime_message(_message(text_body="Привет"), _config())
    assert mime.get_content_type() == "multipart/alternative"
    parts = [part.get_content_type() for part in mime.iter_parts()]
    assert parts == ["text/plain", "text/html"]


def test_html_only_message_is_single_part() -> None:
    mime = build_mime_message(_message(), _config())
    assert mime.get_content_type() == "text/html"


def test_message_id_uses_sender_domain() -> None:
    mime = build_mime_message(_message(), _config())
    assert mime["Message-ID"].endswith("@fanfan.example>")


async def test_smtp_failure_becomes_domain_error() -> None:
    # A relay outage must surface as a domain error (mapped to 502) instead of an
    # unhandled exception, so the caller reports it and it stays out of Sentry.
    # Port 1 on loopback refuses the connection, which aiosmtplib raises as
    # SMTPConnectError.
    sender = SmtpEmailSender(_config(port=1))
    with pytest.raises(EmailDeliveryFailed):
        await sender.send(_message())
