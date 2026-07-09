# ADR-0002: Hexagonal + DDD layering with enforced boundaries

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project maintainers

## Context

The backend integrates several volatile external systems — PostgreSQL, Redis,
NATS, Telegram, and two third-party vendor APIs (cosplay2, TicketsCloud). Left
unstructured, framework and vendor concerns tend to leak into business logic,
making use cases hard to test and vendor changes ripple across the codebase.

We wanted business rules that are pure, unit-testable without infrastructure,
and insulated from any single framework or vendor. Documentation alone does not
hold such boundaries — they erode the moment one "quick" import crosses a layer.

## Decision

We will structure the backend as concentric layers following Clean
Architecture / Hexagonal (ports & adapters) with DDD building blocks:

- `core/` — pure domain (entities, value objects, domain exceptions, domain
  events). No I/O frameworks; Pydantic allowed only in two narrow, documented
  spots.
- `application/` — interactors (use cases) and services, depending on
  infrastructure **only** through abstract ports in `application/ports/`.
- `adapters/` — concrete infrastructure implementing those ports.
- `presentation/` — HTTP, Telegram, FastStream, CLI, scheduler entrypoints.
- `main/` — composition root and DI wiring.

Boundaries are **enforced, not just documented**: `just backend-import-lint`
(import-linter) fails the build if `core/` imports any outer layer or if
`application/` imports `adapters/`/`presentation/` outside sanctioned
exceptions. Vendor integrations sit behind driven ports as anti-corruption
layers, so there are **no** `application → adapters` exceptions.

## Consequences

- Interactors are unit-testable with fakes; domain logic has no framework
  coupling; swapping an adapter (or vendor) does not touch business rules.
- A hard, CI-checked rule set: contributors must route infrastructure through
  ports and cannot take shortcuts across layers. This is upfront ceremony —
  ports, adapters, mappers — that we accept as the cost of isolation.
- Some indirection (e.g. VO ↔ storage conversion confined to mappers) that would
  be unnecessary in a flat app is justified here by the isolation it buys.

See [`docs/backend.md`](../backend.md) for the full working rules.
