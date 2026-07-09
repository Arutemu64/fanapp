# ADR-0005: Ports as `Protocol` with explicit adapter subclassing

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project maintainers

## Context

Ports live in `application/ports/` and must not create any inward dependency
from adapters onto the application layer. The common Python idiom — an abstract
base class with `@abstractmethod` — has two drawbacks here: `ABC` inheritance
couples the adapter's class hierarchy to the application layer, and
`@abstractmethod` only catches a *missing* method at instantiation, not a method
whose signature has silently drifted from the port.

We wanted the boundary to be checked by the type checker (`ty`), catching drift
— changed parameters or return types — at check time, not at runtime.

## Decision

We will define every port as a `typing.Protocol`, without `@abstractmethod`.

- Structural typing keeps `application/` free of any inward dependency.
- Adapters in `adapters/` **must explicitly subclass** the port they implement
  (e.g. `class SqlUserGateway(UserGateway): ...`). The explicit inheritance turns
  structural typing into *checked nominal* typing: `just backend-typecheck`
  flags any method that drifts from its port — missing, changed parameters, or
  changed return type.

## Consequences

- Signature drift between a port and its adapter is a **type error**, caught in
  CI before runtime.
- The application layer stays import-clean — adapters depend on ports, never the
  reverse.
- A small convention to remember: adapters must name their port in the base
  list. It is not optional decoration — it is what makes the check work.
