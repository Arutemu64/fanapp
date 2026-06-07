# Backend Architectural Guidelines

## Core Domain & Interactors
* **Core Layer (`core/`)**: Pure domain entities, value objects, and domain exceptions. Must be completely free of external frameworks (absolutely no FastAPI, SQLAlchemy, or Pydantic imports).
* **Application Layer (`application/`)**: Orchestrates interactors and business use cases. Must never import database ORM models directly. Communication with infrastructure happens via abstract interfaces (ports under `application/ports/`) and schemas/DTOs.
* **Command/Query Port Split (CQRS-style)**: Ports are split by intent. Writes (loading and persisting aggregates) go through `application/ports/repositories/`; reads (projections returned to callers) go through `application/ports/queries/`. When adding a read, add a query port — do not extend a repository.

## Persistence & Transaction Management
* **ORM Models**: SQLAlchemy database models live strictly under `adapters/db/models/`.
* **Repositories/Gateways**: Concrete SQL queries, database reads, and inserts are isolated in gateway implementations under `adapters/db/gateways/` (one per aggregate/concern). These implement the abstract `repositories/` and `queries/` ports.
* **Mappers**: ORM model ↔ domain entity translation lives in `adapters/db/mappers/` (one per aggregate). Gateways must map ORM rows to pure domain objects (and back) through these — never leak ORM models out of the adapter layer. When you add a new persisted aggregate, you typically add a model, a mapper, and a gateway together.
* **Transaction Management**: Database commits and rollbacks in use cases are managed strictly by injecting `trx: TransactionManager` (from `application/ports/trx`) and invoking `await self.trx.commit()`. Do not call raw SQLAlchemy session commits (`session.commit()`) inside interactors.
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

When an event directly records a state change on an aggregate, raise it inside the aggregate method using `record_event()`. The interactor then dispatches all collected events after the commit via `pull_events()`:

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

# application/interactors/voting/add_vote.py
vote = Vote.create(user_id=..., participant_id=...)
await self.vote_repo.add(vote)
await self.trx.commit()
for event in vote.pull_events():
    await self.events_broker.publish(event)
```

`ScheduleChange` and `Vote` follow this pattern. The `pull_events()` call clears the aggregate's internal event list, so events are dispatched exactly once.

### Events raised directly by interactors

Some events are not tied to a single aggregate's state change — they are application-level triggers to infrastructure (e.g. "queue a notification for these users"). These may be constructed and published directly in the interactor without going through an aggregate:

```python
# application/interactors/notifications/send_broadcast.py
await self.events_broker.publish(
    BroadcastQueued(mailing_id=mailing.id, body=data.body, roles=data.roles)
)
```

`NotificationQueued`, `BroadcastQueued`, and `MailingCancelled` follow this pattern.

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
