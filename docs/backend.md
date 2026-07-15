# Backend Architectural Guidelines

> Testing conventions (unit vs integration, what to fake, rollback isolation)
> live in [testing.md](testing.md).

> Layer boundaries are enforced, not just documented: `just backend-import-lint` (import-linter, config in `backend/pyproject.toml`) fails the build if `core/` imports any outer layer, or if `application/` imports `adapters/`/`presentation/` outside the sanctioned exceptions listed below. Run it after touching imports; it is part of `just backend-lint`.

## Rules at a glance

Everything below this section is detail; these rules alone prevent most mistakes.

1. `core/` is pure domain: plain dataclasses, no I/O frameworks. Pydantic is allowed
   only in `core/events/base.py` and `core/vo/fields.py`.
2. `application/` orchestrates through ports (`application/ports/`) — never ORM
   models or concrete adapters.
3. One gateway port per aggregate (`XGateway`): writes first, then `read_*` DTO
   projections under a `# Read projections (return DTOs, not aggregates)` divider.
4. Ports are `typing.Protocol` (no `@abstractmethod`); adapters explicitly subclass
   their port so the type checker catches signature drift.
5. Authorize via `PermissionService.ensure(...)` — never hardcoded role checks.
   Authenticate inside interactors via `CurrentUserProvider.require_user()` — never
   FastAPI `Depends`.
6. Commit only via `uow.commit()`. Aggregate state-change events: `record_event()`
   inside the aggregate (delivered through the outbox). Service events (no state
   change): publish via `EventBroker` in the interactor.
7. Translate known `IntegrityError`s to domain exceptions at the gateway with
   `translate_integrity_error` — do not pre-`SELECT` to dodge the race.
8. New domain exception: inherit the semantic marker (`NotFound`, `Conflict`, …)
   listed *first* in the bases; never edit the status map.
9. Migrations: prefer autogenerate; always review the output (renames emit as
   drop+create; enum member changes need hand-written migrations).
10. Logging: stdlib `logging.getLogger(__name__)`; short static message + scalar ids
    in `extra`; `str(...)` UUIDs; never log secrets, codes, or PII.

## Common task recipes

### Add a persisted aggregate
1. Domain model in `core/models/` (dataclass; subclass `AggregateRoot` if it records events).
2. ORM model in `adapters/db/models/` — storage types only, no VO-typed columns.
3. Mapper in `adapters/db/mappers/` — the only place VO ↔ storage conversion happens.
4. Port `XGateway` in `application/ports/gateways/`; implementation in `adapters/db/gateways/` explicitly subclassing it. If the aggregate records events, call `self.uow.register(aggregate)` in every `add`/`get`.
5. Wire providers in `main/ioc/`; generate a migration (`just backend-generate-auto <name>`) and review it.

### Add a domain event
1. Class in `core/events/<context>.py`, subclassing `AppEvent`; PascalCase past tense (`VoteCreated`); `subject` ClassVar `<context>[.<entity>].<past-verb>` (`votes.created`).
2. Records an aggregate state change → `record_event()` inside the aggregate method; the outbox delivers it on `uow.commit()`. Application-level trigger with no state change → publish directly via `EventBroker` in the interactor.
3. Add a FastStream subscriber in `presentation/faststream/routes/` — never add a published event without a subscriber.
4. `subject` is a published contract: renaming one is a migration, not a rename.

### Add a client-facing domain exception / error code
1. Define the exception with the semantic marker first in its bases (`class UserNotFound(NotFound, UserException)`).
2. If it never reaches an HTTP client, list it in `INTERNAL_ONLY` in `tests/unit/presentation/test_exception_status_map.py` — the drift test fails otherwise.
3. Run `just frontend-generate-api`, then add Russian copy for the new code to `ERROR_MESSAGES` in `frontend/src/lib/api/errors.ts` (a compile-time exhaustiveness guard reports it until you do).

### Add an SSE event
1. Add a member to `SSEEventName` (`application/dto/realtime.py`) — snake_case, single token, **no dots**.
2. Mirror it in `SSEEventMap` (`frontend/src/lib/services/events.svelte.ts`) — the two are kept in sync by hand.

## Core Domain & Interactors
* **Core Layer (`core/`)**: Pure domain entities, value objects, and domain exceptions. Must be free of all I/O frameworks and outer layers — no FastAPI, SQLAlchemy, no `adapters/`/`application/`/`presentation/` imports. **Pydantic is the one allowed exception, and only in two narrow spots**: `core/events/base.py` (`AppEvent` is a `BaseModel` so domain events serialize cleanly over NATS) and `core/vo/fields.py` (validation helpers for value objects). Do not reach for Pydantic elsewhere in `core/` — plain dataclasses are the default for entities and value objects.
* **Application Layer (`application/`)**: Orchestrates interactors and business use cases. Must never import database ORM models directly. Communication with infrastructure happens via abstract interfaces (ports under `application/ports/`) and schemas/DTOs.
* **One gateway port per aggregate**: Each aggregate has a single port under `application/ports/gateways/`, named `XGateway`, that carries both writes (loading and persisting aggregates) and reads (DTO projections returned to callers). Group the read methods at the bottom of the port under a `# Read projections (return DTOs, not aggregates)` comment and prefix them with `read_`. These are **gateways, not repositories, on purpose** — they also serve read DTOs, and we deliberately do **not** split reads into separate CQRS-style query ports; the rationale and the conditions for revisiting live in [ADR-0003](adr/0003-persistence-gateways-over-repositories.md).
* **Ports are `Protocol`, never `ABC`**: Define every port in `application/ports/` as a `typing.Protocol`; do not decorate port methods with `@abstractmethod`. Adapters in `adapters/` **must explicitly subclass** the port they implement (e.g. `class SqlUserGateway(UserGateway): ...`), so `just backend-typecheck` (`ty`) flags any method that drifts from its port — missing method, changed parameters, or a changed return type. Rationale: [ADR-0005](adr/0005-ports-as-protocol-with-explicit-adapter-subclassing.md).

## Services

Services hold logic that is reused across several interactors (or is too cohesive to scatter through them). An interactor is one use case end-to-end; a service is a focused collaborator the use case leans on. Use a service only when the logic is genuinely shared — a single-caller helper usually belongs inline in its interactor. Services are wired in `main/ioc/services.py` (request-scoped). There are two homes, chosen by what the service depends on:

* **`core/services/`** — **pure** domain logic with no ports and no I/O (e.g. `email_login.py`: OTP policy constants plus a code generator). Same purity rules as the rest of `core/`: no FastAPI, SQLAlchemy, Pydantic, or adapter imports. These need no DI wiring when they are plain functions.
* **`application/services/`** — services that orchestrate over **ports** (gateways, id-provider, etc.). They live in the application layer precisely because they touch infrastructure through abstract ports — never concrete adapters or ORM models.

Naming: suffix services with `Service` (the historical `CurrentUserProvider` is the one exception). A port-dependent collaborator that is really an infrastructure concern (password hashing, etc.) is **not** a service — model it as a port in `application/ports/` with an adapter in `adapters/`, so the application layer stays free of concrete libraries.

### Authorization

Gate use cases through `PermissionService.ensure(user, PermissionName(Permissions.X))`, never with hardcoded role checks (`if user.role is UserRole.ORG: ...`). Each permission is a named definition (the `Permissions` enum in `core/vo/permission.py`, seeded as rows in the `permissions` table via migration) that a role can be granted per object. `ORG` is the staff admin role and short-circuits `ensure` — it implicitly holds every permission, including future ones, so it never needs a granted row. Add a new `Permissions` member **and** a seed migration together when introducing a permission so non-`ORG` roles can actually be granted it. Genuine ownership-or-permission checks (e.g. "the owner, or anyone with `notifications:send`") keep the ownership comparison inline and fall back to `ensure` only for the non-owner branch.

Authentication is **enforced inside interactors**, not via FastAPI `Depends`: the current user is resolved through `CurrentUserProvider.require_user()` (`application/services/current_user.py`), backed by the `IdProvider` port (the web adapter reads the session cookie in `adapters/auth/providers/web.py`). FastAPI therefore can't infer which routes need a session, so OpenAPI/Swagger is told **for documentation only** via `require_session_docs` (`presentation/web/security.py`) — an `APIKeyCookie(auto_error=False)` security marker that renders the lock icon + "Authorize" without ever enforcing anything (the interactor stays the single source of truth). Attach it to protected routes alongside `AUTH_RESPONSES` (401/403, `presentation/web/responses.py`): set both on the `APIRouter(...)` constructor for fully-protected routers (they propagate to included sub-routers), or per-operation via `dependencies=[require_session_docs]` for routers that mix public and protected endpoints (e.g. `voting.py`). Public routes carry neither; `VALIDATION_RESPONSES` (422) is the only globally applied response set.

## Persistence & Transaction Management
* **ORM Models**: SQLAlchemy database models live strictly under `adapters/db/models/`. Columns are typed with **standard/SQLAlchemy storage types only** (`str`, `int`, `uuid.UUID`, `datetime`, …) plus native enums (`Mapped[UserRole]` + `postgresql.ENUM(...)`). Do **not** annotate columns with domain value objects (e.g. `Mapped[UserId]`): keeping the ORM in storage types decouples it from `core/` and prevents a VO's underlying type from silently driving the column type (drift with no migration). The trade-off — VO ↔ storage conversion happening in one explicit place (the mapper) instead of implicitly — is intentional.
* **Shared base & mixins** (`models/base.py`, `models/mixins/`): `BaseORM` holds the shared `metadata` (with the `ix`/`uq`/`ck`/`fk`/`pk` naming convention that the constraint-violation handling relies on), the audit `created_at`/`updated_at` columns, and a generic `__repr__`. Most aggregates also mix in `UUIDPrimaryKeyMixin` (`models/mixins/pk.py`) for the time-ordered uuid7 `id` — do not re-declare the PK per model. `AppSettingsORM` is the deliberate exception (singleton `int` PK). `OrderMixin` (`models/mixins/order.py`) adds the deferred-unique `order` column.
* **Enum columns store the value, not the member name**: domain enums are `StrEnum`s (`core/vo/`), and every persisted enum column is declared with the `str_enum_column(EnumCls, name=..., length=...)` helper (`models/base.py`) rather than a hand-rolled `Enum(...)`. The helper fixes `native_enum=False`, `create_constraint=True`, and `values_callable=lambda e: [m.value for m in e]`: SQLAlchemy's default persists the member *name* (`"VISITOR"`); `values_callable` flips it to the *value* (`"visitor"`) so the DB matches what the API, DTOs and frontend already use. Pass `server_default` (and `default`) as the value too (`UserRole.VISITOR.value`). Keep this uniform — a column that stores names is drift, not a variant.
* **VO ↔ storage conversion happens only in mappers**: the mapper is the single seam where domain value objects are constructed from rows (`UserId(orm.id)`, `Email(orm.email)`) and unwrapped back (`model.id`, `model.email.value`). Because `to_model`/`parse_*_dto` must wrap every value, a VO whose base type drifts surfaces as a **type error in the mapper** — caught by `just backend-typecheck`, not at runtime. (Storage-vs-actual-column drift is still Alembic's job.)
* **Gateways**: Concrete SQL queries, database reads, and inserts are isolated in gateway implementations under `adapters/db/gateways/` (one per aggregate/concern). Each implements its aggregate's abstract `gateways/` port (reads and writes). Order methods to mirror the port: aggregate persistence first (`add`/`get`/`save`/`delete`), then `read_*` DTO projections last under the same `# Read projections (return DTOs, not aggregates)` divider, so port and adapter read identically top-to-bottom.
* **Constraint-violation handling**: A gateway must never leak a raw `IntegrityError` for a *known, reportable* conflict — translate it to a domain exception at the boundary so inner layers stay pure. There are two sanctioned styles, chosen by whether the caller needs to hear about the conflict:
  * **Reportable conflict → `translate_integrity_error` (`adapters/db/constraints.py`)**. Force the write with `await session.flush([orm])` *inside* the `with` block so the violation surfaces at the gateway (not later at `uow.commit()`), and map the constraint name to a domain exception: `with translate_integrity_error({"uq_votes_user_id": VoteAlreadyExists}): ...`. It dispatches on the DB constraint name (robust, driver-tolerant — relies on the `uq_`/`fk_`/`ix_` naming convention), raises `from` the original, and **re-raises any unmapped constraint** so an unexpected `NOT NULL`/`CHECK` bug is never swallowed or mislabeled. This is the default — and it is also the race-safe backstop, so do **not** pre-`SELECT` to avoid the insert.
  * **Idempotent marker → `INSERT ... ON CONFLICT DO NOTHING`**. Only when a duplicate is a no-op the caller need not hear about (e.g. `user_flags`: a user either has a flag or not). Race-free at the DB level and avoids the try/except, but it signals "nothing happened" via `rowcount`, never an exception — so do not use it where a conflict must surface as a domain error.
* **Mappers**: ORM model ↔ domain entity translation lives in `adapters/db/mappers/` (one per aggregate). Gateways must map ORM rows to pure domain objects (and back) through these — never leak ORM models out of the adapter layer. When you add a new persisted aggregate, you typically add a model, a mapper, and a gateway together. Mappers that (de)serialize a JSONB column to a dataclass (e.g. `UserMapper`, `AppSettingsMapper`) take an adaptix `Retort` in their constructor; the owning gateway receives the shared `Retort` from DI and passes it down — do not instantiate `Retort()` ad-hoc (adaptix caches per-type morphers, so it is built once and reused).
* **Transaction Management (Unit of Work)**: Database commits and rollbacks in use cases are managed strictly by injecting `uow: UnitOfWork` (from `application/ports/uow.py`) and invoking `await self.uow.commit()`. Do not call raw SQLAlchemy session commits (`session.commit()`) inside interactors. The `UnitOfWork` also tracks aggregates and, on commit, writes their domain events to the transactional outbox in the same transaction (see [Domain Events](#domain-events)) — gateways call `self.uow.register(aggregate)` inside their `add`/`get` methods so the interactor never pulls or publishes those events by hand.
* **Migrations**: **Prefer autogenerated migrations over hand-written ones** — generate via `just backend-generate <name>` (against a running app DB) or `just backend-generate-auto <name>` (boots a throwaway prod-matching Postgres 18 via `backend/scripts/generate_migration.py`, using testcontainers — the same container mechanism as the drift test; use this where no DB is running, e.g. Claude Code on the web), then apply with `just backend-migrate`. **Always review the generated file before committing**: autogenerate emits column **renames** as drop+create (data loss) and can get **server-default** changes wrong, so hand-edit those cases. Autogenerate has `compare_type` on (Alembic's default since 1.12.0), so it detects column **type** drift between the ORM models and the database — which pairs with the mapper's compile-time VO checks to cover both seams. Note that plain Alembic does **not** detect changes to **enum members** (adding/removing/renaming `ENUM` labels), so write those migrations by hand.

## Dependency Injection (Dishka)
* **DI Container**: Wired in `main/di.py` using Dishka providers (defined under `main/ioc/`).
* **Config narrowing**: `EnvConfig` (`adapters/config/models.py`) is the single settings aggregate, but a factory should depend on the **narrowest slice it needs**, never the whole aggregate. The provider that *owns a domain* unpacks that domain's slice from `EnvConfig` (e.g. `StreamProvider` → `NatsConfig`, `BotProvider` → `TelegramConfig`, `MailProvider` → `MailConfig | None`, `PushProvider` → `PushConfig`, `CaptchaProvider` → `TurnstileConfig | None`, `InteractorsProvider` → `OutboxConfig`/`NotificationConfig`). Only genuinely cross-cutting leaves (`WebConfig`, `DebugConfig`, `timezone`) plus the `EnvConfig` root itself stay in `ConfigProvider` (`main/ioc/config.py`). Consuming the full `EnvConfig` is reserved for the composition roots (`parsers.get_config`, `main/scheduler.py`).
* **Serialization (adaptix `Retort`)**: The base `Retort` used to (de)serialize plain-dataclass models is built once in `adapters/serialization.py` (`create_retort`) and provided app-scoped by `SerializationProvider` (`main/ioc/serialization.py`). Inject `Retort` wherever you serialize (mappers via their gateway, the NATS realtime gateway, vendor API clients). Dishka resolves by type, so a configuration that needs different rules gets its **own `NewType` alias** keyed separately — e.g. `RedisRetort` (`adapters/redis/utils.py`) carries Redis-specific loaders/dumpers and is injected as `RedisRetort`, never colliding with the base `Retort`.
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

### Naming standard

Event classes live in `core/events/<context>.py` and subclass `AppEvent` (`core/events/base.py`).

* **Class name** — PascalCase, **past tense**, `<Entity><PastVerb>` (e.g. `VoteCreated`, `VoteDeleted`, `ScheduleChangeUndone`, `MailingCancelled`). An event records something that *already happened*, so the verb is always past tense; if you can't name it in the past tense it probably isn't an event (see the "keep domain events honest" note under [service events](#events-raised-directly-by-interactors-service-events)).
* **`subject` ClassVar** — the NATS/JetStream subject the event is published and subscribed on, and the wire contract. Lowercase, **dot-separated** hierarchy, snake_case within a segment, with the **past-tense verb as the final segment**: `<context>[.<entity>].<verb>` — e.g. `votes.created`, `notifications.broadcast.queued`, `schedule.change.undone`, `users.email_login_code_requested`. The leading segment names the bounded context (`votes`, `notifications`, `schedule`, `users`). Unlike SSE event names (single token, no dots — see [Realtime (SSE)](#realtime-sse)), dots here are intentional: JetStream consumers bind with hierarchical wildcards (`notifications.>`).
* **Stability** — a `subject` is a published contract. Renaming one orphans existing durable consumers and any outbox rows already written with the old subject, so treat changes as a migration, not a rename.

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

Aggregate events are **not** published to NATS on commit — that would be a dual write: if the process dies between the DB commit and the publish, state is persisted but the event is lost ([ADR-0004](adr/0004-transactional-outbox-for-domain-events.md)). Instead, `uow.commit()` serializes each recorded event into an `OutboxEventORM` row (`adapters/db/models/outbox.py`) committed in the **same transaction** as the aggregate change, and a relay delivers it asynchronously:

* **Relay** — `PublishOutboxEvents` (`application/interactors/outbox/`), run as an `IntervalTrigger` job (~seconds) in the scheduler (`main/scheduler.py`). It reads unpublished rows `FOR UPDATE SKIP LOCKED` in creation order (`created_at` with the uuid7 `id` as tiebreaker — rows from one commit share the transaction timestamp), calls `EventBroker.publish_raw(subject, payload, message_id)`, marks them published, and commits. If a publish fails mid-batch, the already-acked prefix is still marked before the error propagates, so only the failed rows are retried next tick.
* **Delivery guarantee** — at-least-once: a row is marked published only after NATS acks it. Consumers stay idempotent; the row id is sent as `Nats-Msg-Id` so JetStream dedups redeliveries within its window. Delivery to *consumers* is bounded by the JetStream stream retention (`presentation/faststream/jstream.py`, `max_age` 24h): once a row is marked published the outbox never resends it, so a consumer outage longer than the stream retention loses events.
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

## Realtime (SSE)

Browser push goes over Server-Sent Events, separate from the domain-event/outbox path: interactors and FastStream consumers publish an `SSEMessage` via `RealtimeGateway` (`adapters/nats/realtime_gateway.py`), which fans out over NATS subjects to every open `/events` stream (`presentation/web/routes/sse.py`). It carries no committed state, so it never touches the `UnitOfWork` or the outbox.

**Every SSE event name is a member of the `SSEEventName` `StrEnum`** (`application/dto/realtime.py`) — never a bare string literal. `SSEMessage.event_name` is typed to the enum, so a typo is a type error, not a silently dead event. To add an event: add a member here, then mirror it in the frontend `SSEEventMap` (`frontend/src/lib/services/events.svelte.ts`).

Naming standard for new events:
* **snake_case, single token — no dots.** The subject is built as `sse.broadcast.{event_name}` / `sse.user.{user_id}.{event_name}` and consumers subscribe with a single-token wildcard (`sse.broadcast.*`). A dot in the name splits into extra subject tokens and silently stops matching the wildcard. (`SSEEventName` being a `StrEnum` means it interpolates straight into the subject and into the SSE `event:` field as its value.)
* Prefer `<entity>_<event>` for new names.
* The backend enum and frontend `SSEEventMap` are kept in sync **by hand** — SSE events are not part of the OpenAPI spec, so `just frontend-generate-api` does not cover them. Every enum value must have a matching `SSEEventMap` key.

**Liveness heartbeat**: the `/events` route injects a named `ping` event after `HEARTBEAT_INTERVAL_SECONDS` (30s) of stream silence — `ping` is the one `SSEEventName` never published via `RealtimeGateway`. Comment-based keepalives are invisible to the browser `EventSource` API, so the frontend watchdog (`HEARTBEAT_TIMEOUT_MS`, 3x the interval, in `events.svelte.ts`) relies on these pings to detect silently dead connections (Wi-Fi roaming, NAT timeouts) and reconnect. If you change the interval, keep it below common proxy idle timeouts (60s) and update the frontend timeout to match.

## Notification Formatting

A notification `body` is stored as a **small, safe HTML subset** so the same text can be highlighted across every delivery channel. The subset is the intersection of what Telegram's HTML parse mode accepts and what the web UI can render: `b`, `strong`, `i`, `em`, `u`, `s`, `a[href]`, `code`, `pre`, `blockquote`. Line breaks are stored as plain `\n` (no `<br>`/`<p>`), which Telegram treats as newlines and the web renders via CSS `white-space: pre-line`.

* **Single sanitization chokepoint**: every notification — broadcast, personal message, schedule-change template — is built into the persisted model in `CreateNotification._to_model` (`application/interactors/notifications/create_notification.py`), which runs the body through the `HtmlSanitizer` port (`application/ports/html_sanitizer.py`, nh3 adapter `adapters/html/sanitizer.py`). `SendNotification` and the realtime SSE DTO both re-read the **persisted, already-sanitized** record, so sanitizing once covers web, Telegram, and push. Never sanitize per-channel.
* **Per-channel rendering**: the web UI renders the stored body with `{@html}` (it is pre-sanitized — see [frontend.md](frontend.md)); the Telegram notifier (`adapters/tgbot/notifier.py`) sends it with `parse_mode=ParseMode.HTML` and only HTML-escapes the plain-text `title`; the push notifier (`adapters/push/push.py`) strips all tags to plain text because OS notifications do not render HTML.
* **Templates**: Jinja notification templates (`adapters/jinja/templates/`) may use the subset tags directly (e.g. `<b>`) to highlight key details. `autoescape=True` keeps `{{ variables }}` escaped, and the central sanitizer is the final safety net, so template-interpolated DB values can never inject markup.
* **Deep-link path**: each notification carries an optional in-app `path` (e.g. `/schedule`), set by the interactor that builds the `NewNotification` (the originating use case knows the target — `PushNotifier` cannot infer it from title/body). It is persisted on `Notification` and flows through both DTOs. The push notifier sends it as the payload `url`, which the service worker navigates to on click (`frontend/src/service-worker.ts`); the web UI makes notification list items and push toasts link to it. `None` falls back to the app root (`/`).
* **Retention**: `PurgeNotifications` (`application/interactors/notifications/`) drops notifications older than `NotificationConfig.retention_days` (default 30), on the `SCHEDULER__NOTIFICATION_RETENTION_CRON` cron. In-app notifications lose relevance shortly after the convention, so the window is bounded to cap per-user growth; mirrors the outbox retention job.

## Profanity Filtering

User-chosen **public** text is screened for profanity behind the `ProfanityFilter` port (`application/ports/profanity_filter.py`, word-list adapter `adapters/profanity/filter.py`). Currently only the username is filtered: `UpdateCurrentUser._update_username` calls `contains_profanity` and raises `UsernameProfanity` (HTTP 400, code `USERNAME_PROFANITY`) before persisting. Feedback text is **intentionally not** filtered — it is private (org-only), so users may vent freely.

The adapter normalizes input before matching (casefold, fold Latin/leet look-alikes to Cyrillic, strip non-letters, collapse repeats), so obfuscated forms (`х.у.й`, `пизд@`, `хуууй`) are still caught. It combines two static word lists under `adapters/profanity/data/`: the vendored CC-BY [LDNOOBW](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words) ru/en lists (used for **exact** normalized-token matches, see `NOTICE`) plus a curated `roots_ru.txt` of unambiguous mat stems (used for **substring** matches to catch inflections). To filter another field, inject the port and call it in that interactor.

## Rate Limiting

Two distinct rate-limiting ports exist — pick by semantics, do not overload one for the other:

* **`RateLockFactory`** (`application/ports/rate_lock.py`): a distributed mutex that also enforces a cooldown, written **only on a successful run**. Use it for "one *successful* action per N seconds" flows where a failure should be retryable immediately (e.g. requesting/sending an email code). A failed attempt does **not** consume the cooldown.
* **`RateLimiter`** (`application/ports/rate_limiter.py`): a fixed-window attempt **counter** that locks a key once a number of attempts is exceeded, regardless of success. Use it to penalize failures — password login brute-force, OTP guessing. Call `hit(key, limit=, window_seconds=)` on each attempt and `reset(key)` after success. It raises `TooManyAttempts`; callers catch and re-raise a flow-specific subclass (`TooManyLoginAttempts`, `TooManyOtpAttempts`) so each feature keeps its own error code/copy.

The Redis adapters live in `adapters/redis/rate_lock.py` and `adapters/redis/rate_limiter.py`. The login interactor passes the client IP in via its input DTO (filled by the web route through `presentation/web/utils.get_client_ip`) so the application layer never touches `Request`.

## Captcha

The unauthenticated `request-login-code` flow is additionally guarded by a captcha, behind the `CaptchaVerifier` port (`application/ports/captcha.py`). The interactor calls `await captcha_verifier.verify(token)` before doing any work; a missing or rejected token raises `CaptchaVerificationFailed` (mapped to HTTP 403). The token rides in on the input DTO so the application layer never touches `Request`.

The feature is **optional and config-gated**, like the other external integrations: when `turnstile` is unset in `EnvConfig` (no `TURNSTILE__SECRET_KEY`), `CaptchaProvider` (`main/ioc/captcha.py`) wires a `NoOpCaptchaVerifier` that accepts everything; when set, it wires `TurnstileCaptchaVerifier` (`adapters/captcha/turnstile.py`), which validates against Cloudflare's siteverify endpoint. A missing token or an explicit negative verdict is always rejected, but if Cloudflare is **unreachable** (transport error or 5xx) the verifier **fails open** — a CDN outage shouldn't lock everyone out of login, and the per-email rate lock still caps abuse. The matching frontend key is `PUBLIC_TURNSTILE_SITE_KEY`.

## Anti-corruption layers (vendor sync)

The third-party sync flows for **cosplay2** and **TicketsCloud** are anti-corruption layers (ACLs): their whole job is to translate a vendor's wire format into our domain model. They sit **behind driven ports** (`application/ports/sources/`), so the `application/` layer depends only on those ports — never on `adapters/`. There are **no** `application → adapters` exceptions in the import-linter contract.

* **Source ports** (`application/ports/sources/`): `CosplaySource` and `TicketsSource` are `Protocol`s whose methods return **neutral application DTOs** (`ExternalNomination`, `ExternalParticipant`, `ExternalTicket`) — never vendor DTOs. The neutral DTOs use a vendor-agnostic `external_id` for the source's id; the interactor maps it onto the domain model's existing `cosplay2_id` / `ticketscloud_ticket_id` field.
* **Source adapters** (`adapters/api/<vendor>/source.py`): `Cosplay2Source` / `TCloudSource` implement the ports. This is where the actual translation lives — grouping/renaming vendor fields, the `event_id → UserRole` mapping, and deciding which vendor records the domain recognizes (e.g. only `APPROVED` requests with a voting title become participants; only `DONE` orders with a barcode become tickets). Because the boundary speaks the domain's language, the interactors that consume them are named for the capability, not the vendor — `interactors/cosplay/sync_cosplay.py` (`SyncCosplay`), `interactors/tickets/sync_tickets.py` (`SyncTickets`), `interactors/tickets/process_ticket_order.py` (`ProcessTicketOrder`) — and together with the `TicketImportService` (`services/tickets_import.py`) they stay vendor-free and unit-testable with a fake source. The vendor name lives only where the vendor actually is: the `adapters/api/<vendor>/` packages, the `main/ioc/<vendor>.py` wiring, and the operator-facing knobs (CLI `sync tcloud` / `cosplay2`, the `SCHEDULER__SYNC_*_CRON` env keys, the `/webhooks/tcloud` URL).
* **Vendor clients** (`adapters/api/<vendor>/client.py`) are thin subclasses of `BaseApiClient` (`adapters/api/base.py`): a small `httpx2.AsyncClient` wrapper whose `_get` loads JSON responses into the plain-dataclass vendor DTOs via the injected adaptix `Retort`. Each endpoint is one explicit async method with a real return type — no decorator magic. httpx2 raises `httpx2.HTTPStatusError` on non-2xx (status at `error.response.status_code`); translate vendor errors here (e.g. 404 → `None` in `TCloudClient.get_order`). The client is now a private detail of its source adapter. The base URL and auth headers are configured on the `httpx2.AsyncClient` in the DI provider (`main/ioc/<vendor>.py`), which also binds the source to its port.
* **Aggregates are never built by the source.** A source returns *what the vendor asserts*; the interactor reconstitutes/merges the aggregate it owns — assigning identity and preserving domain-only fields the vendor doesn't know (`Nomination.is_votable`, the resolved `Participant.nomination_id`). That is why the ports return DTOs, not `Nomination`/`Participant`/`Ticket`.
* If you build a new vendor integration, follow this shape: a thin client, a `*Source` adapter implementing a new port under `application/ports/sources/`, returning neutral DTOs. Do **not** inject a vendor client into the application layer, and do **not** dress a port up with methods that still traffic in vendor DTOs — that hides the coupling without removing it. **Any `application → adapters` import is a bug** and will fail `just backend-import-lint`.

## Presentation Layers
* **HTTP APIs (`presentation/web/`)**: FastAPI routes mapping HTTP requests.
* **Event Streaming & Bots (`presentation/faststream/`, `presentation/tgbot/`)**: FastStream handlers consuming NATS subjects, or Telegram bots handling events. Inject interactors exactly the same way using `@inject` and `FromDishka`.
* **Scheduler (`presentation/scheduler/`)**: APScheduler (v3 `AsyncIOScheduler`) runs periodic sync jobs (`sync_tcloud`, `sync_cosplay2`) as the `scheduler` compose service (composition root: `main/scheduler.py`). Dishka has no APScheduler integration — each job is a closure that opens a fresh REQUEST scope off the system container and resolves the interactor, mirroring the CLI commands. Schedules are cron strings in config (`SCHEDULER__SYNC_*_CRON`, app timezone); unset = job disabled. Change a schedule by editing `.env` and running `docker compose restart scheduler` — no code change. Trigger a sync manually any time via `docker compose run --rm api cli sync tcloud`.
* **Exception Mapping**: Interactors raise pure domain exceptions; the presentation layer catches and maps them to client-safe responses (handlers in `presentation/web/exceptions.py`; every error body is the `ErrorMessage` `{code, details}` schema, including a catch-all handler so unexpected errors become `INTERNAL_ERROR` 500 instead of a leaked traceback).
  * **Status codes via semantic markers, not a leaf registry.** Domain exceptions carry an HTTP-agnostic *marker* base from `core/exceptions/base.py` — `ConstraintViolation` (400), `NotFound` (404), `Conflict` (409), `RateLimited` (429), `AccessDenied` (403) — plus `AuthenticationError` (401) from `core/exceptions/auth.py`. `EXCEPTION_STATUS_MAP` keys on those ~6 markers only; `_resolve_status_code` walks the exception MRO to find one. **To add an exception, inherit the marker that fits its meaning** (listed *first* in the bases so it wins MRO precedence over the feature-grouping base, e.g. `class UserNotFound(NotFound, UserException)`) — do not edit the status map. Markers stay HTTP-free so `core/` remains pure (import-linter still passes).
  * **Drift guard**: `tests/unit/presentation/test_exception_status_map.py` enumerates every concrete `AppException` subclass and fails if one resolves to 500 without being listed in its `INTERNAL_ONLY` set (exceptions that never reach an HTTP client — notification delivery, rate-lock guards, missing-vendor-config). Adding an unmarked, non-internal exception breaks this test by design.
  * **Client-facing code set**: `presentation/web/error_codes.py` derives the codes a client can actually receive (exceptions that resolve to a marker, plus the synthesized `VALIDATION_ERROR`/`HTTP_ERROR`/`INTERNAL_ERROR`). The OpenAPI generator stamps them onto `ErrorMessage.code` as an `enum`, so the frontend gets a typed union and can compile-time-check its error copy is complete (see [api.md](api.md)). The test above reuses the same module — one source of truth for "which exception maps where".

## Logging & Observability
* **Setup**: Logging is configured once per process by `setup_logging()` in `adapters/debug/logging.py`, called from the shared `main/common.py:init()` that every service entrypoint runs. It uses **structlog as a formatting layer over the stdlib `logging`** module (via `ProcessorFormatter` + `foreign_pre_chain`), so plain `logging.getLogger(__name__)` records and structlog records flow through the same pipeline. `setup_logging()` is idempotent — it clears existing root handlers before adding its own, so calling `init()` more than once does not duplicate log lines.
* **Getting a logger**: Use the stdlib pattern everywhere: `logger = logging.getLogger(__name__)` at module level. Do not call `structlog.get_logger()` — the codebase standardises on stdlib loggers.
* **Output format**: Console (`ConsoleRenderer`) by default; JSON (`JSONRenderer`) when `DEBUG__JSON_LOGS=true`. Log level and JSON toggle come from `DebugConfig` (`adapters/debug/config.py`).
* **Environment posture (`APP_ENV`)**: `APP_ENV=dev|staging|prod` is the single source of truth for the debug posture. It's read via `Field(validation_alias="APP_ENV")` (the Python attribute stays `config.env`) — named `APP_ENV` rather than bare `ENV` because pydantic-settings also reads `os.environ`, where a stray ambient `ENV` could silently shadow the `.env` value. `DebugConfig` ships **production-safe defaults** (`enabled=False`, `logging_level=INFO`, `json_logs=True`); `EnvConfig._apply_environment_posture` relaxes them to developer-friendly values (`enabled=True`, `DEBUG`-level, console logs) **only when `APP_ENV=dev`** and the specific `DEBUG__*` var wasn't set explicitly (an explicit value always wins). With `APP_ENV=prod` the app **refuses to start** if `DEBUG__ENABLED=True`, since FastAPI debug mode leaks stack traces in HTTP responses. So leave the derived flags unset in `.env` and just set `APP_ENV`.
* **Structured logging convention**: The processor chain runs `ExtraAdder()`, so anything passed via the stdlib `extra={...}` dict is captured and rendered as top-level fields (queryable in the JSON renderer). Follow these rules when adding log calls (especially in interactors):
  * **Short, static message + fields in `extra`.** Keep the message a fixed human-readable string and put identifiers in `extra` — do not interpolate values into the message *and* repeat them in `extra`. Prefer `logger.info("Subscription created", extra={...})` over `logger.info("Subscription %s created", id, ...)`.
  * **Discrete scalar fields, not whole objects.** Never pass a domain model/dataclass as an extra value — the JSON renderer falls back to `repr`, producing one unqueryable blob and risking unintended field/PII leakage. Pass the specific ids/flags you need instead.
  * **Stringify UUID ids.** `extra` values that are `UUID`-based VOs must be wrapped in `str(...)`; a raw `UUID` renders as `"UUID('…')"` under the JSON renderer. Plain ints/bools/strings need no conversion.
  * **Consistent key names.** Use `actor_id` for the authenticated user performing the action; when a separate subject exists, name it explicitly (e.g. `target_user_id`). Name entity ids by their type (`subscription_id`, `event_id`, `mailing_id`, …).
  * **Verbosity & secrets.** Log one record per significant state change (typically after `commit`); do not log reads/queries. Log security-relevant auth events (login success/failure with a `reason`, lockouts). Never log passwords, OTP/login codes, raw emails, or other PII — `client_ip` is acceptable on failed/blocked logins for abuse correlation.
* **Request correlation**: The web app binds a `request_id` into structlog `contextvars` for every HTTP request via `bind_request_context` (`presentation/web/middlewares.py`, registered last in the factory so it runs outermost). Because the processor chain includes `merge_contextvars`, every log line emitted while handling a request automatically carries that `request_id`; it is also echoed back in the `X-Request-ID` response header (and reused from the incoming header when present). To attach more fields to all logs in a scope, use `structlog.contextvars.bind_contextvars(...)`.
* **Noise control**: Noisy third-party loggers (urllib3, aiogram.event, aiohttp.access) are raised to WARNING, and `uvicorn.access` logs for the `/debug/health` probe are dropped by `_HealthCheckFilter`.
* **Error reporting (Sentry)**: `setup_telemetry()` (`adapters/debug/telemetry.py`) wires Sentry when `DEBUG__SENTRY_DSN` is set. Domain `AppException`s and request-validation errors are filtered out, and request headers / user PII are scrubbed before events are sent.
