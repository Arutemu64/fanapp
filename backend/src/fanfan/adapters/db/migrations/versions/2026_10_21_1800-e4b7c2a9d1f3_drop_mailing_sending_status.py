"""drop mailing sending status and sent_count

The fan-out finishes a mailing in the transaction that stores its last
notification, so a mailing goes straight from ``pending`` to ``finished`` and no
per-notification ``sent_count`` is kept. A ``sending`` row is a fan-out that was
running when this ran; nothing finishes it any more, so it becomes ``finished``,
the state its fan-out was about to reach. The status column is a VARCHAR guarded
by a CHECK constraint (``native_enum=False``), so dropping a member is a
hand-written constraint swap.

Revision ID: e4b7c2a9d1f3
Revises: c3d9e1f2a4b6
Create Date: 2026-10-21 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e4b7c2a9d1f3"
down_revision = "c3d9e1f2a4b6"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_mailings_mailingstatus"
_TABLE = "mailings"
_COLUMN = "status"

_KEPT = ["pending", "finished", "cancelled", "failed"]
_DROPPED = "sending"


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE mailings SET status = 'finished' WHERE status = :dropped"
        ).bindparams(dropped=_DROPPED)
    )
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_(_KEPT),
    )
    op.drop_column(_TABLE, "sent_count")


def downgrade() -> None:
    # The counts are gone: every mailing comes back with sent_count 0, and a
    # mailing moved from sending to finished stays finished.
    op.add_column(
        _TABLE,
        sa.Column(
            "sent_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
    )
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_([*_KEPT, _DROPPED]),
    )
