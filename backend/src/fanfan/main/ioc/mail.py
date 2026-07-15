import logging

from dishka import Provider, Scope, provide
from fastapi_mail import ConnectionConfig, FastMail

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.mail.config import MailConfig
from fanfan.adapters.mail.email_sender import FastEmailSender, LogOnlyEmailSender
from fanfan.application.ports.email_sender import EmailSender

logger = logging.getLogger(__name__)


class MailProvider(Provider):
    scope = Scope.APP

    @provide
    def get_mail_config(self, config: EnvConfig) -> MailConfig | None:
        # Optional — when unset, get_email_sender falls back to a log-only sender.
        return config.mail

    @provide
    def get_email_sender(self, config: MailConfig | None) -> EmailSender:
        # Mail is optional: without SMTP config, fall back to a log-only sender
        # so the app boots and email-based auth flows degrade gracefully.
        if config is None:
            logger.warning(
                "Mail is not configured — outgoing emails will be logged, not sent"
            )
            return LogOnlyEmailSender()

        connection_config = ConnectionConfig(
            MAIL_USERNAME=config.username,
            MAIL_PASSWORD=config.password,
            MAIL_SERVER=config.host,
            MAIL_PORT=config.port,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            MAIL_FROM=config.sender.email,
            MAIL_FROM_NAME=config.sender.name,
        )
        return FastEmailSender(FastMail(connection_config))
