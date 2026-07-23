from fanfan.adapters.db.models import SyncRunORM
from fanfan.application.dto.sync import SyncRunDTO, SyncRunUserDTO
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import SyncRunId
from fanfan.core.vo.user import UserId


class SyncRunMapper:
    @staticmethod
    def from_model(model: SyncRun) -> SyncRunORM:
        return SyncRunORM(
            id=model.id,
            source=model.source,
            trigger=model.trigger,
            status=model.status,
            started_by_user_id=model.started_by_user_id,
            started_at=model.started_at,
            finished_at=model.finished_at,
            error_message=model.error_message,
        )

    @staticmethod
    def to_model(orm: SyncRunORM) -> SyncRun:
        return SyncRun(
            id=SyncRunId(orm.id),
            source=orm.source,
            trigger=orm.trigger,
            status=orm.status,
            started_by_user_id=UserId(orm.started_by_user_id)
            if orm.started_by_user_id is not None
            else None,
            started_at=orm.started_at,
            finished_at=orm.finished_at,
            error_message=orm.error_message,
        )

    @staticmethod
    def parse_dto(orm: SyncRunORM) -> SyncRunDTO:
        return SyncRunDTO(
            id=SyncRunId(orm.id),
            source=orm.source,
            trigger=orm.trigger,
            status=orm.status,
            started_at=orm.started_at,
            finished_at=orm.finished_at,
            error_message=orm.error_message,
            started_by=SyncRunUserDTO(
                id=UserId(orm.started_by.id),
                username=orm.started_by.username,
            )
            if orm.started_by
            else None,
        )
