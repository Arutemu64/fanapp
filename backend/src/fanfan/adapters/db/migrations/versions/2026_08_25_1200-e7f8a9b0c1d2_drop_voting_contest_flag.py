"""drop voting_contest user flag

Removes the only ``UserFlagName`` member, ``voting_contest``. The prize-draw pool
is now computed on demand from the votes table, so the materialised flag is gone.

The user-flag system (table, gateway, empty enum) is kept for future markers, so
the CHECK constraint is recreated in its empty form — ``Enum(UserFlagName)`` with
no members renders ``name IN (NULL) AND (1 != 1)``, rejecting every value until a
new member re-populates the list — rather than dropped. Alembic does not diff
CHECK bodies, so this swap is hand-written.

Revision ID: e7f8a9b0c1d2
Revises: 0c1c3b98ba5e
Create Date: 2026-08-25 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e7f8a9b0c1d2"
down_revision = "0c1c3b98ba5e"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_user_flags_userflagname"
_TABLE = "user_flags"
_COLUMN = "name"
_PREVIOUS = ("voting_contest",)


def upgrade() -> None:
    # The flag is meaningless now; drop the rows so the tightened constraint,
    # which rejects every value, can be applied.
    op.execute(sa.text("DELETE FROM user_flags WHERE name = 'voting_contest'"))
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_([]),
    )


def downgrade() -> None:
    # Deleted voting_contest rows are not restored — the flag is derivable from
    # votes, so re-materialising it is out of scope for a schema downgrade.
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_(_PREVIOUS),
    )
