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
    CreatedUserEvent,
    EmailConfirmationCodeRequestedEvent,
    EmailLoginCodeRequestedEvent,
)
from fanfan.presentation.faststream.jstream import stream

users_router = NatsRouter()


@users_router.subscriber(
    CreatedUserEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_email_confirmation_code",
)
@inject
async def send_email_confirmation_code(
    data: CreatedUserEvent,
    interactor: FromDishka[SendEmailConfirmationCode],
):
    await interactor(SendEmailConfirmationCodeInput(user_id=data.user_id))


@users_router.subscriber(
    EmailConfirmationCodeRequestedEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_email_confirmation_code_on_request",
)
@inject
async def send_email_confirmation_code_on_request(
    data: EmailConfirmationCodeRequestedEvent,
    interactor: FromDishka[SendEmailConfirmationCode],
):
    await interactor(SendEmailConfirmationCodeInput(user_id=data.user_id))


@users_router.subscriber(
    EmailLoginCodeRequestedEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_login_code_email",
)
@inject
async def send_login_code_email(
    data: EmailLoginCodeRequestedEvent,
    interactor: FromDishka[SendLoginCodeEmail],
):
    await interactor(SendLoginCodeEmailInput(user_id=data.user_id))
