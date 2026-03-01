from dishka import Provider, Scope, provide
from fastapi_mail import ConnectionConfig, FastMail

from fanfan.adapters.mail.config import MailConfig


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
            MAIL_FROM="FAN App <from@app.fancom.info>",
        )

    @provide
    def get_mail(self, config: ConnectionConfig) -> FastMail:
        return FastMail(config)
