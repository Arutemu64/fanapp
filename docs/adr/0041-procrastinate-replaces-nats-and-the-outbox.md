# ADR-0041: Procrastinate on Postgres replaces NATS, FastStream and the outbox

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** maintainer

## Context

Background work reached its handlers through three hops:

1. `uow.commit()` wrote an `outbox_events` row in the producing transaction
   ([ADR-0004](0004-transactional-outbox-for-domain-events.md)).
2. A relay in the scheduler, woken by LISTEN/NOTIFY
   ([ADR-0015](0015-listen-notify-wakes-the-outbox-relay.md)), published the
   row to NATS JetStream.
3. FastStream consumers in a separate `stream` service handled it, with
   redelivery, consumer-config sync and dedup machinery of our own.

The outbox existed only because a broker cannot join a Postgres transaction.
Brandur calls this a "transactionally staged job drain"
([brandur.org/job-drain](https://brandur.org/job-drain)). The outbox table was
already a queue: rows claimed with `FOR UPDATE SKIP LOCKED`, retried with
backoff, woken by NOTIFY. JetStream was a second queue behind it, with its own
failure modes: a stream retention that could drop published events, a dedup
window, and durable configs that outlive deploys.

The scale does not need a broker. The app serves one convention of a few
thousand attendees from a 1-vCPU / 2 GB VPS. Postgres-backed queues are a
reasonable default below a few thousand jobs per second when jobs are tied to
the producing transaction
([DEV](https://dev.to/philip_mcclarence_2ef9475/for-transactional-job-queues-just-use-postgres-k10)).
The known LISTEN/NOTIFY limit is a commit-time global lock that hurt at tens of
thousands of concurrent writers
([Recall.ai](https://www.recall.ai/blog/postgres-listen-notify-does-not-scale)),
and the relay already relied on NOTIFY.

ADR-0040 rejected a separate task queue because it "would duplicate the ack,
retry and outbox machinery JetStream already gives us". A queue that lives in
Postgres replaces both the outbox and JetStream, so that objection no longer
holds.

## Decision

We will queue all background work as
[Procrastinate](https://procrastinate.readthedocs.io/en/stable/) jobs in the app
database, written in the producing transaction. We drop NATS, FastStream and the
outbox.

- **Enqueue.** `uow.commit()` pulls recorded events and enqueued commands. It
  takes the psycopg connection under the session's open transaction and writes
  one job per subscribed task in one `batch_defer_jobs_async` call on that
  connection (`adapters/procrastinate/job_queue.py`). This is Procrastinate's
  external-connection defer, available since 3.8.0
  ([docs](https://procrastinate.readthedocs.io/en/stable/howto/production/external_connection.html)).
  There is no relay and no dual write.
- **Nothing in memory.** Every subscriber, including one that only touches this
  database, runs as its own job. A crash or deploy between the commit and the
  work never loses it, and one subscriber's retry never reruns another.
- **Routing.** `Message.subject` stays the routing key. The `subscriber`
  decorator (`presentation/worker/subscriber.py`) registers a task per
  subscriber in a blueprint per context. The composition root hands the
  subject → tasks table to the adapter. A message with no subscriber is refused
  at commit (`UnroutedMessageError`), and a unit test fails the build on one.
- **Worker.** A `worker` service (`main/worker.py`) replaces `stream`. It runs
  Procrastinate's async worker on its own psycopg pool, with concurrency 8,
  LISTEN/NOTIFY plus a 5 s polling backstop, and a heartbeat. It opens a Dishka
  REQUEST scope per job and uses a Sentry worker middleware that continues the
  producer's trace.
- **Retries.** `BoundedBackoff` waits 1 s, 5 s, 30 s, 2 min, then 5 min, for 20
  runs at most. A `NotificationRetryAfter` waits the delay the channel asked
  for.
- **Recovery and retention.** Two periodic tasks: `retry_stalled_jobs` every
  5 min, which is Procrastinate's documented recipe for jobs of dead workers,
  and `prune_finished_jobs` daily.
- **Schema.** Procrastinate's schema SQL for 3.10.0 is vendored and applied by
  an Alembic revision. Alembic's `include_name` keeps autogenerate off the
  `procrastinate_*` tables.
- **Cutover.** A data migration turns every undelivered outbox row into its
  jobs, then drops `outbox_events` and its trigger. It refuses to run if an
  undelivered row has no subscriber, rather than drop that row unseen.
- **SSE.** SSE fan-out moves from core NATS to Redis pub/sub
  (`adapters/redis/realtime_gateway.py`). Both are fire-and-forget, and SSE
  carries no committed state. Each api process holds one pattern subscription
  and routes messages to its streams itself.

## Consequences

- **Fewer moving parts.** One service and one durable store fewer: NATS (96 MiB)
  is gone, and the stream consumer becomes the worker. About 1,700 lines of
  relay, broker and consumer-config code go with them. Steady-state memory falls
  from 1792 to 1696 MiB.
- **Stronger delivery.** A job commits with its cause, and no stream retention
  can expire it unconsumed. The fan-outs (`ProcessBroadcast`,
  `SendScheduleChangeNotifications`) now queue their notifications in the same
  commit that moves the mailing to SENDING. `NotificationCreated` is queued only
  for a newly inserted notification, so a rerun no longer re-sends on every
  channel.
- **Queue load sits on the primary database.** Job churn creates dead tuples,
  so long-open transactions must stay off this database: they stop vacuum
  reclaiming queue rows ([brandur.org/postgres-queues](https://brandur.org/postgres-queues)).
  At this volume the load is negligible.
- **We own the schema upgrades.** Procrastinate tracks no applied version
  ([migrations](https://procrastinate.readthedocs.io/en/stable/howto/production/migrations.html)),
  so a release that changes its schema needs a hand-written Alembic revision
  running that release's vendored scripts. Renovate flags procrastinate majors
  for review.
- **Stored names are contracts.** Task names are stored on job rows, so renaming
  a task, like renaming a subject, is a migration.
- **The worker's DB access is undocumented upstream.** Procrastinate documents
  the external connection for raw psycopg, not SQLAlchemy. We reach it through
  `AsyncConnection.get_raw_connection().driver_connection`, which bypasses
  SQLAlchemy's adapter mutex; one session never runs two statements at once, so
  this is safe. An integration test asserts that rolled-back jobs vanish with
  their transaction.
- **Deploy caveat.** Messages already in JetStream but unconsumed at the deploy
  that removes NATS are lost; the deploy guide says to cut over when nothing is
  in flight.
- **Upstream maturity.** Procrastinate's authors still want "real monitoring
  tools before we call this really ready for production"
  ([discussions](https://procrastinate.readthedocs.io/en/stable/discussions.html)).
  The jobs are plain Postgres rows, which is the monitoring we have (deployment
  guide, "Inspecting background jobs").

## Alternatives considered

- **Keep NATS; tune it.** This keeps two queues and a relay between them for a
  volume one table handles. Rejected: the operational weight buys nothing at
  this scale.
- **Roll our own executor on the outbox table.** The relay already had about
  80% of it. The missing 20% is the subtle part: concurrent workers, heartbeats,
  stalled-job recovery, deduplicated cron and abort. "Most work queue
  implementations in SQL are wrong"
  ([2ndQuadrant](https://www.2ndquadrant.com/en/?p=9279)).
  Rejected in favour of a maintained library with those parts.
- **PgQueuer.** Its examples and fast path are built on asyncpg, while the app
  standardised on psycopg 3
  ([ADR-0018](0018-psycopg-3-as-the-postgres-driver.md)).
- **Dispatch domain events in memory after commit.** A crash or deploy between
  the commit and the dispatch loses the work: the exact failure ADR-0004 fixed.
  In-memory handlers would also run external I/O (Telegram, VK, push) inside
  api requests on a single vCPU. Rejected.
- **Postgres LISTEN/NOTIFY for SSE.** NOTIFY payloads are capped below 8000
  bytes ([PostgreSQL: NOTIFY](https://www.postgresql.org/docs/current/sql-notify.html))
  and every NOTIFY takes the commit-time lock above. Redis pub/sub was already
  deployed and costs nothing extra.
