from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import cast, override

import pytest

from fanfan.application.interactors.notifications.send_test_notification import (
    TEST_NOTIFICATION_COOLDOWN_SECONDS,
    SendTestNotification,
)
from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions import notifications as notification_errors
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.core.vo.user import generate_user_id
from tests.fakes.event_broker import FakeEventBroker
from tests.fakes.id_provider import FakeIdProvider

pytestmark = pytest.mark.asyncio


class FakeCooldown(Cooldown):
    """Holds claimed keys forever: enough to see the second call rejected."""

    def __init__(self) -> None:
        self.claimed: dict[str, int] = {}

    @asynccontextmanager
    async def _claim(self, key: str, seconds: int) -> AsyncGenerator[None]:
        if key in self.claimed:
            raise CooldownActive(retry_after=self.claimed[key])
        self.claimed[key] = seconds
        try:
            yield
        except BaseException:
            del self.claimed[key]
            raise

    @override
    def claim(self, key: str, seconds: int) -> AbstractAsyncContextManager[None]:
        return self._claim(key, seconds)


def make_interactor(
    broker: FakeEventBroker, cooldown: FakeCooldown, id_provider: FakeIdProvider
) -> SendTestNotification:
    provider = CurrentUserProvider(id_provider, cast("UserGateway", object()))
    return SendTestNotification(provider, broker, cooldown)


async def test_a_second_test_within_the_cooldown_is_rejected() -> None:
    broker = FakeEventBroker()
    id_provider = FakeIdProvider()
    id_provider.set_current_user_id(generate_user_id())
    send = make_interactor(broker, FakeCooldown(), id_provider)

    await send()
    with pytest.raises(notification_errors.TestNotificationTooFast) as error:
        await send()

    assert len(broker.published_events) == 1
    assert error.value.details["retry_after"] == TEST_NOTIFICATION_COOLDOWN_SECONDS


async def test_the_cooldown_is_per_user() -> None:
    broker = FakeEventBroker()
    cooldown = FakeCooldown()
    id_provider = FakeIdProvider()
    send = make_interactor(broker, cooldown, id_provider)

    id_provider.set_current_user_id(generate_user_id())
    await send()
    id_provider.set_current_user_id(generate_user_id())
    await send()

    assert len(broker.published_events) == 2
