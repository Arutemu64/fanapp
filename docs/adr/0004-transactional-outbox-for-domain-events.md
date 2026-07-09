# ADR-0004: Transactional outbox for domain-event delivery

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project maintainers

## Context

Aggregate state changes raise domain events that must be published to NATS and
consumed by FastStream subscribers. Publishing to NATS *after* the database
commits is a **dual write**: if the process dies between the DB commit and the
publish, the state is persisted but the event is lost — silently. For events
that guard committed state (a vote created, a broadcast queued), that loss is a
correctness bug, not a hiccup.

## Decision

We will deliver aggregate domain events through a **transactional outbox**.

- `uow.commit()` serializes each recorded aggregate event into an
  `OutboxEventORM` row committed in the **same transaction** as the aggregate
  change. Aggregates record events via `record_event()`; the `UnitOfWork` pulls
  and writes them — interactors never publish aggregate events by hand.
- A relay job (`PublishOutboxEvents`, an interval-triggered scheduler job) reads
  unpublished rows `FOR UPDATE SKIP LOCKED`, publishes to NATS, and marks them
  published only after an ack — **at-least-once** delivery. The row id rides as
  `Nats-Msg-Id` so JetStream dedups redeliveries; consumers stay idempotent.
- A purge job drops delivered rows past a retention window.
- **Service events** (application-level triggers that guard no committed state —
  "send a login code", "queue a notification") stay direct via `EventBroker` and
  do **not** go through the outbox. SSE/realtime uses a separate
  `RealtimeGateway` and is unaffected.

## Consequences

- Domain-event delivery is atomic with the write: a rolled-back transaction
  never emits events, and a crash never drops one.
- The cost is one poll-interval of latency and an extra table plus two scheduler
  jobs (relay + purge).
- Contributors must keep the two paths distinct: aggregate state-change events
  flow through `uow.commit()`; only service events are published directly.
  Injecting `EventBroker` into an interactor is the signal that an event is a
  service event.

See [`docs/backend.md`](../backend.md#transactional-outbox) for the working
rules and naming standard.
