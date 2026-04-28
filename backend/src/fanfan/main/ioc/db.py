from collections.abc import AsyncIterable

from dishka import Provider, Scope, alias, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.factory import create_engine, create_session_pool
from fanfan.adapters.db.gateways.app_settings import SqlAppSettingsGateway
from fanfan.adapters.db.gateways.mailings import SqlMailingGateway
from fanfan.adapters.db.gateways.nominations import SqlNominationGateway
from fanfan.adapters.db.gateways.notifications import SqlNotificationGateway
from fanfan.adapters.db.gateways.participants import SqlParticipantGateway
from fanfan.adapters.db.gateways.permissions import (
    SqlPermissionGateway,
    SqlUserPermissionGateway,
)
from fanfan.adapters.db.gateways.push_subscriptions import (
    SqlPushSubscriptionGateway,
)
from fanfan.adapters.db.gateways.schedule_changes import SqlScheduleChangeGateway
from fanfan.adapters.db.gateways.schedule_events import SqlScheduleEventGateway
from fanfan.adapters.db.gateways.social_ids import SqlSocialIdentityGateway
from fanfan.adapters.db.gateways.subscriptions import SqlSubscriptionGateway
from fanfan.adapters.db.gateways.tickets import SqlTicketGateway
from fanfan.adapters.db.gateways.user_flags import SqlUserFlagGateway
from fanfan.adapters.db.gateways.users import SqlUserGateway
from fanfan.adapters.db.gateways.votes import SqlVoteGateway
from fanfan.adapters.db.uow import SqlTransactionManager
from fanfan.application.ports.queries import (
    MailingQuery,
    NominationQuery,
    NotificationQuery,
    ParticipantQuery,
    ScheduleChangeQuery,
    ScheduleEventQuery,
    SocialIdentityQuery,
    SubscriptionQuery,
    UserQuery,
)
from fanfan.application.ports.repositories import (
    AppSettingsRepository,
    PermissionRepository,
    ScheduleChangeRepository,
    ScheduleEventRepository,
    UserPermissionRepository,
)
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.repositories.nominations import NominationRepository
from fanfan.application.ports.repositories.notifications import NotificationRepository
from fanfan.application.ports.repositories.participants import ParticipantRepository
from fanfan.application.ports.repositories.push_subscriptions import (
    PushSubscriptionRepository,
)
from fanfan.application.ports.repositories.social_ids import SocialIdentityRepository
from fanfan.application.ports.repositories.subscriptions import SubscriptionRepository
from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.ports.repositories.user_flags import UserFlagRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.repositories.votes import VoteRepository
from fanfan.application.ports.trx import TransactionManager


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

    trx = provide(
        SqlTransactionManager, provides=TransactionManager, scope=Scope.REQUEST
    )


class SqlGatewaysProvider(Provider):
    scope = Scope.REQUEST

    nominations = provide(SqlNominationGateway)
    nominations_repo = alias(source=SqlNominationGateway, provides=NominationRepository)
    nominations_query = alias(source=SqlNominationGateway, provides=NominationQuery)

    participants = provide(SqlParticipantGateway)
    participants_repo = alias(
        source=SqlParticipantGateway, provides=ParticipantRepository
    )
    participants_query = alias(source=SqlParticipantGateway, provides=ParticipantQuery)

    schedule_events = provide(SqlScheduleEventGateway)
    schedule_events_repo = alias(
        source=SqlScheduleEventGateway, provides=ScheduleEventRepository
    )
    schedule_events_query = alias(
        source=SqlScheduleEventGateway, provides=ScheduleEventQuery
    )

    schedule_changes = provide(SqlScheduleChangeGateway)
    schedule_changes_repo = alias(
        source=SqlScheduleChangeGateway,
        provides=ScheduleChangeRepository,
    )
    schedule_changes_query = alias(
        source=SqlScheduleChangeGateway,
        provides=ScheduleChangeQuery,
    )

    settings = provide(SqlAppSettingsGateway, provides=AppSettingsRepository)

    subscriptions = provide(SqlSubscriptionGateway)
    subscriptions_repo = alias(
        source=SqlSubscriptionGateway, provides=SubscriptionRepository
    )
    subscriptions_query = alias(
        source=SqlSubscriptionGateway, provides=SubscriptionQuery
    )

    tickets = provide(SqlTicketGateway, provides=TicketRepository)

    users = provide(SqlUserGateway)
    users_repo = alias(source=SqlUserGateway, provides=UserRepository)
    users_query = alias(source=SqlUserGateway, provides=UserQuery)

    votes = provide(SqlVoteGateway, provides=VoteRepository)
    flags = provide(SqlUserFlagGateway, provides=UserFlagRepository)
    permissions = provide(SqlPermissionGateway, provides=PermissionRepository)
    user_permissions = provide(
        SqlUserPermissionGateway, provides=UserPermissionRepository
    )

    push_subscriptions = provide(
        SqlPushSubscriptionGateway, provides=PushSubscriptionRepository
    )

    mailings = provide(SqlMailingGateway)
    mailings_repo = alias(source=SqlMailingGateway, provides=MailingRepository)
    mailings_query = alias(source=SqlMailingGateway, provides=MailingQuery)

    notifications = provide(SqlNotificationGateway)
    notifications_repo = alias(
        source=SqlNotificationGateway, provides=NotificationRepository
    )
    notifications_query = alias(
        source=SqlNotificationGateway, provides=NotificationQuery
    )

    social_ids = provide(SqlSocialIdentityGateway)
    social_ids_repo = alias(
        source=SqlSocialIdentityGateway, provides=SocialIdentityRepository
    )
    social_ids_query = alias(
        source=SqlSocialIdentityGateway, provides=SocialIdentityQuery
    )
