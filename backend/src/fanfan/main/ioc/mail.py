from dishka import Provider, Scope, provide
from fastapi_mail import ConnectionConfig, FastMail

from fanfan.adapters.mail.config import MailConfig
from fanfan.adapters.mail.email_sender import FastEmailSender
from fanfan.application.ports.email_sender import EmailSender


class MailProvider(Provider):
    scope = Scope.APP

    @provide
    def get_connection_config(self, config: MailConfig) -> ConnectionConfig:
        return ConnectionConfig(
            MAIL_USERNAME=config.username,
            MAIL_PASSWORD=config.password,
            MAIL_SERVER=config.host,
            MAIL_PORT=config.port,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            MAIL_FROM=config.sender.email,
            MAIL_FROM_NAME=config.sender.name,
        )

    @provide
    def get_mail(self, config: ConnectionConfig) -> FastMail:
        return FastMail(config)

    email_sender = provide(FastEmailSender, provides=EmailSender)
