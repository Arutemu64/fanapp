# Plan 005: Enforce one-vote-per-nomination at the database, closing the concurrent double-vote gap

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update the status row for this plan in `plans/README.md`.
>
> **Load these skills before you start** (per AGENTS.md, working on ORM models /
> migrations): `fanfan-migrations` and
> `sqlalchemy-alembic-expert-best-practices-code-review`. Read
> `docs/backend.md` "Persistence & Transaction Management".
>
> **Drift check (run first)**:
> `git diff --stat 3063e77e..HEAD -- backend/src/fanfan/adapters/db/models/vote.py backend/src/fanfan/adapters/db/gateways/votes.py backend/src/fanfan/application/interactors/voting/add_vote.py`
> If any in-scope file changed since this plan was written, compare the "Current
> state" excerpts against the live code before proceeding; on a mismatch, treat
> it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (schema change + migration)
- **Depends on**: none
- **Category**: correctness (voting integrity)
- **Planned at**: commit `3063e77e`, 2026-09-05

## Why this matters

The "one vote per nomination" rule is enforced **only** by an application-layer
check-then-act, with **no database backstop**. `AddVote` reads
`get_user_vote_by_nomination(...)`; if it returns `None` it inserts a vote. But
the `SELECT ... FOR UPDATE` in that read locks nothing when no row exists (you
cannot lock a row that isn't there — a phantom), so two near-simultaneous
requests from one user for two *different* participants in the *same* nomination
both see `None` and both commit. Under READ COMMITTED that yields **two votes in
one nomination**, inflating two participants' tallies — a voting-integrity defect
on the very feature the contest exists for. The only DB constraint today is
`(user_id, participant_id)`, which catches an *exact* duplicate participant but
never a second participant in the same nomination.

The reliable fix is a DB `UNIQUE (user_id, nomination_id)` constraint so the
second concurrent insert fails atomically and is mapped to the existing
`VoteAlreadyExists` domain error. We denormalise `nomination_id` onto the `votes`
table **at the persistence layer only** (a unique constraint can't span a join),
keeping the core `Vote` domain model and all its construction sites unchanged.

## Current state

- `backend/src/fanfan/application/interactors/voting/add_vote.py:53-69` — the
  check-then-act (leave the app-level check as the fast path; the DB constraint
  is the backstop):

  ```python
      participant = await self.participant_gateway.get(data.participant_id)
      if participant is None:
          raise ParticipantNotFound

      # One vote per nomination, not per participant: the participant is
      # resolved above only to read the nomination it competes in.
      if await self.vote_gateway.get_user_vote_by_nomination(
          nomination_id=participant.nomination_id, user_id=current_user.id
      ):
          raise VoteAlreadyExists

      vote = Vote.create(
          user_id=current_user.id,
          participant_id=data.participant_id,
      )
      await self.vote_gateway.add(vote)
      await self.uow.commit()
  ```

- `backend/src/fanfan/adapters/db/models/vote.py` — the ORM model today:

  ```python
  class VoteORM(UUIDPrimaryKeyMixin, BaseORM):
      __tablename__ = "votes"
      __table_args__ = (UniqueConstraint("user_id", "participant_id"),)

      user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
      participant_id: Mapped[UUID] = mapped_column(
          ForeignKey("participants.id", ondelete="CASCADE"), index=True
      )

      participant: Mapped[ParticipantORM] = relationship()
      nomination: Mapped[NominationORM] = relationship(
          secondary="participants",
          viewonly=True,
      )
  ```

- `backend/src/fanfan/adapters/db/gateways/votes.py` — relevant parts:

  ```python
  def _from_model(model: Vote) -> VoteORM:
      return VoteORM(
          id=model.id,
          user_id=model.user_id,
          participant_id=model.participant_id,
      )
  # ...
      async def add(self, vote: Vote) -> None:
          vote_orm = _from_model(vote)
          with translate_integrity_error(
              {
                  "fk_votes_participant_id_participants": ParticipantNotFound,
                  "uq_votes_user_id": VoteAlreadyExists,
              }
          ):
              self.session.add(vote_orm)
              await self.session.flush([vote_orm])
          self.uow.register(vote)
  # ...
      async def get_user_vote_by_nomination(
          self, nomination_id: NominationId, user_id: UserId
      ) -> Vote | None:
          vote_orm = await self.session.scalar(
              select(VoteORM)
              .where(
                  and_(
                      VoteORM.user_id == user_id,
                      VoteORM.nomination.has(NominationORM.id == nomination_id),
                  ),
              )
              .with_for_update()
          )
          ...
  ```

- The core `Vote` model (`backend/src/fanfan/core/models/vote.py`) carries
  `id`, `user_id`, `participant_id` only. **It stays unchanged** — `nomination_id`
  is a persistence denormalisation, not domain state. This keeps the ~7 existing
  `Vote(...)` / `Vote.create(...)` construction sites (unit `test_vote.py`,
  integration voting tests) working untouched.
- `ParticipantORM.nomination_id` (`adapters/db/models/participant.py:31-33`) is
  the FK to `nominations` — the source of truth this plan copies onto votes.
- The existing `(user_id, participant_id)` unique constraint is surfaced under the
  name `uq_votes_user_id` (see the gateway mapping). Keep it — it is harmless and
  subsumed by the new one; the new constraint is what fixes the bug.

## Fix approach

1. Add a non-null `nomination_id` FK column to `votes` and a **named** unique
   constraint `uq_votes_user_nomination` on `(user_id, nomination_id)`.
2. Populate `nomination_id` in the gateway's `add()` from the participant (one
   scalar subquery — the interactor's domain model doesn't carry it, and this
   keeps `Vote` pure).
3. Map the new constraint name to `VoteAlreadyExists`.
4. Point `get_user_vote_by_nomination` at the new direct column.
5. Autogenerate + review the migration (Docker required).

Since the app is **pre-production (no real users)**, no data backfill/migration
for existing rows is required (see the app-pre-production note in the repo's
memory / AGENTS.md philosophy). The autogenerate step runs against a throwaway
empty Postgres, so the non-null column adds cleanly.

## Commands you will need

| Purpose               | Command                                                        | Expected on success |
|-----------------------|---------------------------------------------------------------|---------------------|
| Lint                  | `just backend-lint`                                           | exit 0              |
| Typecheck             | `just backend-typecheck`                                      | exit 0, no errors   |
| Autogenerate migration| `just backend-generate-auto add_votes_nomination_uniqueness`  | writes a new file under `backend/src/fanfan/adapters/db/migrations/versions/` (needs Docker) |
| Migration drift check | `just backend-check-migrations`                              | passes (needs Docker) |
| Voting integration    | `cd backend && uv run pytest -m integration backend/tests/integration/voting/` | all pass (needs Docker) |

**Docker is required** for the migration and integration steps (testcontainers
Postgres). If no Docker daemon is available, STOP and report — this plan cannot
be completed or verified without it.

## Scope

**In scope**:
- `backend/src/fanfan/adapters/db/models/vote.py`
- `backend/src/fanfan/adapters/db/gateways/votes.py`
- One new migration under `backend/src/fanfan/adapters/db/migrations/versions/`
  (generated, then reviewed/edited by hand only to fix an autogen miss)
- `backend/tests/integration/voting/test_add_vote.py` (add the DB-backstop test)

**Out of scope** (do NOT touch):
- `backend/src/fanfan/core/models/vote.py` — the domain model stays pure; do NOT
  add `nomination_id` to it (that would ripple into every `Vote(...)` test site
  and the `VoteCreated` event for no benefit).
- `backend/src/fanfan/application/interactors/voting/add_vote.py` — the app-level
  check stays exactly as-is as the fast path; the fix is the DB backstop.
- The existing `(user_id, participant_id)` constraint and its `uq_votes_user_id`
  mapping — keep both.
- **Never hand-write the migration from scratch** — always `just backend-generate-auto`,
  then review/adjust (repo rule: migrations are autogen-only).

## Git workflow

- Branch: `advisor/005-vote-nomination-uniqueness` off `main`.
- Commit the code changes and the reviewed migration together; imperative title,
  e.g. `Enforce one vote per nomination with a DB unique constraint`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the column, FK, and named unique constraint to the ORM

Edit `adapters/db/models/vote.py`. Add a non-null `nomination_id` FK to
`nominations`, add the named unique constraint, and replace the `secondary`
view-only `nomination` relationship with a direct relationship on the new FK (so
there is one unambiguous path). Target shape:

```python
class VoteORM(UUIDPrimaryKeyMixin, BaseORM):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("user_id", "participant_id"),
        # One vote per nomination per user, enforced in the DB: the app-level
        # check in AddVote can race (its FOR UPDATE locks nothing when no vote
        # exists yet), so this constraint is the real backstop against a
        # concurrent double-vote across two participants in the same nomination.
        UniqueConstraint("user_id", "nomination_id", name="uq_votes_user_nomination"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    # Denormalised from the participant so a unique constraint can enforce the
    # per-nomination rule (a constraint cannot span the participants join).
    nomination_id: Mapped[UUID] = mapped_column(
        ForeignKey("nominations.id", ondelete="CASCADE"), index=True
    )

    participant: Mapped[ParticipantORM] = relationship()
    nomination: Mapped[NominationORM] = relationship()
```

Confirm with the `sqlalchemy-alembic-expert-best-practices-code-review` skill that
a single direct FK relationship named `nomination` is unambiguous here (no
`foreign_keys=`/`overlaps=` needed) given `participant` is a separate FK.

**Verify**: `just backend-typecheck` → exit 0.

### Step 2: Populate and enforce in the gateway

Edit `adapters/db/gateways/votes.py`:

- In `add()`, set `vote_orm.nomination_id` from the participant before flush, via
  a scalar subquery, and add the new constraint to the `translate_integrity_error`
  mapping:

  ```python
      async def add(self, vote: Vote) -> None:
          vote_orm = _from_model(vote)
          # Denormalise the nomination from the participant so the DB can enforce
          # one vote per nomination; the domain Vote doesn't carry it.
          vote_orm.nomination_id = await self.session.scalar(
              select(ParticipantORM.nomination_id).where(
                  ParticipantORM.id == vote.participant_id
              )
          )
          with translate_integrity_error(
              {
                  "fk_votes_participant_id_participants": ParticipantNotFound,
                  "uq_votes_user_id": VoteAlreadyExists,
                  "uq_votes_user_nomination": VoteAlreadyExists,
              }
          ):
              self.session.add(vote_orm)
              await self.session.flush([vote_orm])
          self.uow.register(vote)
  ```

  Import `ParticipantORM` from `fanfan.adapters.db.models`. If the subquery
  returns `None` (participant does not exist), the FK insert would fail anyway;
  the existing `ParticipantNotFound` mapping covers it — do not add extra handling.

- Point `get_user_vote_by_nomination` at the direct column instead of the join:

  ```python
      async def get_user_vote_by_nomination(
          self, nomination_id: NominationId, user_id: UserId
      ) -> Vote | None:
          vote_orm = await self.session.scalar(
              select(VoteORM)
              .where(
                  and_(
                      VoteORM.user_id == user_id,
                      VoteORM.nomination_id == nomination_id,
                  ),
              )
              .with_for_update()
          )
          if vote_orm is None:
              return None
          vote = _to_model(vote_orm)
          self.uow.register(vote)
          return vote
  ```

  `NominationORM` may become an unused import after this — remove it if so (lint
  will flag it).

Leave `_from_model` / `_to_model` unchanged (the core `Vote` has no
`nomination_id`).

**Verify**: `just backend-typecheck` → exit 0. `just backend-lint` → exit 0.

### Step 3: Autogenerate and review the migration

Run `just backend-generate-auto add_votes_nomination_uniqueness`. Open the
generated file and confirm it: adds the `nomination_id` column (non-null) with the
FK to `nominations` and its index, and adds the `uq_votes_user_nomination` unique
constraint. Autogenerate emits renames as drop+create and misses enum changes —
neither applies here, but still read it. Fix any autogen miss by hand
(consult `fanfan-migrations`). Do not leave an empty or partial migration.

**Verify**: `just backend-check-migrations` → passes (the ORM↔migration drift
guard). This needs Docker.

### Step 4: Add the DB-backstop regression test

In `backend/tests/integration/voting/test_add_vote.py`, add a test that proves
the **database** rejects a second vote in the same nomination even when the
app-level check is bypassed (i.e. simulating the concurrency race). Model it on
the existing `test_add_vote_twice_in_same_nomination_raises_already_voted` in the
same file, but drive the gateway directly:

- create one nomination + two participants (as that test does),
- `await vote_gateway.add(Vote.create(user_id=..., participant_id=first.id))`,
- `await uow.commit()`,
- then `await vote_gateway.add(Vote.create(user_id=..., participant_id=second.id))`
  and assert it raises `VoteAlreadyExists` (this is the constraint firing, not the
  app-level check — the gateway `add` is called directly).

Use `visitor_with_ticket`, `login`, `outbox`, `uow` fixtures and resolve
`VoteGateway`, `NominationGateway`, `ParticipantGateway` from `dishka_request`, as
the surrounding tests do.

**Verify**:
`cd backend && uv run pytest -m integration backend/tests/integration/voting/` →
all pass, including the new test and the untouched existing ones.

## Test plan

- New test in `test_add_vote.py` (Step 4): the DB constraint rejects a second
  vote for a different participant in the same nomination — the exact regression.
- Existing voting integration tests must still pass unchanged (they construct
  `Vote(...)` directly and go through `get_user_vote_by_nomination`, both of which
  keep working).
- Structural pattern: the existing tests in
  `backend/tests/integration/voting/test_add_vote.py`.
- Verification: the two integration commands above, plus
  `just backend-check-migrations`. Prefer CI only if you lack Docker — but note
  this plan's core verification (migration + constraint) **requires** Docker, so
  running it locally is expected here.

## Done criteria

ALL must hold:

- [ ] `just backend-typecheck` exits 0
- [ ] `just backend-lint` exits 0 (no unused `NominationORM` import left behind)
- [ ] A reviewed migration adds `votes.nomination_id` (FK, non-null, indexed) and
      the `uq_votes_user_nomination` unique constraint
- [ ] `just backend-check-migrations` passes
- [ ] `cd backend && uv run pytest -m integration backend/tests/integration/voting/`
      passes, including the new DB-backstop test
- [ ] The core `Vote` model and `add_vote.py` interactor are unchanged
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- No Docker daemon is available (the migration and integration steps can't run).
- The "Current state" excerpts don't match the live code (drift).
- SQLAlchemy raises a relationship-ambiguity error after Step 1 (two FKs to
  resolve) — report it; do not guess `foreign_keys=`/`overlaps=` without the
  `sqlalchemy-alembic-expert-best-practices-code-review` skill's guidance.
- `just backend-generate-auto` produces an empty migration or one that also drops
  unrelated objects — do not apply it; report what it emitted.
- Applying the migration fails because a local dev DB already holds `votes` rows
  (a non-null column add on a populated table) — pre-production, the fix is to
  reset that dev DB, but confirm with the operator rather than deleting data.

## Maintenance notes

- If a future feature ever allows multiple votes per nomination (ranked/approval
  voting), this constraint is the thing to revisit — it is the single source of
  the one-vote rule now.
- A reviewer should confirm: the new constraint name matches the
  `translate_integrity_error` mapping exactly (a name mismatch silently degrades
  to a re-raised `IntegrityError` instead of `VoteAlreadyExists`), and the
  `nomination_id` subquery in `add()` can't insert a NULL.
- The app-level `get_user_vote_by_nomination` check remains as a fast path so the
  common (sequential) double-vote returns a clean `VoteAlreadyExists` without
  hitting the constraint; the constraint only catches the concurrent race.
