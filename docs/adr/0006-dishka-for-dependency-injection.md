# ADR-0006: Dishka for dependency injection

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project maintainers

## Context

The hexagonal design (ADR-0002) means interactors depend on abstract ports that
must be wired to concrete adapters somewhere central, with correct lifetimes:
some dependencies are app-scoped (a shared serialization `Retort`), most are
request-scoped (gateways, unit of work, current-user provider). We also run the
*same* interactors from multiple entrypoints — FastAPI routes, FastStream
consumers, Telegram handlers, CLI commands, and scheduler jobs — so the wiring
must not be FastAPI-specific.

FastAPI's own `Depends` is tied to the request/response cycle and to FastAPI
itself, which does not fit interactors invoked from a CLI command or a cron job.

## Decision

We will use **Dishka** as the DI container, wired in `main/di.py` with providers
under `main/ioc/`, and resolve dependencies by type with explicit scopes.

- Routes and presenters inject interactors with `@inject` + `FromDishka[...]`.
  We do **not** use FastAPI `Depends` for anything Dishka manages.
- Non-HTTP entrypoints (CLI, scheduler) open a fresh REQUEST scope off the system
  container and resolve the interactor the same way.
- Type-keyed resolution: a dependency needing different configuration gets its
  own `NewType` alias (e.g. `RedisRetort` vs. the base `Retort`) so it never
  collides.

## Consequences

- One composition root wires the whole app; the same interactor runs unchanged
  under HTTP, NATS, Telegram, CLI, and the scheduler.
- Scopes are explicit and consistent, avoiding request state leaking into
  app-scoped singletons.
- We take on Dishka as a framework dependency and its scope/provider model as
  something every contributor must learn. `Depends` is reserved for the few
  things genuinely tied to the HTTP request that Dishka does not own.
