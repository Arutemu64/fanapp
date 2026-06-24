from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.factory import create_engine, create_session_pool
from fanfan.adapters.db.gateways.app_settings import SqlAppSettingsGateway
from fanfan.adapters.db.gateways.feedback import SqlFeedbackGateway
from fanfan.adapters.db.gateways.mailings import SqlMailingGateway
from fanfan.adapters.db.gateways.nominations import SqlNominationGateway
from fanfan.adapters.db.gateways.notifications import SqlNotificationGateway
from fanfan.adapters.db.gateways.outbox import SqlOutboxGateway
from fanfan.adapters.db.gateways.participants import SqlParticipantGateway
from fanfan.adapters.db.gateways.permissions import (
    SqlUserPermissionGateway,
)
from fanfan.adapters.db.gateways.push_subscriptions import (
    SqlPushSubscriptionGateway,
)
from fanfan.adapters.db.gateways.schedule_changes import SqlScheduleChangeGateway
from fanfan.adapters.db.gateways.schedule_items import SqlScheduleItemGateway
from fanfan.adapters.db.gateways.social_identity import SqlSocialIdentityGateway
from fanfan.adapters.db.gateways.subscriptions import SqlSubscriptionGateway
from fanfan.adapters.db.gateways.tickets import SqlTicketGateway
from fanfan.adapters.db.gateways.user_flags import SqlUserFlagGateway
from fanfan.adapters.db.gateways.users import SqlUserGateway
from fanfan.adapters.db.gateways.votes import SqlVoteGateway
from fanfan.adapters.db.uow import SqlUnitOfWork
from fanfan.application.ports.gateways import (
    AppSettingsGateway,
    ScheduleChangeGateway,
    ScheduleItemGateway,
    UserPermissionGateway,
)
from fanfan.application.ports.gateways.feedback import FeedbackGateway
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.user_flags import UserFlagGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork


class DbProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_engine(self, config: DatabaseConfig) -> AsyncIterable[AsyncEngine]:
        engine = create_engine(config)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.APP)
    def get_pool(self, engine: AsyncEngine) -> async_sessionmaker:
        return create_session_pool(engine)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self,
        pool: async_sessionmaker,
    ) -> AsyncIterable[AsyncSession]:
        async with pool() as session:
            yield session

    uow = provide(SqlUnitOfWork, provides=UnitOfWork, scope=Scope.REQUEST)


class SqlGatewaysProvider(Provider):
    scope = Scope.REQUEST

    # Each gateway implements a single repository port (reads + writes),
    # so one binding per aggregate is enough.
    nominations = provide(SqlNominationGateway, provides=NominationGateway)
    participants = provide(SqlParticipantGateway, provides=ParticipantGateway)
    schedule_items = provide(SqlScheduleItemGateway, provides=ScheduleItemGateway)
    schedule_changes = provide(SqlScheduleChangeGateway, provides=ScheduleChangeGateway)
    settings = provide(SqlAppSettingsGateway, provides=AppSettingsGateway)
    subscriptions = provide(SqlSubscriptionGateway, provides=SubscriptionGateway)
    tickets = provide(SqlTicketGateway, provides=TicketGateway)
    feedback = provide(SqlFeedbackGateway, provides=FeedbackGateway)
    users = provide(SqlUserGateway, provides=UserGateway)
    votes = provide(SqlVoteGateway, provides=VoteGateway)
    flags = provide(SqlUserFlagGateway, provides=UserFlagGateway)
    user_permissions = provide(SqlUserPermissionGateway, provides=UserPermissionGateway)
    push_subscriptions = provide(
        SqlPushSubscriptionGateway, provides=PushSubscriptionGateway
    )
    mailings = provide(SqlMailingGateway, provides=MailingGateway)
    notifications = provide(SqlNotificationGateway, provides=NotificationGateway)
    social_identities = provide(
        SqlSocialIdentityGateway, provides=SocialIdentityGateway
    )
    outbox = provide(SqlOutboxGateway, provides=OutboxGateway)
