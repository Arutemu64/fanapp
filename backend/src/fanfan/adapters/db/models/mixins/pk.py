from uuid import UUID, uuid7

from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Adds a time-ordered UUIDv7 primary key.

    uuid7 is generated app-side (not via a DB default) so freshly inserted rows
    stay roughly index-ordered — unlike random uuid4 — giving good B-tree
    locality without a server round-trip. The bare ``Mapped[UUID]`` annotation
    resolves to SQLAlchemy's ``Uuid`` type, which is a native ``UUID`` column on
    PostgreSQL.

    The column name is given explicitly ("id") rather than left to be inferred
    from the attribute key. A same-class ``column_property`` can reference
    ``cls.id`` while the mapping is still being built (e.g. ScheduleEventORM.queue
    correlates a subquery on it); an inferred name isn't assigned yet at that
    point, which would raise "Cannot initialize a sub-selectable ... until its
    'name' has been assigned". An explicit name sidesteps the ordering entirely.
    """

    id: Mapped[UUID] = mapped_column("id", primary_key=True, default=uuid7)
