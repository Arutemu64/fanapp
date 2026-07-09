# ADR-0003: Persistence gateways over repositories (no CQRS split)

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project maintainers

## Context

A strict DDD repository returns only aggregates. But many use cases here need
read-side **projections** — DTOs shaped for a caller — that never reconstitute a
full aggregate. The textbook answer is a CQRS-style split: a repository port for
writes and a separate query port for reads.

At this project's scale that split turned out to be pure ceremony: a single class
implemented both ports, and DI simply aliased it twice. It added surface area
without buying the independent scaling or divergent read models that justify
CQRS.

## Decision

We will define **one gateway port per aggregate** under
`application/ports/gateways/`, named `XGateway`, carrying **both** writes
(load/persist aggregates) and reads (DTO projections).

- Read methods are grouped at the bottom under a
  `# Read projections (return DTOs, not aggregates)` divider and prefixed
  `read_`.
- We call these **gateways, not repositories, on purpose** — they serve read
  DTOs in addition to aggregates, and the naming matches their `SqlXGateway`
  implementations.
- A dedicated read port is introduced **only if** a read model genuinely
  diverges from its aggregate (different store, independent scaling).

## Consequences

- Less boilerplate: one port, one adapter, one DI registration per aggregate.
- Read and write concerns live together, ordered consistently port-to-adapter,
  which keeps navigation predictable.
- We give up the clean CQRS separation up front. The escape hatch is explicit:
  split only when a read model actually diverges — reversing this per-aggregate
  is cheap, so we default to the simpler shape.
