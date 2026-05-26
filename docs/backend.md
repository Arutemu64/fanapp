# Backend Architectural Guidelines

## Core Domain & Interactors
* **Core Layer (`core/`)**: Pure domain entities, value objects, and domain exceptions. Must be completely free of external frameworks (absolutely no FastAPI, SQLAlchemy, or Pydantic imports).
* **Application Layer (`application/`)**: Orchestrates interactors and business use cases. Must never import database ORM models directly. Communication with infrastructure happens via abstract interfaces (gateways/repositories under `application/ports/`) and schemas/DTOs.

## Persistence & Transaction Management
* **ORM Models**: SQLAlchemy database models live strictly under `adapters/db/models/`.
* **Repositories/Gateways**: Concrete SQL queries, database reads, and inserts are isolated in repository implementations under `adapters/db/gateways/`.
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
