import logging
from email.utils import formataddr

import sentry_sdk
from aiosmtplib.errors import SMTPException
from fastapi_mail import FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from fastapi_mail.schemas import MultipartSubtypeEnum
from pydantic import NameEmail

from fanfan.application.ports.email_sender import EmailMessage, EmailSender
from fanfan.core.exceptions.email import EmailDeliveryFailed

logger = logging.getLogger(__name__)


def _encode_display_name(name: str) -> str:
    """RFC 2047-encode a recipient display name so the To header is pure ASCII.

    fastapi-mail assigns the recipient to a legacy (compat32) MIMEMultipart
    header via ``str(NameEmail(...))``, which does NOT encode non-ASCII display
    names. A Cyrillic username then reaches the SMTP server as raw bytes and
    Yandex Postbox rejects the message with "email address parse failed (To)".
    ``formataddr`` encodes non-ASCII names and quotes ASCII specials (comma,
    quotes) — format against an empty address and drop it, keeping only the
    encoded/quoted display-name token to hand back to NameEmail.
    """
    if not name:
        return ""
    return formataddr((name, ""), charset="utf-8").removesuffix(" <>")


class FastEmailSender(EmailSender):
    def __init__(self, mail: FastMail):
        self.mail = mail

    async def send(self, message: EmailMessage) -> None:
        recipients = [
            NameEmail(name=_encode_display_name(recipient.name), email=recipient.email)
            for recipient in message.recipients
        ]
        logger.info("Sending email to %s", recipients)
        if message.text_body is not None:
            # Multipart/alternative. Order matters: RFC 2046 says clients render the
            # LAST part they understand, so the plain-text part must come first and
            # HTML last, or Gmail/Apple Mail show the plain-text version. FastMail
            # attaches `body` first and `alternative_body` last, so we send the PLAIN
            # text as the primary body (subtype=plain) and the HTML as the alternative
            # (FastMail flips it to html). This yields [text/plain, text/html].
            # See https://github.com/sabuhish/fastapi-mail/issues/115
            fast_mail_message = MessageSchema(
                subject=message.subject,
                recipients=recipients,
                body=message.text_body,
                subtype=MessageType.plain,
                alternative_body=message.html_body,
                multipart_subtype=MultipartSubtypeEnum.alternative,
            )
        else:
            fast_mail_message = MessageSchema(
                subject=message.subject,
                recipients=recipients,
                body=message.html_body,
                subtype=MessageType.html,
            )
        # fastapi-mail wraps connection setup failures in ConnectionErrors and lets
        # aiosmtplib's SMTPException (disconnect, timeout, auth/recipient refusal)
        # bubble from the send itself. Both mean the relay could not take the
        # message — translate them into a domain error so the caller reports a
        # transient outage (502) instead of an unhandled 500.
        try:
            await self.mail.send_message(fast_mail_message)
        except (ConnectionErrors, SMTPException) as e:
            logger.warning("Email delivery failed: %s", e)
            # Report the raw transport error, not the EmailDeliveryFailed we raise:
            # domain exceptions are scrubbed from Sentry on purpose (telemetry.py),
            # so capturing the SMTP error keeps an ops-visible, grouped signal that
            # mail is down — one issue with an event count, not a per-request crash.
            sentry_sdk.capture_exception(e)
            raise EmailDeliveryFailed from e


class LogOnlyEmailSender(EmailSender):
    """Used when no SMTP is configured: logs the message instead of sending it.

    In development this surfaces login and confirmation codes in the app logs,
    so the email-based auth flows remain usable without a real mail server.
    """

    async def send(self, message: EmailMessage) -> None:
        logger.warning(
            "Mail is not configured — email NOT sent. Subject %r to %s\n%s",
            message.subject,
            [recipient.email for recipient in message.recipients],
            message.html_body,
        )
