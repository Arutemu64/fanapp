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

## Presentation Layers
* **HTTP APIs (`presentation/web/`)**: FastAPI routes mapping HTTP requests.
* **Event Streaming & Bots (`presentation/faststream/`, `presentation/tgbot/`)**: FastStream handlers consuming NATS subjects, or Telegram bots handling events. Inject interactors exactly the same way using `@inject` and `FromDishka`.
* **Exception Mapping**: Interactors raise pure domain exceptions. The presentation layer is responsible for catching and mapping these exceptions to standard client-safe formats (e.g. using exception handlers in `presentation/web/exceptions.py` for FastAPI endpoints).
