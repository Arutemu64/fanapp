from dishka import FromDishka
from dishka_faststream import inject
from faststream.nats import NatsRouter, PullSub

from fanfan.application.auth.send_email_verification import (
    SendEmailVerification,
    SendEmailVerificationCommand,
)
from fanfan.core.events.users import CreatedUserEvent, EmailVerificationRequestedEvent
from fanfan.presentation.faststream.jstream import stream

users_router = NatsRouter()


@users_router.subscriber(
    CreatedUserEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_email_verification",
)
@inject
async def send_email_verification(
    data: CreatedUserEvent,
    interactor: FromDishka[SendEmailVerification],
):
    await interactor(SendEmailVerificationCommand(user_id=data.user_id))


@users_router.subscriber(
    EmailVerificationRequestedEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_email_verification_on_request",
)
@inject
async def send_email_verification_on_request(
    data: EmailVerificationRequestedEvent,
    interactor: FromDishka[SendEmailVerification],
):
    await interactor(SendEmailVerificationCommand(user_id=data.user_id))
