# Backend Architectural Guidelines

## Core Domain & Interactors
* **Core Layer (`core/`)**: Pure domain entities, value objects, and domain exceptions. Must be completely free of external frameworks (absolutely no FastAPI, SQLAlchemy, or Pydantic imports).
* **Application Layer (`application/`)**: Orchestrates interactors and business use cases. Must never import database ORM models directly. Communication with infrastructure happens via abstract interfaces (ports under `application/ports/`) and schemas/DTOs.
* **Command/Query Port Split (CQRS-style)**: Ports are split by intent. Writes (loading and persisting aggregates) go through `application/ports/repositories/`; reads (projections returned to callers) go through `application/ports/queries/`. When adding a read, add a query port — do not extend a repository.

## Persistence & Transaction Management
* **ORM Models**: SQLAlchemy database models live strictly under `adapters/db/models/`.
* **Repositories/Gateways**: Concrete SQL queries, database reads, and inserts are isolated in gateway implementations under `adapters/db/gateways/` (one per aggregate/concern). These implement the abstract `repositories/` and `queries/` ports.
* **Mappers**: ORM model ↔ domain entity translation lives in `adapters/db/mappers/` (one per aggregate). Gateways must map ORM rows to pure domain objects (and back) through these — never leak ORM models out of the adapter layer. When you add a new persisted aggregate, you typically add a model, a mapper, and a gateway together.
* **Transaction Management (Unit of Work)**: Database commits and rollbacks in use cases are managed strictly by injecting `uow: UnitOfWork` (from `application/ports/uow.py`) and invoking `await self.uow.commit()`. Do not call raw SQLAlchemy session commits (`session.commit()`) inside interactors. The `UnitOfWork` also tracks aggregates and dispatches their domain events on commit (see [Domain Events](#domain-events)) — gateways call `self.uow.register(aggregate)` inside their `add`/`get` methods so the interactor never pulls or publishes those events by hand.
* **Migrations**: Generate and apply database migrations strictly via Alembic CLI helpers (`just backend-generate <name>` and `just backend-migrate`).

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

When an event directly records a state change on an aggregate, raise it inside the aggregate method using `record_event()`. The interactor does **not** publish these — the `UnitOfWork` dispatches them automatically. The gateway registers the aggregate when it is added or loaded, and `uow.commit()` publishes the recorded events *after* the transaction is durable:

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
await self.uow.commit()  # commits, then publishes VoteCreated
```

`Vote` and `ScheduleChange` follow this pattern; their gateways register the aggregate in every `add`/`get` method. The `UnitOfWork` pulls events from each registered aggregate exactly once (the internal event list is cleared on dispatch) and publishes strictly **after** the DB commit, so a rolled-back transaction never emits events. When you add a new aggregate that records events, register it in its gateway's `add`/`get` methods — that is the only wiring required.

> Note: this is still a dual write (DB commit, then in-process publish). If the process dies between the two, events are lost. The `UnitOfWork` is the natural place to later adopt a transactional outbox if at-least-once delivery is ever required.

### Events raised directly by interactors (service events)

Some events are not tied to a single aggregate's committed state change — they are application-level triggers to infrastructure (e.g. "queue a notification for these users", "send an email code"). These are constructed and published directly in the interactor via an injected `EventBroker`, and are **not** routed through the `UnitOfWork`:

```python
# application/interactors/notifications/send_broadcast.py
await self.events_broker.publish(
    BroadcastQueued(mailing_id=mailing.id, body=data.body, roles=data.roles)
)
```

`NotificationQueued`, `BroadcastQueued`, and `MailingCancelled` follow this pattern. The user email-code events (`EmailLoginCodeRequested`, `EmailConfirmationCodeRequested`) are also treated as service events: although they are recorded on the `User` aggregate, they represent "send a code" commands with no reliable commit boundary (some flows publish them without persisting any state), so the `User` aggregate is **not** registered with the `UnitOfWork` and those interactors publish via `EventBroker` directly. Rule of thumb: inject `EventBroker` into an interactor **only** for service events; aggregate state-change events flow through `uow.commit()`.

## Rate Limiting

Two distinct rate-limiting ports exist — pick by semantics, do not overload one for the other:

* **`RateLockFactory`** (`application/ports/rate_lock.py`): a distributed mutex that also enforces a cooldown, written **only on a successful run**. Use it for "one *successful* action per N seconds" flows where a failure should be retryable immediately (e.g. requesting/sending an email code). A failed attempt does **not** consume the cooldown.
* **`RateLimiter`** (`application/ports/rate_limiter.py`): a fixed-window attempt **counter** that locks a key once a number of attempts is exceeded, regardless of success. Use it to penalize failures — password login brute-force, OTP guessing. Call `hit(key, limit=, window_seconds=)` on each attempt and `reset(key)` after success. It raises `TooManyAttempts`; callers catch and re-raise a flow-specific subclass (`TooManyLoginAttempts`, `TooManyOtpAttempts`) so each feature keeps its own error code/copy.

The Redis adapters live in `adapters/redis/rate_lock.py` and `adapters/redis/rate_limiter.py`. The login interactor passes the client IP in via its input DTO (filled by the web route through `presentation/web/utils.get_client_ip`) so the application layer never touches `Request`.

## Presentation Layers
* **HTTP APIs (`presentation/web/`)**: FastAPI routes mapping HTTP requests.
* **Event Streaming & Bots (`presentation/faststream/`, `presentation/tgbot/`)**: FastStream handlers consuming NATS subjects, or Telegram bots handling events. Inject interactors exactly the same way using `@inject` and `FromDishka`.
* **Scheduler (`presentation/scheduler/`)**: APScheduler (v3 `AsyncIOScheduler`) runs periodic sync jobs (`sync_tcloud`, `sync_cosplay2`) as the `scheduler` compose service (composition root: `main/scheduler.py`). Dishka has no APScheduler integration — each job is a closure that opens a fresh REQUEST scope off the system container and resolves the interactor, mirroring the CLI commands. Schedules are cron strings in config (`SCHEDULER__SYNC_*_CRON`, app timezone); unset = job disabled. Change a schedule by editing `.env` and running `docker compose restart scheduler` — no code change. Trigger a sync manually any time via `docker compose run --rm api cli sync tcloud`.
* **Exception Mapping**: Interactors raise pure domain exceptions. The presentation layer is responsible for catching and mapping these exceptions to standard client-safe formats (e.g. using exception handlers in `presentation/web/exceptions.py` for FastAPI endpoints).
