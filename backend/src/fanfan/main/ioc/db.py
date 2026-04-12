from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.factory import create_engine, create_session_pool
from fanfan.adapters.db.repositories.app_settings import SqlAppSettingsRepository
from fanfan.adapters.db.repositories.mailings import SqlMailingRepository
from fanfan.adapters.db.repositories.nominations import SqlNominationRepository
from fanfan.adapters.db.repositories.notifications import SqlNotificationRepository
from fanfan.adapters.db.repositories.participants import SqlParticipantRepository
from fanfan.adapters.db.repositories.permissions import SqlPermissionRepository
from fanfan.adapters.db.repositories.push_subscriptions import (
    SqlPushSubscriptionRepository,
)
from fanfan.adapters.db.repositories.schedule_changes import SqlScheduleChangeRepository
from fanfan.adapters.db.repositories.schedule_events import SqlScheduleEventRepository
from fanfan.adapters.db.repositories.social_ids import SqlSocialIdentityRepository
from fanfan.adapters.db.repositories.subscriptions import SqlSubscriptionRepository
from fanfan.adapters.db.repositories.tickets import SqlTicketRepository
from fanfan.adapters.db.repositories.user_flags import SqlUserFlagRepository
from fanfan.adapters.db.repositories.users import SqlUserRepository
from fanfan.adapters.db.repositories.votes import SqlVoteRepository
from fanfan.adapters.db.uow import SqlTransactionManager
from fanfan.application.ports.repositories import (
    AppSettingsRepository,
    PermissionRepository,
    ScheduleChangeRepository,
    ScheduleEventRepository,
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
    def get_db_config(self, config: EnvConfig) -> DatabaseConfig:
        return config.db

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


class SqlRepositoriesProvider(Provider):
    scope = Scope.REQUEST

    nominations = provide(SqlNominationRepository, provides=NominationRepository)
    participants = provide(SqlParticipantRepository, provides=ParticipantRepository)
    schedule_events = provide(
        SqlScheduleEventRepository, provides=ScheduleEventRepository
    )
    schedule_changes = provide(
        SqlScheduleChangeRepository,
        provides=ScheduleChangeRepository,
    )
    settings = provide(SqlAppSettingsRepository, provides=AppSettingsRepository)
    subscriptions = provide(SqlSubscriptionRepository, provides=SubscriptionRepository)
    tickets = provide(SqlTicketRepository, provides=TicketRepository)
    users = provide(SqlUserRepository, provides=UserRepository)
    votes = provide(SqlVoteRepository, provides=VoteRepository)
    flags = provide(SqlUserFlagRepository, provides=UserFlagRepository)
    permissions = provide(SqlPermissionRepository, provides=PermissionRepository)
    push_subscriptions = provide(
        SqlPushSubscriptionRepository, provides=PushSubscriptionRepository
    )
    mailings = provide(SqlMailingRepository, provides=MailingRepository)
    notifications = provide(SqlNotificationRepository, provides=NotificationRepository)
    social_ids = provide(SqlSocialIdentityRepository, provides=SocialIdentityRepository)
