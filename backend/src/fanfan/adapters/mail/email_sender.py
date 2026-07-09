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
        # Convert the application-level email DTO to the FastMail-specific schema here.
        recipients = [
            NameEmail(name=recipient.name, email=recipient.email)
            for recipient in message.recipients
        ]
        logger.info("Sending email to %s", recipients)
        # When a plain-text body is provided, send multipart/alternative: HTML as the
        # primary body and text as the alternative. FastMail flips the alternative to
        # the opposite subtype (plain) of `subtype` (html).
        fast_mail_message = MessageSchema(
            subject=message.subject,
            recipients=recipients,
            body=message.html_body,
            subtype=MessageType.html,
            alternative_body=message.text_body,
            multipart_subtype=(
                MultipartSubtypeEnum.alternative
                if message.text_body is not None
                else MultipartSubtypeEnum.mixed
            ),
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
