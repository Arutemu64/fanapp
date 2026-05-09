import logging

from fastapi_mail import FastMail, MessageSchema, MessageType

from fanfan.application.ports.email_sender import EmailMessage, EmailSender

logger = logging.getLogger(__name__)


class FastEmailSender(EmailSender):
    def __init__(self, mail: FastMail):
        self.mail = mail

    async def send(self, message: EmailMessage) -> None:
        # Convert the application-level email DTO to the FastMail-specific schema here.
        recipients = [recipient.email for recipient in message.recipients]
        logger.info("Sending email to %s", recipients)
        fast_mail_message = MessageSchema(
            subject=message.subject,
            recipients=recipients,  # type: ignore[arg-type] fails when using NameEmail
            body=message.html_body,
            subtype=MessageType.html,
        )
        await self.mail.send_message(fast_mail_message)
