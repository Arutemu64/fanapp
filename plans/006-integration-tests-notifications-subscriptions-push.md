# Plan 006: Add integration coverage for the notifications, subscriptions, and push domains

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update the status row for this plan in `plans/README.md`.
>
> **Read before starting**: `docs/testing.md` (all of it — the backend suite
> conventions). This plan adds only tests; it changes no production code.
>
> **Drift check (run first)**:
> `git diff --stat 3063e77e..HEAD -- backend/src/fanfan/application/interactors/notifications backend/src/fanfan/application/interactors/subscriptions backend/src/fanfan/application/interactors/push_sub`
> If any interactor changed since this plan was written, read its current
> `__call__` before writing its test.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: LOW (tests only)
- **Depends on**: none
- **Category**: tests
- **Blocks**: 007 (needs the `tests/integration/notifications/` harness this plan
  creates)
- **Planned at**: commit `3063e77e`, 2026-09-05

## Why this matters

Three core product domains have **no integration tests at all** — there is no
`tests/integration/{notifications,subscriptions,push_sub}/` directory:

- **Notifications / broadcasts** — the product's "get notified when the schedule
  changes" and organizer-broadcast features. The subscription-window and
  queue-difference arithmetic in `send_schedule_change_notifications.py` is exactly
  the ordering/time calculation `docs/testing.md` says must be tested.
- **Subscriptions** — a core attendee feature, including an **access-control
  guard** (`delete_subscription` rejects deleting another user's subscription)
  with zero regression protection.
- **Web Push subscriptions** — a named product pillar; registration/dedup/removal
  of push endpoints is unverified.

This plan establishes the test harness and the highest-value cases. It is also a
**prerequisite for Plan 007** (notification-idempotency fix): those changes must
land on top of characterization tests, not bare.

## Current state (facts the tests rely on)

- Test conventions (`docs/testing.md`): interactors are tested
  `@pytest.mark.integration` in `tests/integration/<feature>/`, against **real**
  PostgreSQL + Redis, resolved from `dishka_request`. External side-effecting
  ports (NATS `EventBroker`, push, email, Telegram, realtime) are **faked** and
  record what they received. Never unit-test an interactor with mocked gateways.
- Reference example to copy structure from:
  `backend/tests/integration/schedule_mgmt/test_set_current_event.py` (happy
  path, permission failure, an error path with `uow.rollback()`), and
  `backend/tests/integration/voting/test_add_vote.py` (nomination/participant
  setup, `visitor` / `visitor_with_ticket` personas, `outbox` assertions via
  `as_outbox(...)`).
- Shared fixtures (`tests/integration/conftest.py`): `login`, `outbox`, `uow`.
  User personas (`tests/fixtures/users.py`): `visitor`, `visitor_with_ticket`,
  `schedule_editor`, `sync_operator`. The `EventBroker` is faked as
  `FakeEventBroker`; resolve it to assert what a fan-out published.
- Interactors to cover (read each one's `__call__` and Input/Output before
  writing its test — signatures below are from HEAD `3063e77e`):

  **subscriptions/**
  - `create_subscription.py` — `CreateSubscriptionInput(event_id, counter)`;
    creates a `Subscription` for the current user; returns `subscription_id`.
    (Note: it injects `schedule_gateway`/`user_gateway` but uses neither, and does
    **not** validate that `event_id` exists — see "Document current behavior".)
  - `delete_subscription.py` — `DeleteSubscriptionInput(subscription_id)`; raises
    `SubscriptionNotFound` if missing, `AccessDenied` if
    `subscription.user_id != current_user.id`, else deletes.
  - `get_subscriptions.py` — read the signature before testing.

  **push_sub/**
  - `create_push_subscription.py`, `delete_push_subscription.py`
    (has an ownership check), `check_push_subscription.py` — read each `__call__`
    and its Input/Output before testing.

  **notifications/**
  - `send_broadcast.py` — `SendBroadcastInput(body, roles)`; requires
    `Permission.NOTIFICATIONS_SEND`; creates a `Mailing`, records
    `BroadcastQueued` on it (lands in the outbox), returns `mailing_id`.
  - `process_broadcast.py` — `ProcessBroadcastInput(mailing_id, body, roles)`;
    reads users by role, `set_total`, and publishes one `NotificationQueued` per
    user via the (faked) `EventBroker`.
  - `create_notification.py` — `CreateNotificationInput(notification)`; sanitizes
    the body, `increment_sent` on the mailing, inserts the notification.
  - `send_schedule_change_notifications.py` — the subscription-window /
    queue-difference fan-out (the most intricate; test last).

## Commands you will need

| Purpose               | Command                                                              | Expected |
|-----------------------|---------------------------------------------------------------------|----------|
| Lint                  | `just backend-lint`                                                 | exit 0   |
| Typecheck             | `just backend-typecheck`                                            | exit 0   |
| Integration (subset)  | `cd backend && uv run pytest -m integration backend/tests/integration/notifications backend/tests/integration/subscriptions backend/tests/integration/push_sub` | all pass |

**Docker required** (testcontainers Postgres + Redis). If unavailable, you can
write the tests but cannot verify them — STOP and report rather than guessing;
these tests must be run green at least once before this plan is DONE.

## Scope

**In scope** (new test files + their `__init__.py`, under `backend/tests/`):
- `backend/tests/integration/subscriptions/` (`__init__.py`, `test_create_subscription.py`, `test_delete_subscription.py`)
- `backend/tests/integration/push_sub/` (`__init__.py`, plus test file(s))
- `backend/tests/integration/notifications/` (`__init__.py`, `test_send_broadcast.py`, `test_process_broadcast.py`, `test_send_schedule_change_notifications.py`)

**Out of scope** (do NOT modify):
- Any production code under `backend/src/`. If a test reveals a bug (e.g.
  `create_subscription` accepting a non-existent `event_id`), **do not fix it** —
  write the test to document current behavior and note the bug in your report and
  the PR. Fixes are separate plans.
- Existing tests and fixtures (extend fixtures only if genuinely shared; prefer
  local setup in the test body per `docs/testing.md`).

## Git workflow

- Branch: `advisor/006-notifications-subscriptions-push-tests` off `main`.
- Commit per domain is fine (subscriptions / push / notifications) or one commit;
  imperative title, e.g.
  `Add integration coverage for subscriptions, push, and notifications`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

Do these in order; each is independently verifiable. Before writing each test,
open the interactor's `__call__` and its Input/Output model.

### Step 1: Subscriptions

`test_create_subscription.py`:
- happy path: `visitor` creates a subscription; assert it is persisted (resolve
  `SubscriptionGateway`, read it back) and the returned id matches.
- **Document current behavior**: creating a subscription for a non-existent
  `event_id` currently succeeds (no validation). Write the test to assert what
  actually happens today, and add a comment + a note in your report that this is a
  latent bug (candidate for a future plan), not something to fix here.

`test_delete_subscription.py` (model on the permission-failure test in
`schedule_mgmt/test_set_current_event.py`):
- happy path: a user deletes their own subscription; assert it's gone.
- `SubscriptionNotFound` when the id doesn't exist.
- **IDOR guard**: user A creates a subscription; user B attempting to delete it
  raises `AccessDenied` and the subscription still exists. This is the key
  security regression test.

**Verify**: `cd backend && uv run pytest -m integration backend/tests/integration/subscriptions` → all pass.

### Step 2: Push subscriptions

Read the three `push_sub` interactors first. Cover:
- create: registering an endpoint persists it; re-registering the **same**
  endpoint is idempotent (no duplicate / no error) — assert whatever the code
  actually does and document it.
- check: reports presence/absence correctly.
- delete: removes the endpoint; the ownership check rejects deleting another
  user's endpoint (assert `AccessDenied` or the actual guard exception).

**Verify**: `cd backend && uv run pytest -m integration backend/tests/integration/push_sub` → all pass.

### Step 3: Notifications — broadcast path

`test_send_broadcast.py`:
- happy path: a user with `NOTIFICATIONS_SEND` sends a broadcast; assert a
  `Mailing` is created and `BroadcastQueued` is in the outbox
  (`await outbox.fetch_unpublished(...)` compared via `as_outbox(...)`).
- permission failure: a `visitor` raises `AccessDenied`; nothing in the outbox.

`test_process_broadcast.py`:
- given N users matching the roles, `ProcessBroadcast` sets the mailing total to N
  and publishes N `NotificationQueued` events. Resolve the `FakeEventBroker` and
  assert on the recorded events (count and that each targets a distinct user).
  This test is the characterization baseline Plan 007 will build on.

**Verify**: `cd backend && uv run pytest -m integration backend/tests/integration/notifications -k "broadcast"` → all pass.

### Step 4: Notifications — schedule-change fan-out (the intricate one)

`test_send_schedule_change_notifications.py`: read
`send_schedule_change_notifications.py` carefully first (the subscription-window
condition `current_event.order <= changed_event.order <= s.event.order` and the
`s.event.queue - current_event_queue` math). Cover at least:
- a subscriber whose subscribed event is at/after the changed event within the
  window **receives** a notification; one outside the window does not;
- the queue-difference value carried to the notification is correct for a
  mid-schedule move.
Set up schedule events, a current event, and subscriptions through the gateways,
run the interactor, and assert on the published `NotificationQueued` set (via the
`FakeEventBroker`) and/or the outbox, matching how the interactor delivers.

**Verify**: `cd backend && uv run pytest -m integration backend/tests/integration/notifications` → all pass.

## Test plan

- New files listed in Scope. Each interactor gets happy-path + the failure/edge
  case that encodes a rule (`docs/testing.md` "write a test when the change
  encodes a rule that can break silently").
- Patterns: `schedule_mgmt/test_set_current_event.py` and
  `voting/test_add_vote.py`. Fakes and fixtures per `docs/testing.md`.
- Verification: the subset command in "Commands you will need" runs green.

## Done criteria

ALL must hold:

- [ ] `just backend-lint` exits 0; `just backend-typecheck` exits 0
- [ ] New dirs exist with `__init__.py` and the test files listed in Scope
- [ ] `cd backend && uv run pytest -m integration backend/tests/integration/notifications backend/tests/integration/subscriptions backend/tests/integration/push_sub`
      passes (all new tests green) — run at least once with Docker
- [ ] The subscription IDOR guard test and the `ProcessBroadcast` fan-out test
      both exist (they are the load-bearing ones)
- [ ] No production code under `backend/src/` modified (`git status`)
- [ ] Any bug discovered (e.g. `create_subscription` not validating `event_id`) is
      documented in the PR, not fixed here
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- No Docker daemon is available (tests can't be verified).
- An interactor's real signature differs materially from the summary above
  (drift) — write to the real signature and note it.
- A test can only pass by changing production code — that means you found a bug;
  document it and STOP rather than fixing it in this tests-only plan.
- The `FakeEventBroker` / a needed fake isn't registered for the interactor you're
  testing (e.g. `skip_validation` leaves a port unwired) — report which port, so
  a fake can be added deliberately (see `docs/testing.md` container-wiring notes).

## Maintenance notes

- Plan 007 depends on `test_process_broadcast.py` and a `create_notification`
  test; keep those readable and behavior-focused so 007's idempotency assertions
  slot in cleanly.
- If `create_subscription`'s missing event-existence validation is fixed later,
  the "document current behavior" test in Step 1 must be updated in the same
  change.
