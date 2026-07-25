from fanfan.adapters.db.models import SyncRunORM
from fanfan.application.dto.sync import SyncRunDTO
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import SyncRunId
from fanfan.core.vo.user import UserId


class SyncRunMapper:
    @staticmethod
    def from_model(model: SyncRun) -> SyncRunORM:
        return SyncRunORM(
            id=model.id,
            source=model.source,
            status=model.status,
            by_user_id=model.by_user_id,
            started_at=model.started_at,
            finished_at=model.finished_at,
            result=model.result,
            error=model.error,
        )

    @staticmethod
    def to_model(orm: SyncRunORM) -> SyncRun:
        return SyncRun(
            id=SyncRunId(orm.id),
            source=orm.source,
            status=orm.status,
            by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
            started_at=orm.started_at,
            finished_at=orm.finished_at,
            result=orm.result,
            error=orm.error,
        )

    @staticmethod
    def parse_dto(orm: SyncRunORM) -> SyncRunDTO:
        return SyncRunDTO(
            id=SyncRunId(orm.id),
            source=orm.source,
            status=orm.status,
            started_at=orm.started_at,
            finished_at=orm.finished_at,
            result=orm.result,
            error=orm.error,
        )
