import logging
from email.headerregistry import Address
from email.message import EmailMessage as MimeMessage
from email.utils import formatdate, make_msgid
from typing import override

import aiosmtplib
import sentry_sdk

from fanfan.adapters.mail.config import MailConfig
from fanfan.application.ports.email_sender import EmailMessage, EmailSender
from fanfan.core.exceptions.email import EmailDeliveryFailed

logger = logging.getLogger(__name__)


def build_mime_message(message: EmailMessage, config: MailConfig) -> MimeMessage:
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
    mime["Message-ID"] = make_msgid(domain=config.sender.email.rsplit("@", 1)[-1])
    transfer_encoding = "quoted-printable"
    if message.text_body is None:
        mime.set_content(message.html_body, subtype="html", cte=transfer_encoding)
    else:
        mime.set_content(message.text_body, cte=transfer_encoding)
        mime.add_alternative(message.html_body, subtype="html", cte=transfer_encoding)
    return mime


class SmtpEmailSender(EmailSender):
    def __init__(self, config: MailConfig) -> None:
        self.config = config

    @override
    async def send(self, message: EmailMessage) -> None:
        logger.info("Sending email", extra={"recipient_count": len(message.recipients)})
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
            sentry_sdk.capture_exception(e)
            raise EmailDeliveryFailed from e


class LogOnlyEmailSender(EmailSender):
    """Used when no SMTP is configured: logs the message instead of sending it.

    In development this surfaces login and confirmation codes in the app logs,
    so the email-based auth flows remain usable without a real mail server.
    """

    @override
    async def send(self, message: EmailMessage) -> None:
        logger.warning(
            "Mail is not configured — email NOT sent. Subject %r to %s\n%s",
            message.subject,
            [recipient.email for recipient in message.recipients],
            message.html_body,
        )
