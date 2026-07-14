from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM


class AppSettingsORM(BaseORM):
    __tablename__ = "app_settings"
    # Singleton table: the app reads/writes the one row with id=1, so make it
    # impossible to insert a second row that would then be silently ignored.
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True, server_default="1")
    config: Mapped[dict] = mapped_column(JSONB)
