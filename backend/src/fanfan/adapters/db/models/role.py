from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM


class RoleORM(BaseORM):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str] = mapped_column(unique=True)
