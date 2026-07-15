from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    },
)


def str_enum_column(
    enum_cls: type[PyEnum],
    *,
    name: str,
    length: int = 32,
    **kwargs: Any,
) -> MappedColumn:
    """Map a StrEnum to a VARCHAR column guarded by a CHECK constraint.

    We deliberately avoid a native PostgreSQL ENUM type (``native_enum=False``):
    a CHECK constraint is far cheaper to evolve than ``ALTER TYPE ... ADD VALUE``.
    We store the enum *value* ("visitor"), not the member name, via
    ``values_callable`` so the DB matches the value used across the API, DTOs and
    frontend — both for the stored data and the generated CHECK constraint.

    Extra ``kwargs`` (``default``, ``server_default``, ``index``, ...) pass
    through to ``mapped_column``.
    """
    return mapped_column(
        Enum(
            enum_cls,
            native_enum=False,
            create_constraint=True,
            name=name,
            length=length,
            values_callable=lambda cls: [m.value for m in cls],
        ),
        **kwargs,
    )


class BaseORM(DeclarativeBase):
    """Declarative base carrying the shared metadata and the ``created_at`` audit
    column.

    ``created_at`` is universal — knowing when a row was inserted is useful on
    every table. ``updated_at`` is opt-in via ``UpdatedAtMixin`` (mixins/
    timestamps.py), applied only to tables that actually receive UPDATEs.
    """

    metadata = metadata

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        pk = self.__mapper__.primary_key_from_instance(self)
        pk_repr = ", ".join(map(repr, pk))
        return f"<{type(self).__name__}({pk_repr})>"
