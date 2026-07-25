import logging

from fastapi_mail import FastMail, MessageSchema, MessageType
from fastapi_mail.schemas import MultipartSubtypeEnum
from pydantic import NameEmail

from fanfan.application.ports.email_sender import EmailMessage, EmailSender

logger = logging.getLogger(__name__)


class FastEmailSender(EmailSender):
    def __init__(self, mail: FastMail):
        self.mail = mail

    async def send(self, message: EmailMessage) -> None:
        recipients = [
            NameEmail(name=recipient.name, email=recipient.email)
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
        await self.mail.send_message(fast_mail_message)


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
