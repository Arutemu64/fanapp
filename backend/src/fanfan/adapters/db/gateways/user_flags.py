from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.user_flag import UserFlagMapper
from fanfan.adapters.db.models import UserFlagORM
from fanfan.application.ports.gateways.user_flags import UserFlagGateway
from fanfan.core.models.user_flag import UserFlag
from fanfan.core.vo.user import UserId


class SqlUserFlagGateway(UserFlagGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = UserFlagMapper()

    async def add(self, flag: UserFlag) -> None:
        flag_orm = self.mapper.from_model(flag)
        self.session.add(flag_orm)
        await self.session.flush([flag_orm])
        return

    async def get_by_user(self, user_id: UserId, flag_name: str) -> UserFlag | None:
        stmt = (
            select(UserFlagORM)
            .where(
                and_(
                    UserFlagORM.user_id == user_id,
                    UserFlagORM.name == flag_name,
                )
            )
            .with_for_update()
        )
        flag_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(flag_orm) if flag_orm else None

    async def delete(self, flag: UserFlag) -> None:
        await self.session.execute(delete(UserFlagORM).where(UserFlagORM.id == flag.id))
