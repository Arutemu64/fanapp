from dishka import FromDishka
from dishka_faststream import inject
from faststream.nats import NatsRouter, PullSub

from fanfan.application.interactors.auth.send_email_confirmation_code import (
    SendEmailConfirmationCode,
    SendEmailConfirmationCodeInput,
)
from fanfan.application.interactors.auth.send_login_code_email import (
    SendLoginCodeEmail,
    SendLoginCodeEmailInput,
)
from fanfan.core.events.users import (
    EmailConfirmationCodeRequested,
    EmailLoginCodeRequested,
)
from fanfan.presentation.faststream.jstream import stream

users_router = NatsRouter()


@users_router.subscriber(
    EmailConfirmationCodeRequested.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_email_confirmation_code_on_request",
)
@inject
async def send_email_confirmation_code_on_request(
    data: EmailConfirmationCodeRequested,
    interactor: FromDishka[SendEmailConfirmationCode],
):
    await interactor(SendEmailConfirmationCodeInput(user_id=data.user_id))


@users_router.subscriber(
    EmailLoginCodeRequested.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_login_code_email",
)
@inject
async def send_login_code_email(
    data: EmailLoginCodeRequested,
    interactor: FromDishka[SendLoginCodeEmail],
):
    await interactor(SendLoginCodeEmailInput(user_id=data.user_id))
