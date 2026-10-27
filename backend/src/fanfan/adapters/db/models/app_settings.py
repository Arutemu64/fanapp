from typing import Any

from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin


class AppSettingsORM(UpdatedAtMixin, BaseORM):
    __tablename__ = "app_settings"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True, server_default="1")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
