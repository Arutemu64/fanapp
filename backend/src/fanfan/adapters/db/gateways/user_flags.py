from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.user_flag import UserFlagMapper
from fanfan.adapters.db.models import UserFlagORM
from fanfan.core.models.user_flag import UserFlag
from fanfan.core.vo.user import UserId


class UserFlagGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = UserFlagMapper()

    async def add_user_flag(self, flag: UserFlag) -> UserFlag:
        flag_orm = self.mapper.from_model(flag)
        self.session.add(flag_orm)
        await self.session.flush([flag_orm])
        return self.mapper.to_model(flag_orm)

    async def get_flag_by_user(
        self, user_id: UserId, flag_name: str
    ) -> UserFlag | None:
        stmt = select(UserFlagORM).where(
            and_(
                UserFlagORM.user_id == user_id,
                UserFlagORM.name == flag_name,
            )
        )
        flag_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(flag_orm) if flag_orm else None

    async def delete_user_flag(self, flag: UserFlag) -> None:
        await self.session.execute(delete(UserFlagORM).where(UserFlagORM.id == flag.id))
