from sqlalchemy import Sequence, UniqueConstraint
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class OrderMixin:
    """Adds a deferred-unique float ``order`` column so rows (e.g. schedule
    events) can be reordered — and swapped within a single transaction —
    without violating uniqueness during intermediate flushes.

    Each table gets its own ``<table>_order_seq`` sequence. Alembic does NOT
    autogenerate sequences, so create it by hand in the migration. The order
    column default references the sequence, so create it BEFORE create_table::

        # upgrade(), before create_table:
        op.execute("CREATE SEQUENCE schedule_events_order_seq START 1")
        # downgrade(), after drop_table:
        op.execute("DROP SEQUENCE schedule_events_order_seq")

    IMPORTANT: a model that declares its OWN ``__table_args__`` must merge in
    ``order_table_args()`` explicitly — SQLAlchemy does not merge
    ``__table_args__`` across a mixin and its subclass; the subclass shadows
    the mixin. Models with no other table args inherit the constraint below
    automatically.
    """

    # Hint for the type checker; each concrete model overrides it with its own
    # table name, which is what `order` reads at runtime to name the sequence.
    __tablename__ = None

    @declared_attr
    def order(cls) -> Mapped[float]:
        order_sequence = Sequence(f"{cls.__tablename__}_order_seq", start=1)
        return mapped_column(
            nullable=False,
            server_default=order_sequence.next_value(),
        )

    # Auto-applied to orderable models that declare NO other table args.
    @declared_attr.directive
    def __table_args__(cls) -> tuple:
        return cls.order_table_args()

    @staticmethod
    def order_table_args() -> tuple:
        # Deferred so a transaction can swap two rows' order values without
        # tripping the unique constraint on an intermediate flush.
        return (UniqueConstraint("order", deferrable=True, initially="DEFERRED"),)
