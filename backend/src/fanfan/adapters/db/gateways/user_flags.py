from typing import override

from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import UserFlagORM
from fanfan.application.ports.gateways.user_flags import UserFlagGateway
from fanfan.core.models.user_flag import UserFlag
from fanfan.core.vo.user import UserId
from fanfan.core.vo.user_flag import UserFlagId, UserFlagName


def _from_model(model: UserFlag) -> UserFlagORM:
    return UserFlagORM(
        id=model.id,
        name=model.name,
        user_id=model.user_id,
    )


def _to_model(orm: UserFlagORM) -> UserFlag:
    return UserFlag(
        id=UserFlagId(orm.id),
        name=UserFlagName(orm.name),
        user_id=UserId(orm.user_id),
    )


class SqlUserFlagGateway(UserFlagGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def add(self, flag: UserFlag) -> None:
        flag_orm = _from_model(flag)
        stmt = (
            insert(UserFlagORM)
            .values(id=flag_orm.id, name=flag_orm.name, user_id=flag_orm.user_id)
            .on_conflict_do_nothing(index_elements=["user_id", "name"])
        )
        await self.session.execute(stmt)

    @override
    async def get_by_user(
        self, user_id: UserId, flag_name: UserFlagName
    ) -> UserFlag | None:
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
        return _to_model(flag_orm) if flag_orm else None

    @override
    async def delete(self, flag: UserFlag) -> None:
        await self.session.execute(delete(UserFlagORM).where(UserFlagORM.id == flag.id))
