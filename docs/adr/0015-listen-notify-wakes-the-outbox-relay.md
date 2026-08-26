# ADR-0015: LISTEN/NOTIFY wakes the outbox relay, polling stays the backstop

- **Status:** Accepted
- **Date:** 2026-08-26
- **Deciders:** Backend

## Context

Aggregate domain events are delivered through a transactional outbox
([ADR-0004](0004-transactional-outbox-for-domain-events.md)): `uow.commit()`
writes an `outbox_events` row in the same transaction as the state change, and a
relay in the scheduler (`PublishOutboxEvents`) forwards undelivered rows to NATS.

The relay ran as a fixed `IntervalTrigger` every 2 s. That interval is the
dominant latency in the whole notification path — everything downstream (NATS →
FastStream → SSE → browser) is already near-instant — so a user waited on
average ~1 s, worst case ~2 s, for a notification the system had already
committed. For a live-event app where "a notification just fired" should feel
immediate, that is the one hop worth removing.

Two directions were considered. Simply shortening the poll interval lowers
latency but only linearly, and it trades latency for idle database load that
scales with how tight you set it. Postgres `LISTEN/NOTIFY` instead lets the
relay be *pushed*: it wakes the moment a row is inserted. The catch is that
`NOTIFY` is not durable — it is delivered only to connections currently
listening and is dropped if none are, so using it as the delivery mechanism
would reintroduce exactly the lost-event failure the outbox exists to prevent.

## Decision

We will keep the durable outbox poll and add `LISTEN/NOTIFY` as a best-effort
speed layer on top of it — a hybrid, not a replacement.

- An `AFTER INSERT ... FOR EACH STATEMENT` trigger on `outbox_events` fires
  `pg_notify('outbox_new', '')` (hand-written migration — autogenerate neither
  emits nor diffs triggers). Statement-level with a constant empty payload so a
  multi-row commit coalesces into one delivery; `NOTIFY` fires at COMMIT, so the
  listener only wakes once the rows are durably visible.
- `PostgresOutboxSignal` (`adapters/db/outbox_signal.py`, behind the
  `OutboxSignal` port) holds one dedicated asyncpg `LISTEN` connection outside
  the SQLAlchemy pool, with a supervisor that reconnects on drop and nudges a
  drain on every (re)connect.
- The scheduler's relay is now a dedicated loop that drains on each signal and
  re-arms an edge-triggered latch before draining, so a signal arriving
  mid-drain is not lost. `OutboxConfig.poll_interval_seconds` becomes the
  backstop bound on worst-case latency (relaxed 2 s → 10 s), not the everyday
  latency.

## Consequences

- Everyday delivery latency drops from ~1 s average to the time for one NOTIFY
  round-trip plus a drain (tens of ms), while idle database load *falls*,
  because the backstop poll is now 5× slower.
- The at-least-once guarantee is unchanged: correctness rests entirely on the
  poll and the `FOR UPDATE SKIP LOCKED` drain. A missed or undelivered `NOTIFY`
  degrades latency to one backstop interval; it never loses an event. This is
  the load-bearing invariant — a future change must not make delivery *depend*
  on the notification.
- The scheduler now holds a second, long-lived Postgres connection (the LISTEN
  socket) separate from its pool. It is labelled in `pg_stat_activity` via
  `application_name` and must stay off the pool, since a LISTEN connection is
  pinned for the life of the subscription.
- The channel name (`outbox_new`) is a contract split across two places — the
  migration and `OUTBOX_CHANNEL` in the adapter — so changing it is a migration,
  not a rename.
- The relay is a hand-rolled asyncio loop rather than an APScheduler job. It is
  the only push-driven task in the scheduler; the cron jobs are untouched.

## Alternatives considered

- **Just lower the poll interval.** One-line change, no new machinery, but
  latency is bounded by the interval and low latency costs proportional idle DB
  load. It cannot reach "instant" without hammering the database.
- **Replace polling with LISTEN/NOTIFY.** Genuinely instant, but a dropped
  notification is a permanently lost event — it defeats the outbox. Rejected on
  correctness.
- **Logical replication / CDC (Debezium, `wal2json`).** The lowest-latency,
  highest-throughput option and the industry answer at tens-of-thousands of
  events per second. Far too much operational weight for this app's volume, and
  it would add a streaming-platform dependency we otherwise have no need for.
