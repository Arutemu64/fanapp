"""key social identities on the OIDC subject, not the provider's native user id

``social_identities.provider_id`` held Telegram's Bot API user id and served two
jobs at once: the identity matched on at login, and the ``chat_id`` the notifier
sends to. They are different values — Telegram's own sample token pairs
``id: 987654321`` with ``sub: "1234123412341234123"`` — so this splits them:

* ``subject`` (renamed from ``provider_id``) is the OIDC ``sub``, the identity
  key. It is what ``claims_supported`` actually advertises, and it survives the
  bot being switched to EdDSA/ES256K signing in BotFather, which strips the
  ``profile`` scope that carries ``id``.
* ``provider_user_id`` is the Bot API id, kept only as a delivery address, and
  nullable because an ``openid``-only token carries none.

``provider`` becomes an enum-backed VARCHAR with a CHECK constraint, in
preparation for a second provider. Alembic does not diff CHECK bodies, so that
half is hand-written.

**This migration deletes every existing row.** ``sub`` cannot be derived from a
Bot API id offline, so stored identities cannot be carried across; leaving them
would silently strand each account and mint a duplicate user on its owner's next
login. The app is pre-production and the table holds no real data — if that ever
stops being true, this needs replacing with a lazy backfill (match on subject,
fall back to the legacy id, write the subject back on first login).

Revision ID: b4d81f2ac907
Revises: c6ebdce7e2cc
Create Date: 2026-07-31 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4d81f2ac907"
down_revision = "c6ebdce7e2cc"
branch_labels = None
depends_on = None

_TABLE = "social_identities"
_PROVIDER_CONSTRAINT = "ck_social_identities_social_provider"
_PROVIDERS = ["telegram"]


def upgrade() -> None:
    # No row can be migrated (see the module docstring), and the unique
    # constraint below would otherwise be enforced against stale values.
    op.execute(sa.table(_TABLE).delete())

    # Renamed, not dropped and recreated: autogenerate emits renames as
    # drop+create, which would lose the column outright.
    op.alter_column(_TABLE, "provider_id", new_column_name="subject")

    op.add_column(_TABLE, sa.Column("provider_user_id", sa.BigInteger(), nullable=True))
    op.add_column(
        _TABLE,
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.alter_column(
        _TABLE,
        "provider",
        existing_type=sa.String(),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.create_check_constraint(
        op.f(_PROVIDER_CONSTRAINT),
        _TABLE,
        sa.column("provider").in_(_PROVIDERS),
    )


def downgrade() -> None:
    op.drop_constraint(op.f(_PROVIDER_CONSTRAINT), _TABLE, type_="check")
    op.alter_column(
        _TABLE,
        "provider",
        existing_type=sa.String(length=32),
        type_=sa.String(),
        existing_nullable=False,
    )
    op.drop_column(_TABLE, "updated_at")
    op.drop_column(_TABLE, "provider_user_id")
    op.alter_column(_TABLE, "subject", new_column_name="provider_id")
