from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM


class AppSettingsORM(BaseORM):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, server_default="1")
    config: Mapped[dict] = mapped_column(JSONB)
