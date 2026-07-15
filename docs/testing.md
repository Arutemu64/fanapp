# Backend Testing Guidelines

How the backend test suite is structured and the conventions to follow when
adding tests. Tests live under `backend/tests/` and run with `pytest` + `uv`.

> Tests are optional, not mandatory on every change — run them when useful,
> on request, or in CI. After backend code changes you still always run
> `just backend-lint` and `just backend-typecheck`.

## Rules at a glance

Everything below this section is detail; these rules alone are enough to add a
correct test.

1. **Pure domain logic** (`core/`) → `@pytest.mark.unit` test in `tests/unit/`.
   Instantiate the object, call the method, assert. No mocks, no database, no
   DI container.
2. **An interactor** (`application/interactors/`) → `@pytest.mark.integration`
   test in `tests/integration/<feature>/`. Runs against real PostgreSQL and
   Redis. Resolve the interactor from `dishka_request`, assert on persisted
   state and enqueued/published events. **Never unit-test an interactor with
   mocked gateways** — its behavior lives in SQL.
3. **Copy the reference example**:
   `tests/integration/schedule_mgmt/test_set_current_event.py` (happy path,
   permission failure, rate limit, rollback on error).
4. **Real vs fake**: everything behind PostgreSQL/Redis is real (gateways,
   `UnitOfWork`, rate limiter, sessions), and so are deterministic ports
   (hasher, Jinja). Ports that reach *other* external systems (NATS, SMTP,
   Telegram, WebPush, realtime) are faked. New side-effecting port? Add a
   recording fake in `tests/fakes/` and register it in
   `tests/integration/conftest.py` via `AnyOf[ThePort, TheFake]`.
5. **Fixtures are for plumbing only** (`login`, `outbox`, `uow`, user
   personas like `visitor` / `schedule_editor`). The interactor
   under test and the gateways you assert on are resolved explicitly with
   `dishka_request.get(...)` in the test body — never hidden in a fixture.
6. **No cleanup code.** Database writes roll back automatically after every
   test; Redis is flushed automatically. Don't truncate tables or hand-pick
   unique ids.

## Two layers

| Layer | Location | Marker | Infrastructure | Speed |
|-------|----------|--------|----------------|-------|
| Unit | `tests/unit/` | `@pytest.mark.unit` | none | instant |
| Integration | `tests/integration/` | `@pytest.mark.integration` | real PostgreSQL + Redis (testcontainers) | seconds |

Run a subset by marker:

```sh
cd backend
uv run pytest -m unit           # fast, no Docker required
uv run pytest -m integration    # requires a running Docker daemon
uv run pytest                    # everything
uv run pytest --cov             # with coverage (config in pyproject.toml)
```

Integration tests need Docker available (testcontainers spins up real
PostgreSQL and Redis). They cannot run in environments without a Docker daemon.

### Running them on Claude Code on the web

Cloud sessions do **not** run integration tests in-session — CI does
(`.github/workflows/ci.yml`, full `pytest` suite on every push). They prepull
only `postgres:18-alpine` (for Alembic autogenerate), not the testcontainers
images, and keep running the fast, container-free checks (`just backend-lint`,
`backend-typecheck`). For an ad-hoc integration run in-session: the SessionStart
hook starts `dockerd`, but you must lazy-pull the testcontainers images and set
`TESTCONTAINERS_RYUK_DISABLED=true` yourself (the fixtures stop their own
containers in `finally:` blocks). Provisioning details — setup script vs. hook,
image prepull, Docker Hub auth, network access — are in
[claude-cloud.md](claude-cloud.md).

## Unit tests — for `core/`

Pure domain logic (`core/models/`, `core/vo/`, `core/services/`, `core/utils/`)
is tested in isolation: instantiate the object, call the method, assert. No DI
container, no database, no async fixtures. These protect domain rules
(aggregate state machines, value-object validation, event recording) cheaply.

```python
pytestmark = pytest.mark.unit

def test_set_as_used_twice_raises():
    ticket = _ticket(used_by=UserId(uuid7()))
    with pytest.raises(TicketAlreadyUsed):
        ticket.set_as_used(UserId(uuid7()))
```

Aggregates record domain events via `record_event`; assert on `pull_events()`
to verify the right event was raised (see `tests/unit/core/test_vote.py`).

## Integration tests — for interactors

Interactors are tested **through the real stack**: a real database and real
gateways, resolved from the Dishka container, exactly as in
production. We do not unit-test interactors with mocked gateways — most of
their behavior lives in SQL (constraints, cascades, joins, locking), so a
mock-only test would assert call order and re-encode the implementation
instead of verifying behavior.

A test resolves what it needs from `dishka_request`, sets up state through
gateways, runs the interactor, and asserts on persisted state and
enqueued events. The shared plumbing (acting user, outbox, unit of
work) comes in as fixtures; the interactor under test and the
gateways it asserts on stay explicit so a reader sees the test's
surface at a glance:

```python
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

async def test_add_vote_creates_vote_and_publishes_event(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    login(visitor_with_ticket)              # set the acting user
    interactor = await dishka_request.get(AddVote)
    vote_gateway = await dishka_request.get(VoteGateway)
    ...
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(VoteCreated(...))
```

`tests/integration/schedule_mgmt/test_set_current_event.py` is the reference
example to copy from — happy paths, the permission failure, the rate-limit
path, and an error path that rolls back.

### Shared plumbing fixtures

These live in `tests/integration/conftest.py` and exist only to remove the
identical `dishka_request.get(...)` boilerplate every test would otherwise
repeat:

| Fixture | Type | Use |
|---------|------|-----|
| `login` | `Callable[[User], None]` | `login(user)` sets the acting user (wraps `FakeIdProvider`) |
| `outbox` | `OutboxGateway` | assert on enqueued aggregate events: compare `fetch_unpublished(...)` against the `as_outbox(...)` helper |
| `uow` | `UnitOfWork` | commit setup state; `uow.rollback()` after an expected error |

Rule of thumb: take the plumbing you need from fixtures, but resolve the
**interactor under test and its gateways explicitly** in the body
— do not hide what a test exercises behind more fixtures.

## What is real and what is faked

The rule follows the architecture: **run everything behind the DB/Redis
adapters for real; fake the ports that reach other external systems.**

| Dependency | In tests | Why |
|------------|----------|-----|
| Gateways, `UnitOfWork` | **real** (PostgreSQL) | behavior is in the SQL |
| `TokenRegistry`, `SessionStore`, `RateLimiter`, `RateLockFactory` | **real** (Redis) | behavior is in Redis semantics |
| `PasswordHasher`, Jinja `TemplateRenderer` | **real** | deterministic, no external I/O |
| `EventBroker` | **fake** (`FakeEventBroker`) | assert *what* was published, not NATS delivery |
| `IdProvider` | **fake** (`FakeIdProvider`) | the test sets the acting user |
| `EmailSender`, `TelegramNotifierPort`, `PushNotifierPort`, `RealtimeGateway` | **fake** | external side-effects (SMTP / Telegram / WebPush / NATS) |
| `TicketsSource` (TicketsCloud) | **fake** (`FakeTicketsSource`) | external HTTP; test supplies the tickets a sync should see |
| Cosplay2 HTTP client | not wired yet | concrete client, no port seam (see below) |

Fakes live in `tests/fakes/` and record what they received so tests can assert
on it. When you make a new side-effecting port testable, add a fake there and
register it in the test container (`tests/integration/conftest.py`) via
`AnyOf[ThePort, TheFake]` so a test can resolve either the port or the fake.

## Test isolation: rollback per test

Each integration test runs inside its own database transaction that is **always
rolled back** when the test ends — nothing is persisted and no test sees another
test's writes, even though interactors call `uow.commit()` normally.

This is implemented by `TestSessionProvider`
(`tests/fixtures/db_session.py`), which binds the session to a per-test
connection with `join_transaction_mode="create_savepoint"`: an interactor's
`commit()` only releases a SAVEPOINT, while the outer transaction is rolled
back at teardown. It is registered after `DbProvider` so it overrides the
production session (Dishka resolves the last provider registered for a type).

Consequences:

* You do **not** need to clean up database rows, and you do not need to
  hand-pick unique ids to avoid collisions between tests.
* Redis is **not** transactional, so it is flushed between tests by the
  `reset_redis` autouse fixture.
* Schema and seed data (the `system` user, permissions) are created once per
  session by Alembic migrations and are visible to every test.

## Container wiring (`tests/integration/conftest.py`)

The session-scoped `dishka` fixture builds a container from the real IoC
providers plus test overrides:

* Real: `InteractorsProvider`, `DbProvider`, `SqlGatewaysProvider`,
  `RedisProvider`, `ServicesProvider`, `SecurityProvider`, `JinjaProvider`.
* Test: `TestDbProvider` (testcontainers config), `TestSessionProvider`
  (rollback session), and the fakes above.
* `skip_validation=True` is intentional: external integrations (NATS broker,
  Telegram bot, SMTP, OAuth, the Cosplay2 HTTP client) are not wired, so
  interactors needing them are not yet resolvable. Everything else resolves.
  TicketsCloud now sits behind the `TicketsSource` port with a
  `FakeTicketsSource`, so ticket-sync interactors are testable. When the
  remaining integrations gain a port + fake, register them and the flag can
  eventually be dropped.

## Fixtures

Reusable user fixtures (`visitor`, `visitor_with_ticket`, `schedule_editor`)
live in `tests/fixtures/users.py` and are registered as a plugin in
`tests/conftest.py`. The shared plumbing fixtures (`login`, `outbox`,
`uow`) live in `tests/integration/conftest.py` — see *Shared plumbing
fixtures* above. Add shared setup in these places rather than copying it
between tests.
