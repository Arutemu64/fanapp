# ADR-0040: A Postgres job queue replaces NATS and FastStream; Valkey pub/sub carries SSE

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** maintainer

## Context

Domain events reached their handlers in three hops: `uow.commit()` wrote an
outbox row ([ADR-0004](0004-transactional-outbox-for-domain-events.md)), a relay
in the scheduler copied it to a NATS JetStream stream, and FastStream durable
consumers ran the handlers. Live SSE updates rode the same NATS server as core
pub/sub subjects.

Every guarantee the app needs already lived in Postgres — the outbox made events
durable with the write, `FOR UPDATE SKIP LOCKED` handed rows out once, an
advisory `WorkerLock` stopped a sync running twice. NATS added a second copy of
each event and a second set of delivery rules to keep in step with the first:
JetStream dedup windows, ack policies that drop a message on the first error by
default, `MaxDeliver`, consumer configs the server keeps across deploys, a
24-hour stream retention that silently bounded how long a consumer could be
down, and an fsync interval that was the durability guarantee on a single node.
Service events that guarded no committed state were published straight to NATS,
outside any transaction. For one convention on a 1-vCPU VPS, the event volume is
small; the operational surface was not.

## Decision

We will run domain events as **jobs in Postgres** and drop NATS and FastStream.

- The outbox table becomes `jobs`: `uow.commit()` writes one row per **handler**
  of each event (handler names from the worker's `JobRouter`, injected as
  `EventRoutes`), in the same transaction as the change. Events with no
  aggregate go through `uow.record_events()`, so they are durable too.
- A `worker` service claims due jobs with `UPDATE … WHERE id IN (SELECT … FOR
UPDATE SKIP LOCKED)`, the queue pattern Postgres documents for the clause
  ([SELECT: The Locking Clause](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)).
  A claim leases the job by pushing its `run_at` ahead and commits; a heartbeat
  renews the leases of running jobs, so no transaction stays open while a job
  runs and a dead worker's jobs come due again on their own. Settles are fenced
  by the attempt number.
- Retries use backoff up to a fixed attempt count, then the job is marked
  `failed`; a handler can ask for a specific delay or drop the job outright.
- The LISTEN/NOTIFY wake-up of [ADR-0015](0015-listen-notify-wakes-the-outbox-relay.md)
  moves to the `jobs` table and now wakes the worker; polling stays the backstop.
- Live SSE messages go over **Valkey pub/sub**, already deployed for sessions
  and rate limits. One pub/sub connection per process fans messages out to that
  process's open streams. Pub/sub is at-most-once
  ([Valkey: Pub/Sub](https://valkey.io/topics/pubsub/)), the same as the core
  NATS subjects it replaces, and acceptable because each SSE event only tells a
  client to refetch.
- No backward compatibility: the migration drops `outbox_events` with whatever
  it held, and the NATS stream is not drained.

## Consequences

- One store, one set of delivery rules, one place to look: a stuck or failed job
  is a row with its error, attempts and payload, queryable with SQL.
- Fan-outs are atomic with the state they guard: a broadcast's `SENDING` status
  and every recipient's job commit together, and `CreateNotification` queues the
  channel sends with the notification insert, so a rerun sends nothing twice.
- Two services fewer to run and size (NATS and the FastStream consumer, replaced
  by one worker), and about 100 MiB of memory back on the small host.
- The queue is ours to maintain: lease, heartbeat, backoff and retention are
  application code with tests, where JetStream gave them for free.
- Every job costs a few writes (insert, claim, heartbeat, settle) on the primary
  database. At this app's volume that is noise; at thousands of jobs a second it
  would not be.
- Handlers stay idempotent — delivery is still at-least-once — and a handler
  name stored on queued rows is now the contract that a rename must respect.

## Alternatives considered

- **Keep NATS, drop only FastStream** (raw `nats-py` consumers). Keeps the second
  copy of every event and all of JetStream's delivery rules; removes only the
  framework.
- **Valkey Streams as the queue.** Consumer groups give at-least-once delivery,
  but the queue would again live outside the transaction that records the event,
  so the outbox and a relay would stay — and this Valkey is configured to evict
  keys under memory pressure.
- **A queue library (procrastinate, River-style tools).** Same Postgres design,
  but another dependency with its own schema and worker model for a handful of
  handlers; the hand-written claim/lease loop is a few hundred lines.
