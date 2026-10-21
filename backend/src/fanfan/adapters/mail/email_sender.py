import logging
from email.headerregistry import Address
from email.message import EmailMessage as MimeMessage
from email.utils import formatdate, make_msgid

import aiosmtplib
import sentry_sdk

from fanfan.adapters.mail.config import MailConfig
from fanfan.application.ports.email_sender import EmailMessage, EmailSender
from fanfan.core.exceptions.email import EmailDeliveryFailed

logger = logging.getLogger(__name__)


def build_mime_message(message: EmailMessage, config: MailConfig) -> MimeMessage:
    # The default (non-compat32) policy RFC 2047-encodes non-ASCII display names
    # in address headers. Yandex Postbox rejects a raw-UTF-8 To header with
    # "email address parse failed (To)", and every username here is Cyrillic.
    mime = MimeMessage()
    mime["Subject"] = message.subject
    mime["From"] = Address(
        display_name=config.sender.name, addr_spec=config.sender.email
    )
    mime["To"] = [
        Address(display_name=recipient.name, addr_spec=recipient.email)
        for recipient in message.recipients
    ]
    mime["Date"] = formatdate(localtime=True)
    # A Message-ID on the sender's own domain, not the container hostname that
    # make_msgid() defaults to — spam filters score a mismatched or missing one.
    mime["Message-ID"] = make_msgid(domain=config.sender.email.rsplit("@", 1)[-1])
    # set_content picks 8bit for short UTF-8 bodies, which a relay without the
    # 8BITMIME extension may mangle; quoted-printable keeps the wire 7-bit.
    transfer_encoding = "quoted-printable"
    if message.text_body is None:
        mime.set_content(message.html_body, subtype="html", cte=transfer_encoding)
    else:
        # multipart/alternative: RFC 2046 says clients render the LAST part they
        # understand, so plain text goes first and HTML last.
        mime.set_content(message.text_body, cte=transfer_encoding)
        mime.add_alternative(message.html_body, subtype="html", cte=transfer_encoding)
    return mime


class SmtpEmailSender(EmailSender):
    def __init__(self, config: MailConfig) -> None:
        self.config = config

    async def send(self, message: EmailMessage) -> None:
        logger.info("Sending email", extra={"recipient_count": len(message.recipients)})
        # Every aiosmtplib failure — refused or timed-out connection, disconnect,
        # auth or recipient refusal — subclasses SMTPException, and all mean the
        # relay could not take the message. Translate them into a domain error so
        # the caller reports a transient outage (502) instead of an unhandled 500.
        try:
            await aiosmtplib.send(
                build_mime_message(message, self.config),
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password.get_secret_value(),
                start_tls=True,
                timeout=self.config.timeout,
            )
        except aiosmtplib.SMTPException as e:
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
