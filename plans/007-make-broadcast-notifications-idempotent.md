# Plan 007: Make broadcast notifications idempotent on redelivery

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update the status row for this plan in `plans/README.md`.
>
> **Read before starting**: `docs/backend.md` "Persistence & Transaction
> Management" and `docs/adr/0004-transactional-outbox-for-domain-events.md`
> (delivery-semantics context). This plan changes production code **and** relies
> on the test harness from Plan 006.
>
> **Drift check (run first)**:
> `git diff --stat 3063e77e..HEAD -- backend/src/fanfan/application/interactors/notifications/process_broadcast.py backend/src/fanfan/application/interactors/notifications/create_notification.py backend/src/fanfan/adapters/db/gateways/notifications.py backend/src/fanfan/application/ports/gateways/notifications.py backend/src/fanfan/core/vo/notification.py`
> If any in-scope file changed since this plan was written, compare the "Current
> state" excerpts against the live code before proceeding; on a mismatch, treat
> it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED (touches the notification delivery pipeline)
- **Depends on**: **006** (needs `tests/integration/notifications/` — do not start
  until 006 is DONE)
- **Category**: correctness (idempotency)
- **Planned at**: commit `3063e77e`, 2026-09-05

## Why this matters

The notification fan-out is **not idempotent under redelivery**, and the
consumers run at-least-once:

- `ProcessBroadcast` mints a **fresh** notification id per user on every run and
  publishes `NotificationQueued` via `EventBroker.publish`, which sets **no**
  `Nats-Msg-Id`. So if the consumer redelivers the broadcast message (a handler
  error, NATS blip, or crash after `set_total` commits), the whole fan-out reruns
  with brand-new ids and **every already-notified user gets a duplicate**.
- `CreateNotification` inserts with a plain `session.add`; a redelivered
  `NotificationQueued` with the same id raises an unmapped `IntegrityError` (PK
  violation) that isn't caught by the consumer's `except MailingAlreadyCancelled`,
  so the message **nacks and redelivers forever** (until JetStream `max_deliver`),
  and `increment_sent` can drift.

The fix makes the broadcast path idempotent end-to-end **at the database level**,
independent of NATS dedup: derive **deterministic** notification ids from
`(mailing_id, user_id)` so a rerun produces identical ids, and make the insert an
**upsert** (`ON CONFLICT (id) DO NOTHING`) that only increments the mailing's
sent-count when a row was actually created. A redelivered `NotificationQueued`
then becomes a clean no-op that acks normally.

## Current state

- `core/vo/notification.py` — ids are random today:

  ```python
  NotificationId = NewType("NotificationId", UUID)

  def generate_notification_id() -> NotificationId:
      return NotificationId(uuid7())
  ```

- `application/interactors/notifications/process_broadcast.py:44-60` — random id
  per user, published without a message id:

  ```python
      events = [
          NotificationQueued(
              notification=NewNotification(
                  id=generate_notification_id(),      # ← random, changes every run
                  user_id=u.id,
                  title="Рассылка от организаторов",
                  body=data.body,
                  path="/notifications",
                  mailing_id=data.mailing_id,
                  type=NotificationType.BROADCAST,
              )
          )
          for u in users
      ]
      for e in events:
          await self.events_broker.publish(e)
  ```

- `application/interactors/notifications/create_notification.py:44-62` — note the
  deliberate lock-ordering comment (lock the mailing row **before** inserting):

  ```python
      async def __call__(self, data: CreateNotificationInput) -> NotificationId:
          mailing_id = data.notification.mailing_id
          notification = self._to_model(data.notification)
          # Lock the mailing row (SELECT ... FOR UPDATE) before inserting ...
          # [deadlock-avoidance comment — PRESERVE IT]
          if mailing_id is not None:
              mailing = await self.mailing_gateway.get(mailing_id)
              if mailing is None:
                  raise MailingNotFound
              mailing.ensure_active()
              await self.mailing_gateway.increment_sent(mailing_id=mailing_id)
          await self.notification_gateway.add(notification)
          await self.uow.commit()
          return notification.id
  ```

- `application/ports/gateways/notifications.py:13` — `async def add(self, notification: Notification) -> None: ...`
- `adapters/db/gateways/notifications.py:61-64` — plain insert:

  ```python
      async def add(self, notification: Notification) -> None:
          notification_orm = _from_model(notification)
          self.session.add(notification_orm)
          await self.session.flush([notification_orm])
  ```

- The consumer (`presentation/faststream/routes/notifications.py:91-119`) acks
  only after `CreateNotification` returns, and its `except` only handles
  `MailingAlreadyCancelled`; any other exception (today, the PK `IntegrityError`)
  propagates → redelivery loop.

## Fix approach (broadcast path only)

1. Add a **deterministic** id helper keyed on `(mailing_id, user_id)`.
2. `ProcessBroadcast` uses it, so a rerun/redelivery produces identical ids.
3. `NotificationGateway.add` becomes an idempotent upsert returning whether a row
   was inserted; `CreateNotification` increments the mailing only when a row was
   inserted, **without changing the mailing-lock-before-insert order**.

**Explicitly out of scope**: `send_schedule_change_notifications.py` (still uses
random ids and also has a separate post-commit dual-write issue — that is a
different finding). The `CreateNotification` upsert added here also protects that
path from duplicate *rows*, but making its ids deterministic + outbox-delivered is
a follow-up. Do **not** attempt it in this plan.

## Commands you will need

| Purpose               | Command                                                                 | Expected |
|-----------------------|------------------------------------------------------------------------|----------|
| Lint                  | `just backend-lint`                                                    | exit 0   |
| Typecheck             | `just backend-typecheck`                                               | exit 0   |
| Notifications tests   | `cd backend && uv run pytest -m integration backend/tests/integration/notifications` | all pass (needs Docker) |
| Unit tests            | `cd backend && uv run pytest -m unit`                                  | all pass |

**Docker required** for the integration verification.

## Scope

**In scope**:
- `backend/src/fanfan/core/vo/notification.py` (add the deterministic helper)
- `backend/src/fanfan/application/interactors/notifications/process_broadcast.py`
- `backend/src/fanfan/application/interactors/notifications/create_notification.py`
- `backend/src/fanfan/application/ports/gateways/notifications.py` (`add` return type)
- `backend/src/fanfan/adapters/db/gateways/notifications.py` (upsert)
- `backend/tests/integration/notifications/` (extend Plan 006's tests)

**Out of scope** (do NOT touch):
- `send_schedule_change_notifications.py`, `cancel_mailing.py` — separate findings.
- `adapters/nats/events_broker.py` — the DB-level idempotency here does not require
  changing `publish` to set `Nats-Msg-Id`. (A JetStream dedup header is a valid
  *additional* optimization but is deliberately deferred — leave `publish` alone.)
- The consumer in `presentation/faststream/routes/notifications.py` — with the
  upsert, `CreateNotification` no longer raises on a duplicate, so the existing
  ack path works; do not change ack policy here.
- The mailing-lock-before-insert ordering and its comment in
  `create_notification.py` — preserve exactly (deadlock avoidance).

## Git workflow

- Branch: `advisor/007-broadcast-idempotency` off `main`.
- One commit; imperative title, e.g.
  `Make broadcast notifications idempotent on redelivery`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add a deterministic notification-id helper

In `core/vo/notification.py`, add a helper that derives a stable id from the
mailing and user, alongside the existing random one (keep `generate_notification_id`
for non-mailing callers):

```python
from uuid import NAMESPACE_URL, UUID, uuid5, uuid7
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserId


def notification_id_for(mailing_id: MailingId, user_id: UserId) -> NotificationId:
    """Deterministic id for a mailing's per-user notification.

    A redelivered fan-out must produce the same ids so the insert can be an
    idempotent no-op instead of a duplicate.
    """
    return NotificationId(uuid5(NAMESPACE_URL, f"notification:{mailing_id}:{user_id}"))
```

Watch for an import cycle: `core/vo/notification.py` importing `core/vo/mailing.py`
and `core/vo/user.py`. If either imports back, use plain `UUID`/`str` typing on
the params to avoid the cycle, and note it. `just backend-lint` (import-linter)
will catch a layering problem.

**Verify**: `just backend-typecheck` → exit 0. `just backend-lint` → exit 0.

### Step 2: Use the deterministic id in `ProcessBroadcast`

Replace `id=generate_notification_id()` with
`id=notification_id_for(data.mailing_id, u.id)` in the event-building
comprehension. Add a one-line English comment on *why* (idempotent redelivery).
Leave the `events_broker.publish` loop as-is.

**Verify**: `just backend-typecheck` → exit 0.

### Step 3: Make the gateway insert an idempotent upsert returning "inserted"

- Change the port: `application/ports/gateways/notifications.py` line 13 to
  `async def add(self, notification: Notification) -> bool: ...` with a one-line
  docstring: returns `True` if a new row was inserted, `False` if it already
  existed.
- Implement in `adapters/db/gateways/notifications.py` using the Postgres dialect
  upsert:

  ```python
  from sqlalchemy.dialects.postgresql import insert as pg_insert

      async def add(self, notification: Notification) -> bool:
          values = {
              "id": notification.id,
              "user_id": notification.user_id,
              "title": notification.title,
              "body": notification.body,
              "type": notification.type,
              "path": notification.path,
              "mailing_id": notification.mailing_id,
              "seen_at": notification.seen_at,
          }
          stmt = (
              pg_insert(NotificationORM)
              .values(**values)
              .on_conflict_do_nothing(index_elements=["id"])
              .returning(NotificationORM.id)
          )
          result = await self.session.scalar(stmt)
          return result is not None
  ```

  Confirm the `on_conflict_do_nothing` + `.returning(...)` shape against current
  SQLAlchemy docs for the pinned version (per AGENTS.md) — `RETURNING` yields no
  row when the conflict skips the insert, which is what makes `result is not None`
  the "was inserted" signal. Verify no other caller of `add` relies on the old
  `None` return (`grep -rn "notification_gateway.add\|\.add(notification" backend/src`).

**Verify**: `just backend-typecheck` → exit 0. `just backend-lint` → exit 0.

### Step 4: Increment the mailing only when a row was inserted

In `create_notification.py`, keep the mailing-lock-before-insert ordering but move
the `increment_sent` to depend on the insert result. Target shape:

```python
    async def __call__(self, data: CreateNotificationInput) -> NotificationId:
        mailing_id = data.notification.mailing_id
        notification = self._to_model(data.notification)
        # Lock the mailing row (SELECT ... FOR UPDATE) before inserting the
        # notification ... [PRESERVE the existing deadlock-avoidance comment]
        mailing = None
        if mailing_id is not None:
            mailing = await self.mailing_gateway.get(mailing_id)
            if mailing is None:
                raise MailingNotFound
            mailing.ensure_active()
        inserted = await self.notification_gateway.add(notification)
        # Only count a genuinely new notification: a redelivered NotificationQueued
        # re-runs this with the same id, and the upsert above no-ops it.
        if inserted and mailing_id is not None:
            await self.mailing_gateway.increment_sent(mailing_id=mailing_id)
        await self.uow.commit()
        return notification.id
```

Keep the mailing `get` (FOR UPDATE) **before** `add` so the lock order is
unchanged. Return `notification.id` unconditionally (the caller wants the id
whether or not it was freshly inserted).

**Verify**: `just backend-typecheck` → exit 0. `just backend-lint` → exit 0.

### Step 5: Add the idempotency regression tests

Extend Plan 006's `test_process_broadcast.py` and add/extend a
`create_notification` test in `backend/tests/integration/notifications/`:

1. **Deterministic ids**: running `ProcessBroadcast` twice for the same mailing
   produces the **same** set of notification ids (assert on the recorded
   `FakeEventBroker` events across two runs).
2. **Idempotent create**: calling `CreateNotification` twice with the same
   `NewNotification` (same id + `mailing_id`) results in exactly **one** row and
   `sent_count` incremented **once** (read the mailing back and assert its
   `sent_count`). This is the core regression: the second call is a clean no-op,
   not an `IntegrityError`.

Model on `voting/test_add_vote.py` / the Plan 006 notification tests. Resolve the
interactors and gateways from `dishka_request`.

**Verify**:
`cd backend && uv run pytest -m integration backend/tests/integration/notifications`
→ all pass, including the two new assertions.

## Test plan

- Extend the Plan 006 notification tests with the two cases in Step 5
  (deterministic ids; idempotent create with single increment).
- Patterns: the Plan 006 tests and `voting/test_add_vote.py`.
- Verification: the notifications integration subset runs green with Docker.

## Done criteria

ALL must hold:

- [ ] `just backend-typecheck` exits 0; `just backend-lint` exits 0 (import-linter
      green — no new layering violation from the VO helper)
- [ ] `cd backend && uv run pytest -m unit` exits 0
- [ ] `ProcessBroadcast` uses `notification_id_for(mailing_id, user_id)` (not a
      random id)
- [ ] `NotificationGateway.add` returns `bool` and the SQL is an
      `ON CONFLICT (id) DO NOTHING` upsert
- [ ] `CreateNotification` increments the mailing only when the insert created a
      row, and the mailing FOR-UPDATE lock still precedes the insert (comment
      preserved)
- [ ] New tests prove: two `ProcessBroadcast` runs → identical ids; two
      `CreateNotification` calls with the same id → one row, one increment; and
      `cd backend && uv run pytest -m integration backend/tests/integration/notifications` passes
- [ ] `send_schedule_change_notifications.py`, `events_broker.py`, and the
      faststream consumer are unchanged (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Plan 006 is not yet DONE (this plan needs its test harness).
- No Docker daemon is available (can't verify).
- Adding `notification_id_for` creates an import cycle that import-linter flags
  and can't be resolved by loosening the param types — report it.
- A caller of `notification_gateway.add` other than `CreateNotification` relies on
  the old `None` return — report it before changing the signature.
- The pinned SQLAlchemy version's `on_conflict_do_nothing(...).returning(...)`
  doesn't behave as "no row on conflict" — report; do not fall back to a
  select-then-insert (that reintroduces a race).

## Maintenance notes

- Follow-up (separate plan, ties to the "post-commit direct publish bypasses the
  outbox" finding): make `send_schedule_change_notifications` ids deterministic
  and route its trigger through the outbox, then it inherits the same idempotency.
- An optional further hardening is setting `Nats-Msg-Id` on `EventBroker.publish`
  so JetStream dedups within its window — deferred because the DB-level upsert
  already guarantees correctness; add it only with its own reasoning.
- A reviewer should confirm the mailing lock still precedes the insert (deadlock
  avoidance) and that `sent_count` can never exceed `total_count` after a
  redelivery.
