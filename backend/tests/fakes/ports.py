"""Complete port stubs that reject calls a test has not configured."""

from collections.abc import Sequence
from datetime import datetime
from typing import override

from fanfan.application.commands.base import Command
from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.dto.notification import NotificationDTO
from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
    UserDetailsDTO,
    UserListFilter,
    UserListItemDTO,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.gateways.push_subscriptions import PushSubscriptionGateway
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.base import AggregateRoot
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.notification import Notification
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.user import UserId, UserNumber, UserRole


class StubPushSubscriptionGateway(PushSubscriptionGateway):
    @override
    async def add(self, model: PushSubscription) -> None:
        msg = "Unexpected PushSubscriptionGateway.add call"
        raise AssertionError(msg)

    @override
    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        msg = "Unexpected PushSubscriptionGateway.get_by_endpoint call"
        raise AssertionError(msg)

    @override
    async def exists_for_user(self, user_id: UserId, endpoint: str) -> bool:
        msg = "Unexpected PushSubscriptionGateway.exists_for_user call"
        raise AssertionError(msg)

    @override
    async def list_by_user(self, user_id: UserId) -> list[PushSubscription]:
        msg = "Unexpected PushSubscriptionGateway.list_by_user call"
        raise AssertionError(msg)

    @override
    async def delete(self, model: PushSubscription) -> None:
        msg = "Unexpected PushSubscriptionGateway.delete call"
        raise AssertionError(msg)


class StubSocialIdentityGateway(SocialIdentityGateway):
    @override
    async def add(self, social_identity: SocialIdentity) -> None:
        msg = "Unexpected SocialIdentityGateway.add call"
        raise AssertionError(msg)

    @override
    async def get_by_provider(
        self, user_id: UserId, provider: SocialProvider
    ) -> SocialIdentity | None:
        msg = "Unexpected SocialIdentityGateway.get_by_provider call"
        raise AssertionError(msg)

    @override
    async def get_by_subject(
        self, provider: SocialProvider, subject: str
    ) -> SocialIdentity | None:
        msg = "Unexpected SocialIdentityGateway.get_by_subject call"
        raise AssertionError(msg)

    @override
    async def count_by_user(self, user_id: UserId) -> int:
        msg = "Unexpected SocialIdentityGateway.count_by_user call"
        raise AssertionError(msg)

    @override
    async def delete(self, social_identity: SocialIdentity) -> None:
        msg = "Unexpected SocialIdentityGateway.delete call"
        raise AssertionError(msg)


class StubUserGateway(UserGateway):
    @override
    async def add(self, user: User) -> None:
        msg = "Unexpected UserGateway.add call"
        raise AssertionError(msg)

    @override
    async def get_by_id(self, user_id: UserId) -> User | None:
        msg = "Unexpected UserGateway.get_by_id call"
        raise AssertionError(msg)

    @override
    async def get_by_number(self, number: UserNumber) -> User | None:
        msg = "Unexpected UserGateway.get_by_number call"
        raise AssertionError(msg)

    @override
    async def get_by_username(self, username: str) -> User | None:
        msg = "Unexpected UserGateway.get_by_username call"
        raise AssertionError(msg)

    @override
    async def get_by_email(self, email: str) -> User | None:
        msg = "Unexpected UserGateway.get_by_email call"
        raise AssertionError(msg)

    @override
    async def save(self, user: User) -> None:
        msg = "Unexpected UserGateway.save call"
        raise AssertionError(msg)

    @override
    async def read_current_user(self, user_id: UserId) -> CurrentUserDTO | None:
        msg = "Unexpected UserGateway.read_current_user call"
        raise AssertionError(msg)

    @override
    async def read_ids_by_roles(self, *roles: UserRole) -> list[UserId]:
        msg = "Unexpected UserGateway.read_ids_by_roles call"
        raise AssertionError(msg)

    @override
    async def count_voting_contest_pool(self) -> int:
        msg = "Unexpected UserGateway.count_voting_contest_pool call"
        raise AssertionError(msg)

    @override
    async def draw_voting_contest_winner(self) -> tuple[UserBaseDTO | None, int]:
        msg = "Unexpected UserGateway.draw_voting_contest_winner call"
        raise AssertionError(msg)

    @override
    async def read_ids_receiving_all_announcements(self) -> list[UserId]:
        msg = "Unexpected UserGateway.read_ids_receiving_all_announcements call"
        raise AssertionError(msg)

    @override
    async def read_schedule_editors(self) -> list[UserBaseDTO]:
        msg = "Unexpected UserGateway.read_schedule_editors call"
        raise AssertionError(msg)

    @override
    async def read_users_page(
        self, *, pagination: CursorPagination, user_filter: UserListFilter
    ) -> list[UserListItemDTO]:
        msg = "Unexpected UserGateway.read_users_page call"
        raise AssertionError(msg)

    @override
    async def count_users(self, *, user_filter: UserListFilter) -> int:
        msg = "Unexpected UserGateway.count_users call"
        raise AssertionError(msg)

    @override
    async def read_user_details(self, user_id: UserId) -> UserDetailsDTO | None:
        msg = "Unexpected UserGateway.read_user_details call"
        raise AssertionError(msg)


class StubNotificationGateway(NotificationGateway):
    @override
    async def add_many(self, notifications: Sequence[Notification]) -> int:
        msg = "Unexpected NotificationGateway.add_many call"
        raise AssertionError(msg)

    @override
    async def get(
        self, notification_id: NotificationId, *, lock: bool = True
    ) -> Notification | None:
        msg = "Unexpected NotificationGateway.get call"
        raise AssertionError(msg)

    @override
    async def is_superseded(self, notification: Notification) -> bool:
        msg = "Unexpected NotificationGateway.is_superseded call"
        raise AssertionError(msg)

    @override
    async def mark_all_read_for_user(
        self, user_id: UserId, timestamp: datetime
    ) -> None:
        msg = "Unexpected NotificationGateway.mark_all_read_for_user call"
        raise AssertionError(msg)

    @override
    async def mark_read_for_user(
        self,
        user_id: UserId,
        notification_ids: list[NotificationId],
        timestamp: datetime,
    ) -> None:
        msg = "Unexpected NotificationGateway.mark_read_for_user call"
        raise AssertionError(msg)

    @override
    async def count_unread_for_user(self, user_id: UserId) -> int:
        msg = "Unexpected NotificationGateway.count_unread_for_user call"
        raise AssertionError(msg)

    @override
    async def delete_all_by_mailing_id(self, mailing_id: MailingId) -> None:
        msg = "Unexpected NotificationGateway.delete_all_by_mailing_id call"
        raise AssertionError(msg)

    @override
    async def delete_created_before(self, days: int) -> int:
        msg = "Unexpected NotificationGateway.delete_created_before call"
        raise AssertionError(msg)

    @override
    async def read_realtime_notifications(
        self, notification_ids: Sequence[NotificationId]
    ) -> list[NotificationDTO]:
        msg = "Unexpected NotificationGateway.read_realtime_notifications call"
        raise AssertionError(msg)

    @override
    async def read_list_user_notifications(
        self, user_id: UserId, pagination: CursorPagination
    ) -> list[NotificationDTO]:
        msg = "Unexpected NotificationGateway.read_list_user_notifications call"
        raise AssertionError(msg)


class StubMailingGateway(MailingGateway):
    @override
    async def add(self, mailing: Mailing) -> None:
        msg = "Unexpected MailingGateway.add call"
        raise AssertionError(msg)

    @override
    async def get(self, mailing_id: MailingId, *, lock: bool = True) -> Mailing | None:
        msg = "Unexpected MailingGateway.get call"
        raise AssertionError(msg)

    @override
    async def save(self, mailing: Mailing) -> None:
        msg = "Unexpected MailingGateway.save call"
        raise AssertionError(msg)

    @override
    async def read_broadcasts(self, pagination: CursorPagination) -> list[MailingDTO]:
        msg = "Unexpected MailingGateway.read_broadcasts call"
        raise AssertionError(msg)


class StubUnitOfWork(UnitOfWork):
    @override
    def register(self, entity: AggregateRoot) -> None:
        msg = "Unexpected UnitOfWork.register call"
        raise AssertionError(msg)

    @override
    def enqueue(self, command: Command) -> None:
        msg = "Unexpected UnitOfWork.enqueue call"
        raise AssertionError(msg)

    @override
    async def commit(self) -> None:
        msg = "Unexpected UnitOfWork.commit call"
        raise AssertionError(msg)

    @override
    async def rollback(self) -> None:
        msg = "Unexpected UnitOfWork.rollback call"
        raise AssertionError(msg)

    @override
    async def flush(self) -> None:
        msg = "Unexpected UnitOfWork.flush call"
        raise AssertionError(msg)
