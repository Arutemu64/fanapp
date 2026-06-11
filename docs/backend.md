# Backend Architectural Guidelines

> Testing conventions (unit vs integration, what to fake, rollback isolation)
> live in [testing.md](testing.md).

> Layer boundaries are enforced, not just documented: `just backend-import-lint` (import-linter, config in `backend/pyproject.toml`) fails the build if `core/` imports any outer layer, or if `application/` imports `adapters/`/`presentation/` outside the sanctioned exceptions listed below. Run it after touching imports; it is part of `just backend-lint`.

## Core Domain & Interactors
* **Core Layer (`core/`)**: Pure domain entities, value objects, and domain exceptions. Must be free of all I/O frameworks and outer layers — no FastAPI, SQLAlchemy, no `adapters/`/`application/`/`presentation/` imports. **Pydantic is the one allowed exception, and only in two narrow spots**: `core/events/base.py` (`AppEvent` is a `BaseModel` so domain events serialize cleanly over NATS) and `core/vo/fields.py` (validation helpers for value objects). Do not reach for Pydantic elsewhere in `core/` — plain dataclasses are the default for entities and value objects.
* **Application Layer (`application/`)**: Orchestrates interactors and business use cases. Must never import database ORM models directly. Communication with infrastructure happens via abstract interfaces (ports under `application/ports/`) and schemas/DTOs.
* **One gateway port per aggregate**: Each aggregate has a single port under `application/ports/gateways/`, named `XGateway`, that carries both writes (loading and persisting aggregates) and reads (DTO projections returned to callers). Group the read methods at the bottom of the port under a `# Read projections (return DTOs, not aggregates)` comment and prefix them with `read_`. We call these ports **gateways, not repositories, on purpose**: a strict DDD repository returns only aggregates, but these ports also serve read DTOs, so they are persistence *gateways* — which also matches their `SqlXGateway` implementations. We deliberately do **not** split reads and writes into separate repository + query ports; that CQRS-style split was pure ceremony at this scale (one gateway implemented both, then DI aliased it twice). Reach for a dedicated read port only if a read model ever genuinely diverges from its aggregate (different store, independent scaling).
* **Ports are `Protocol`, never `ABC`**: Define every port in `application/ports/` as a `typing.Protocol` (structural typing keeps the application layer free of any inward dependency from adapters). Do not decorate port methods with `@abstractmethod` — it does not catch signature drift and is redundant with the type checker. Adapters in `adapters/` **must explicitly subclass** the port they implement (e.g. `class SqlUserGateway(UserGateway): ...`); the explicit inheritance turns structural typing into checked nominal typing, so `just backend-typecheck` (`ty`) flags any method that drifts from its port — missing method, changed parameters, or a changed return type.

## Services

Services hold logic that is reused across several interactors (or is too cohesive to scatter through them). An interactor is one use case end-to-end; a service is a focused collaborator the use case leans on. Use a service only when the logic is genuinely shared — a single-caller helper usually belongs inline in its interactor. Services are wired in `main/ioc/services.py` (request-scoped). There are two homes, chosen by what the service depends on:

* **`core/services/`** — **pure** domain logic with no ports and no I/O (e.g. `email_login.py`: OTP policy constants plus a code generator). Same purity rules as the rest of `core/`: no FastAPI, SQLAlchemy, Pydantic, or adapter imports. These need no DI wiring when they are plain functions.
* **`application/services/`** — services that orchestrate over **ports** (gateways, id-provider, etc.). They live in the application layer precisely because they touch infrastructure through abstract ports — never concrete adapters or ORM models.

Naming: suffix services with `Service` (the historical `CurrentUserProvider` is the one exception). A port-dependent collaborator that is really an infrastructure concern (password hashing, etc.) is **not** a service — model it as a port in `application/ports/` with an adapter in `adapters/`, so the application layer stays free of concrete libraries.

## Persistence & Transaction Management
* **ORM Models**: SQLAlchemy database models live strictly under `adapters/db/models/`. Columns are typed with **standard/SQLAlchemy storage types only** (`str`, `int`, `uuid.UUID`, `datetime`, …) plus native enums (`Mapped[UserRole]` + `postgresql.ENUM(...)`). Do **not** annotate columns with domain value objects (e.g. `Mapped[UserId]`): keeping the ORM in storage types decouples it from `core/` and prevents a VO's underlying type from silently driving the column type (drift with no migration). The trade-off — VO ↔ storage conversion happening in one explicit place (the mapper) instead of implicitly — is intentional.
* **VO ↔ storage conversion happens only in mappers**: the mapper is the single seam where domain value objects are constructed from rows (`UserId(orm.id)`, `Email(orm.email)`) and unwrapped back (`model.id`, `model.email.value`). Because `to_model`/`parse_*_dto` must wrap every value, a VO whose base type drifts surfaces as a **type error in the mapper** — caught by `just backend-typecheck`, not at runtime. (Storage-vs-actual-column drift is still Alembic's job.)
* **Gateways**: Concrete SQL queries, database reads, and inserts are isolated in gateway implementations under `adapters/db/gateways/` (one per aggregate/concern). Each implements its aggregate's abstract `gateways/` port (reads and writes). Order methods to mirror the port: aggregate persistence first (`add`/`get`/`save`/`delete`), then `read_*` DTO projections last under the same `# Read projections (return DTOs, not aggregates)` divider, so port and adapter read identically top-to-bottom.
* **Constraint-violation handling**: A gateway must never leak a raw `IntegrityError` for a *known, reportable* conflict — translate it to a domain exception at the boundary so inner layers stay pure. There are two sanctioned styles, chosen by whether the caller needs to hear about the conflict:
  * **Reportable conflict → `translate_integrity_error` (`adapters/db/constraints.py`)**. Force the write with `await session.flush([orm])` *inside* the `with` block so the violation surfaces at the gateway (not later at `uow.commit()`), and map the constraint name to a domain exception: `with translate_integrity_error({"uq_votes_user_id": VoteAlreadyExists}): ...`. It dispatches on the DB constraint name (robust, driver-tolerant — relies on the `uq_`/`fk_`/`ix_` naming convention), raises `from` the original, and **re-raises any unmapped constraint** so an unexpected `NOT NULL`/`CHECK` bug is never swallowed or mislabeled. This is the default — and it is also the race-safe backstop, so do **not** pre-`SELECT` to avoid the insert.
  * **Idempotent marker → `INSERT ... ON CONFLICT DO NOTHING`**. Only when a duplicate is a no-op the caller need not hear about (e.g. `user_flags`: a user either has a flag or not). Race-free at the DB level and avoids the try/except, but it signals "nothing happened" via `rowcount`, never an exception — so do not use it where a conflict must surface as a domain error.
* **Mappers**: ORM model ↔ domain entity translation lives in `adapters/db/mappers/` (one per aggregate). Gateways must map ORM rows to pure domain objects (and back) through these — never leak ORM models out of the adapter layer. When you add a new persisted aggregate, you typically add a model, a mapper, and a gateway together.
* **Transaction Management (Unit of Work)**: Database commits and rollbacks in use cases are managed strictly by injecting `uow: UnitOfWork` (from `application/ports/uow.py`) and invoking `await self.uow.commit()`. Do not call raw SQLAlchemy session commits (`session.commit()`) inside interactors. The `UnitOfWork` also tracks aggregates and, on commit, writes their domain events to the transactional outbox in the same transaction (see [Domain Events](#domain-events)) — gateways call `self.uow.register(aggregate)` inside their `add`/`get` methods so the interactor never pulls or publishes those events by hand.
* **Migrations**: Generate and apply database migrations strictly via Alembic CLI helpers (`just backend-generate <name>` and `just backend-migrate`). Autogenerate has `compare_type` on (Alembic's default since 1.12.0), so it detects column **type** drift between the ORM models and the database — which pairs with the mapper's compile-time VO checks to cover both seams. Plain Alembic ignores changes to **enum members**, so PostgreSQL enum migrations (adding/removing/renaming `ENUM` labels) are handled by [`alembic-postgresql-enum`](https://github.com/RustyGuard/alembic-postgresql-enum); it is activated by the bare `import alembic_postgresql_enum` at the top of `migrations/env.py`, which registers the autogenerate hooks. Keep that import — without it, enum-value changes silently produce no migration.

## Dependency Injection (Dishka)
* **DI Container**: Wired in `main/di.py` using Dishka providers (defined under `main/ioc/`).
* **Router/Presenter Injection**: Use the `@inject` decorator and `FromDishka[...]` type annotations to inject interactors into routes or presenters. Do not use standard FastAPI `Depends(...)` for dependencies managed by Dishka.
  ```python
  from dishka import FromDishka
  from dishka.integrations.fastapi import inject

  @router.get("/voting/status")
  @inject
  async def get_voting_status(
      interactor: FromDishka[GetVotingStatus]
  ) -> VotingStatusDTO:
      return await interactor()
  ```

## Domain Events

Events are published via `EventBroker` (port: `application/ports/events_broker.py`) and consumed by FastStream subscribers in `presentation/faststream/routes/`.

**Do not add a published event without a corresponding subscriber.**

### Events raised by aggregates (preferred)

When an event directly records a state change on an aggregate, raise it inside the aggregate method using `record_event()`. The interactor does **not** publish these — the `UnitOfWork` handles them automatically. The gateway registers the aggregate when it is added or loaded, and `uow.commit()` writes the recorded events to the **transactional outbox** in the same transaction as the state change (see [Transactional outbox](#transactional-outbox)):

```python
# core/models/vote.py
class Vote(AggregateRoot):
    @classmethod
    def create(cls, *, user_id, participant_id) -> Self:
        vote = cls(...)
        vote.record_event(VoteCreated(vote_id=vote.id, ...))
        return vote

    def delete(self) -> None:
        self.record_event(VoteDeleted(vote_id=self.id, ...))

# adapters/db/gateways/votes.py — register on add/get
async def add(self, vote: Vote) -> None:
    self.session.add(self.mapper.from_model(vote))
    await self.session.flush(...)
    self.uow.register(vote)

# application/interactors/voting/add_vote.py — no manual publish
vote = Vote.create(user_id=..., participant_id=...)
await self.vote_repo.add(vote)
await self.uow.commit()  # writes the vote + a VoteCreated outbox row atomically
```

`Vote`, `ScheduleChange`, and `Mailing` follow this pattern; their gateways register the aggregate in every `add`/`get` method. `Mailing.queue_broadcast()` records `BroadcastQueued`, so a broadcast lands in the outbox and is delivered atomically with its mailing row. The `UnitOfWork` pulls events from each registered aggregate exactly once (the internal event list is cleared on store) and writes them as outbox rows in the same transaction, so a rolled-back transaction never emits events. When you add a new aggregate that records events, register it in its gateway's `add`/`get` methods — that is the only wiring required.

### Transactional outbox

Aggregate events are **not** published to NATS on commit. Publishing to a separate system after the DB commits is a dual write — if the process dies between the two, the state is persisted but the event is lost. Instead, `uow.commit()` serializes each recorded event into an `OutboxEventORM` row (`adapters/db/models/outbox.py`) committed in the **same transaction** as the aggregate change, and a relay delivers it asynchronously:

* **Relay** — `PublishOutboxEvents` (`application/interactors/outbox/`), run as an `IntervalTrigger` job (~seconds) in the scheduler (`main/scheduler.py`). It reads unpublished rows `FOR UPDATE SKIP LOCKED`, calls `EventBroker.publish_raw(subject, payload, message_id)`, marks them published, and commits.
* **Delivery guarantee** — at-least-once: a row is marked published only after NATS acks it. Consumers stay idempotent; the row id is sent as `Nats-Msg-Id` so JetStream dedups redeliveries within its window.
* **Retention** — `PurgeOutboxEvents` drops delivered rows older than `OutboxConfig.retention_days`, on the `SCHEDULER__OUTBOX_RETENTION_CRON` cron.
* **Scope** — outbox covers aggregate events only. Service events (below) stay direct, since they guard no committed state.

This makes domain-event delivery atomic with the write, at the cost of one poll-interval of latency. SSE/realtime is unaffected — it uses `RealtimeGateway`, not `EventBroker`.

### Events raised directly by interactors (service events)

Some events are not tied to a single aggregate's committed state change — they are application-level triggers to infrastructure (e.g. "queue a notification for these users", "send an email code"). These are constructed and published directly in the interactor via an injected `EventBroker`, and are **not** routed through the `UnitOfWork`:

```python
# application/interactors/notifications/send_personal_notification.py
await self.events_broker.publish(
    NotificationQueued(notification=...)
)
```

`NotificationQueued` and `MailingCancelled` follow this pattern, as do the user email-code events `EmailLoginCodeRequested` (`request_login_code.py`) and `EmailConfirmationCodeRequested` when sent as a standalone "resend a code" (`request_email_code.py`). These represent "send a code" commands, not aggregate state changes — `request_login_code` / `request_email_code` change no persistent state and may run with no commit at all — so they are **not** recorded on the `User` aggregate. The interactor constructs and publishes them directly via `EventBroker`.

> `BroadcastQueued` used to be published here too, but it guards a committed `Mailing` row, so it now flows through the outbox via `Mailing.queue_broadcast()` (see [Domain Events](#domain-events)).

> Keep domain events honest: a domain event must record an actual state change (past tense). Do **not** call `record_event()` for an action that mutates nothing — model it as a service event published by the interactor instead. `User.request_email_change()` is the counter-example that *is* a domain event: it sets `pending_email`, so it records `EmailConfirmationCodeRequested` and that event flows through `uow.commit()` (the `SqlUserGateway` registers every `User` it adds or loads).

Rule of thumb: inject `EventBroker` into an interactor **only** for service events; aggregate state-change events flow through `uow.commit()`.

## Notification Formatting

A notification `body` is stored as a **small, safe HTML subset** so the same text can be highlighted across every delivery channel. The subset is the intersection of what Telegram's HTML parse mode accepts and what the web UI can render: `b`, `strong`, `i`, `em`, `u`, `s`, `a[href]`, `code`, `pre`, `blockquote`. Line breaks are stored as plain `\n` (no `<br>`/`<p>`), which Telegram treats as newlines and the web renders via CSS `white-space: pre-line`.

* **Single sanitization chokepoint**: every notification — broadcast, personal message, schedule-change template — is built into the persisted model in `CreateNotification._to_model` (`application/interactors/notifications/create_notification.py`), which runs the body through the `HtmlSanitizer` port (`application/ports/html_sanitizer.py`, nh3 adapter `adapters/html/sanitizer.py`). `SendNotification` and the realtime SSE DTO both re-read the **persisted, already-sanitized** record, so sanitizing once covers web, Telegram, and push. Never sanitize per-channel.
* **Per-channel rendering**: the web UI renders the stored body with `{@html}` (it is pre-sanitized — see [frontend.md](frontend.md)); the Telegram notifier (`adapters/tgbot/notifier.py`) sends it with `parse_mode=ParseMode.HTML` and only HTML-escapes the plain-text `title`; the push notifier (`adapters/push/push.py`) strips all tags to plain text because OS notifications do not render HTML.
* **Templates**: Jinja notification templates (`adapters/jinja/templates/`) may use the subset tags directly (e.g. `<b>`) to highlight key details. `autoescape=True` keeps `{{ variables }}` escaped, and the central sanitizer is the final safety net, so template-interpolated DB values can never inject markup.

## Rate Limiting

Two distinct rate-limiting ports exist — pick by semantics, do not overload one for the other:

* **`RateLockFactory`** (`application/ports/rate_lock.py`): a distributed mutex that also enforces a cooldown, written **only on a successful run**. Use it for "one *successful* action per N seconds" flows where a failure should be retryable immediately (e.g. requesting/sending an email code). A failed attempt does **not** consume the cooldown.
* **`RateLimiter`** (`application/ports/rate_limiter.py`): a fixed-window attempt **counter** that locks a key once a number of attempts is exceeded, regardless of success. Use it to penalize failures — password login brute-force, OTP guessing. Call `hit(key, limit=, window_seconds=)` on each attempt and `reset(key)` after success. It raises `TooManyAttempts`; callers catch and re-raise a flow-specific subclass (`TooManyLoginAttempts`, `TooManyOtpAttempts`) so each feature keeps its own error code/copy.

The Redis adapters live in `adapters/redis/rate_lock.py` and `adapters/redis/rate_limiter.py`. The login interactor passes the client IP in via its input DTO (filled by the web route through `presentation/web/utils.get_client_ip`) so the application layer never touches `Request`.

## Captcha

The unauthenticated `request-login-code` flow is additionally guarded by a captcha, behind the `CaptchaVerifier` port (`application/ports/captcha.py`). The interactor calls `await captcha_verifier.verify(token)` before doing any work; a missing or rejected token raises `CaptchaVerificationFailed` (mapped to HTTP 403). The token rides in on the input DTO so the application layer never touches `Request`.

The feature is **optional and config-gated**, like the other external integrations: when `turnstile` is unset in `EnvConfig` (no `TURNSTILE__SECRET_KEY`), `CaptchaProvider` (`main/ioc/captcha.py`) wires a `NoOpCaptchaVerifier` that accepts everything; when set, it wires `TurnstileCaptchaVerifier` (`adapters/captcha/turnstile.py`), which validates against Cloudflare's siteverify endpoint. A missing token or an explicit negative verdict is always rejected, but if Cloudflare is **unreachable** (transport error or 5xx) the verifier **fails open** — a CDN outage shouldn't lock everyone out of login, and the per-email rate lock still caps abuse. The matching frontend key is `PUBLIC_TURNSTILE_SITE_KEY`.

## Anti-corruption layers (vendor sync)

The `application/` layer must not import `adapters/` — with one sanctioned, narrow exception: the third-party sync flows for **cosplay2** and **TicketsCloud**. These are anti-corruption layers (ACLs): their whole job is to translate a vendor's wire format into our domain model, so they legitimately depend on the vendor adapter's client, config, and DTOs.

* The sanctioned modules are `interactors/cosplay2/sync_cosplay2.py`, `interactors/ticketscloud/sync_tcloud.py`, `interactors/ticketscloud/process_tcloud_order.py`, and `services/ticketscloud.py`.
* The exact allowed edges are pinned as `ignore_imports` in the import-linter contract (`backend/pyproject.toml`). **Any other `application → adapters` import is a bug** and will fail `just backend-import-lint`.
* If you build a new vendor integration, prefer keeping the translation here as an ACL and adding the specific edges to the `ignore_imports` list — do **not** widen the rule. Do not dress an ACL up behind a generic port whose methods still traffic in vendor DTOs; that hides the coupling without removing it.

## Presentation Layers
* **HTTP APIs (`presentation/web/`)**: FastAPI routes mapping HTTP requests.
* **Event Streaming & Bots (`presentation/faststream/`, `presentation/tgbot/`)**: FastStream handlers consuming NATS subjects, or Telegram bots handling events. Inject interactors exactly the same way using `@inject` and `FromDishka`.
* **Scheduler (`presentation/scheduler/`)**: APScheduler (v3 `AsyncIOScheduler`) runs periodic sync jobs (`sync_tcloud`, `sync_cosplay2`) as the `scheduler` compose service (composition root: `main/scheduler.py`). Dishka has no APScheduler integration — each job is a closure that opens a fresh REQUEST scope off the system container and resolves the interactor, mirroring the CLI commands. Schedules are cron strings in config (`SCHEDULER__SYNC_*_CRON`, app timezone); unset = job disabled. Change a schedule by editing `.env` and running `docker compose restart scheduler` — no code change. Trigger a sync manually any time via `docker compose run --rm api cli sync tcloud`.
* **Exception Mapping**: Interactors raise pure domain exceptions. The presentation layer is responsible for catching and mapping these exceptions to standard client-safe formats (e.g. using exception handlers in `presentation/web/exceptions.py` for FastAPI endpoints).

## Logging & Observability
* **Setup**: Logging is configured once per process by `setup_logging()` in `adapters/debug/logging.py`, called from the shared `main/common.py:init()` that every service entrypoint runs. It uses **structlog as a formatting layer over the stdlib `logging`** module (via `ProcessorFormatter` + `foreign_pre_chain`), so plain `logging.getLogger(__name__)` records and structlog records flow through the same pipeline. `setup_logging()` is idempotent — it clears existing root handlers before adding its own, so calling `init()` more than once does not duplicate log lines.
* **Getting a logger**: Use the stdlib pattern everywhere: `logger = logging.getLogger(__name__)` at module level. Do not call `structlog.get_logger()` — the codebase standardises on stdlib loggers.
* **Output format**: Console (`ConsoleRenderer`) by default; JSON (`JSONRenderer`) when `DEBUG__JSON_LOGS=true`. Log level and JSON toggle come from `DebugConfig` (`adapters/debug/config.py`). Set the level to INFO (or higher) in production — the default is `DEBUG`.
* **Request correlation**: The web app binds a `request_id` into structlog `contextvars` for every HTTP request via `bind_request_context` (`presentation/web/middlewares.py`, registered last in the factory so it runs outermost). Because the processor chain includes `merge_contextvars`, every log line emitted while handling a request automatically carries that `request_id`; it is also echoed back in the `X-Request-ID` response header (and reused from the incoming header when present). To attach more fields to all logs in a scope, use `structlog.contextvars.bind_contextvars(...)`.
* **Noise control**: Noisy third-party loggers (urllib3, aiogram.event, aiohttp.access) are raised to WARNING, and `uvicorn.access` logs for the `/debug/health` probe are dropped by `_HealthCheckFilter`.
* **Error reporting (Sentry)**: `setup_telemetry()` (`adapters/debug/telemetry.py`) wires Sentry when `DEBUG__SENTRY_DSN` is set. Domain `AppException`s and request-validation errors are filtered out, and request headers / user PII are scrubbed before events are sent.
