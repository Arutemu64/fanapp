# Testing Guidelines

How the test suites are structured and the conventions to follow when adding
tests. The backend suite lives under `backend/tests/` and runs with `pytest` +
`uv`; the frontend suite is colocated under `frontend/src/` and runs with
Vitest ([Frontend](#frontend) below).

> **Whether a change needs a new test is your call — make it deliberately,
> rather than defaulting either way.** Write one when the change encodes a rule
> that can break silently: a permission, a state transition, an ordering or
> time calculation, a parser, or a bug you just fixed. Skip it for copy,
> styling, config, and refactors an existing test already covers. On a close
> call, write the test.
>
> The **existing** suite is not optional: CI runs `pytest tests` and
> `pnpm test`, so a change that breaks a test is broken. And `just
> backend-lint` + `just backend-typecheck` (or `just frontend-lint` + `just
> frontend-check`) still run after every change.

Everything from here to [Frontend](#frontend) describes the **backend** suite.

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

Cloud sessions run integration tests in-session (`just backend-test` /
`backend-test-integration`), same as CI (`.github/workflows/ci.yml`). The
setup script prepulls the testcontainers images (`postgres:18.4-alpine` —
pinned, and shared with Alembic autogenerate and production — and
`valkey/valkey:9.1-alpine`) and the SessionStart hook starts `dockerd` and sets
`TESTCONTAINERS_RYUK_DISABLED=true` (matching CI — the fixtures already stop
their own containers in `finally:` blocks, so the Ryuk reaper isn't needed).
Provisioning details — setup script vs. hook, image prepull, Docker Hub auth,
network access — are in [claude-cloud.md](claude-cloud.md).

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

### Drift guards

A handful of unit tests exist for a different reason: the repo commits
generated artifacts, and a stale one fails silently — it stays internally
consistent, so every other gate goes green while it describes code that no
longer exists. Each committed artifact therefore gets a test that regenerates
it in memory and compares:

| Test | Guards | Fix a failure with |
|------|--------|--------------------|
| `unit/presentation/test_openapi_spec.py` | `shared/openapi/openapi.json` vs. the routers and DTOs | `just frontend-generate-api` |
| `unit/adapters/test_schedule_parser.py::test_parses_the_downloadable_template` | `frontend/static/schedule-template.xlsx` vs. the parser's required columns | `just backend-generate-schedule-template` |
| `integration/test_migrations.py` | the ORM models vs. the migrations (needs Docker) | `just backend-generate <name>` |

The second half of the API contract chain — `frontend/src/lib/api/schema.d.ts`
vs. the spec — is checked by `just frontend-check-api` rather than a test,
because it belongs to the frontend toolchain. See [api.md](api.md).

Adding a generated file that gets committed? Add its guard in the same change,
and state the regeneration command in the failure message — the person who
trips it is rarely the person who wrote it.

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
| `CosplaySource` (Cosplay2) | **fake** (`FakeCosplaySource`) | external HTTP; test supplies nominations/participants, or sets `raises` to exercise the failure path |

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
* Test: `TestDbProvider` (testcontainers config), `TestConfigProvider`
  (fixed test `WebConfig` for the session store and token registry — the full
  `EnvConfig` is not built in tests), `TestSessionProvider` (rollback session),
  and the fakes above.
* `skip_validation=True` is intentional: external integrations (NATS broker,
  Telegram bot, SMTP, OAuth) are not wired, so interactors needing them are not
  yet resolvable. Everything else resolves. Both vendor syncs now sit behind
  ports with fakes (`FakeTicketsSource`, `FakeCosplaySource`), so the sync
  interactors are testable. When the remaining integrations gain a port + fake,
  register them and the flag can eventually be dropped.
* `TestSyncProvider` overrides `AvailableSyncSources`, whose real factory in
  `SyncProvider` reads the `EnvConfig` tests never build. Like
  `TestSessionProvider`, it must be registered **after** the provider it
  overrides — Dishka resolves the last provider registered for a type.

## Fixtures

Reusable user fixtures (`visitor`, `visitor_with_ticket`, `schedule_editor`,
`sync_operator`) live in `tests/fixtures/users.py` and are registered as a plugin in
`tests/conftest.py`. The shared plumbing fixtures (`login`, `outbox`,
`uow`) live in `tests/integration/conftest.py` — see *Shared plumbing
fixtures* above. Add shared setup in these places rather than copying it
between tests.

---

# Frontend

Vitest, run with `just frontend-test` (`pnpm --dir frontend test`) and in CI
alongside the other frontend gates.

Config lives in the `test` block of `frontend/vite.config.ts`, not a
`vitest.config.ts` of its own — that is what the
[Svelte testing docs](https://svelte.dev/docs/svelte/testing) and `sv add
vitest` do, and it is load-bearing: tests run through the SvelteKit plugin, so
`$lib`/`$app` imports resolve and runes compile. `resolve.conditions` is set to
`['browser']` under `VITEST` so packages resolve their browser entry points even
though the runner is Node.

## What to test here

The frontend's testable surface is the **logic in `src/lib/`** — the modules
that encode a rule a reader cannot check by eye: text normalization and matching
(`utils/search.ts`), formatters and pluralization (`utils/formatters.ts`),
permission predicates (`utils/permissions.ts`), cache scoping and staleness
(`utils/offlineCache.ts`). These are where a silent regression is expensive and
a test is nearly free.

That includes the **rune modules** (`services/*.svelte.ts`,
`utils/cooldown.svelte.ts` and friends): name the test `*.svelte.test.ts` and
`$state`/`$derived`/`$effect` are available inside it. Effects need
`$effect.root` and a `flushSync()` to run synchronously — the
[Svelte testing docs](https://svelte.dev/docs/svelte/testing) show the pattern.
Reading a `$derived` directly from test scope only captures its initial value;
pass a getter (`() => count`) into the module under test, as those examples do.

Components, routes and `load` functions are **not** covered: the runner has no
DOM environment, deliberately. Adding one is a real decision (jsdom or Vitest
browser mode, plus `@testing-library/svelte` if you want it), so make it a
considered change and update this section rather than bolting it on — see
[ADR-0011](adr/0011-vitest-for-frontend-unit-tests.md). The Svelte docs' own
advice applies first, though: before reaching for a component test, check
whether the logic can be lifted out and tested without one.

The same judgement call as the backend applies: write a test when the change
encodes a rule that can break silently, skip it for copy, styling and config.

## Conventions

1. **Colocate**: `foo.ts` is tested by `foo.test.ts` in the same folder, and
   `foo.svelte.ts` by `foo.svelte.test.ts` — the `.svelte.` in the name is what
   makes runes available. Vitest collects `src/**/*.test.ts`, which covers both.
2. **Import explicitly** — `import { describe, expect, it } from 'vitest'`.
   Globals are off, so a test file's dependencies are visible at the top like
   any other module.
3. **Test the exported contract**, not the internals. `search.test.ts` exercises
   ё/е folding, diacritics and token order through `createSearchIndex` — the
   only export — so the helpers underneath stay free to change.
4. **Russian fixtures for Russian text.** The normalization rules exist for
   Cyrillic input; assert them with real Russian strings, not ASCII stand-ins.
5. Prettier and ESLint apply to test files like any other source file.
