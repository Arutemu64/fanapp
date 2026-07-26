---
name: fanfan-migrations
description: Generating and reviewing Alembic migrations in this repo. Use when adding or changing a SQLAlchemy model under backend/src/fanfan/adapters/db/models/, writing or reviewing a migration under adapters/db/migrations/versions/, adding a member to an enum backed by a database column (Permission, UserRole, UserFlagName, ...), or when the model-drift check fails.
paths:
  - "backend/src/fanfan/adapters/db/models/**"
  - "backend/src/fanfan/adapters/db/migrations/**"
---

# FAN FAN migrations

## Commands

| Command | Use |
| --- | --- |
| `just backend-generate <name>` | Autogenerate against the running app DB |
| `just backend-generate-auto <name>` | Autogenerate against a throwaway Postgres 18 (needs Docker, no app DB). **Use this in Claude Code on the web.** |
| `just backend-migrate` | Apply (`alembic upgrade head`) |
| `just backend-check-migrations` | Fail if ORM models drift from migrations |

Prefer autogenerate over hand-writing, then **always read the generated file
before committing**. The three things autogenerate gets wrong here are below.

## 1. Renames come out as drop + create

Autogenerate diffs schemas, not intent, so a renamed column or table is emitted
as `drop_column` + `add_column` — silent data loss. Rewrite those by hand as
`op.alter_column(..., new_column_name=...)` / `op.rename_table(...)`.

Renaming a **table** also means renaming its constraints, indexes and sequence
so they stay consistent with the `naming_convention` in
`adapters/db/models/base.py`. `2026_07_15_0720-d4e5f6a7b8c9_model_convention_cleanup.py`
is the worked example.

## 2. Enum members need a hand-written CHECK constraint swap

**This project uses no native PostgreSQL `ENUM` types.** `str_enum_column()`
(`adapters/db/models/base.py`) maps every `StrEnum` to a `VARCHAR` guarded by a
CHECK constraint — `native_enum=False`, because a CHECK is far cheaper to evolve
than `ALTER TYPE ... ADD VALUE`. It stores the enum **value** (`"visitor"`), not
the member name, via `values_callable`, so the database matches the API, DTOs and
frontend.

Alembic does not diff CHECK constraint bodies, so **adding or removing an enum
member produces an empty migration**. Write the swap by hand — drop the
constraint, recreate it with the new member list, and mirror it in `downgrade`.
Copy `2026_07_17_0800-a1b2c3d4e5f6_add_tickets_generate_permission.py`; it spells
the member list out in module-level constants so the diff shows exactly what
changed.

Adding a `Permission` member is this case. It is also only half the job: a
permission grants nothing until a `user_permissions` row exists, so an
unattended interactor's permission needs a data migration granting it to the
system user (`00000000-…-0000`). See `sync:run` and
`tests/integration/sync/test_execute_sync.py`.

## 3. Server defaults

`compare_type` is on, so column **type** drift is detected. Changed
`server_default`s are not reliably detected and are sometimes emitted wrong —
check them by hand.

## Reviewing safety

`sqlalchemy-alembic-expert-best-practices-code-review` covers the general safety
rules: concurrent index creation, `NOT VALID` foreign keys and check constraints,
multi-step column type changes. Its zero-downtime rules are worth following for
anything touching a large or hot table (`users`, `tickets`, `notifications`);
this is a single-instance deployment updated by `just deploy`, so a brief lock on
a small table is acceptable and the multi-step dance is not mandatory.

## Before calling it done

`just backend-lint`, `just backend-typecheck`, and `just backend-check-migrations`
to confirm the models and the migration chain agree. A migration that has been
applied to a deployed database is immutable — fix it forward with a new revision.
