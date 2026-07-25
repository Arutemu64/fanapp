# ADR-0010: HTTP-triggered background jobs use a status row, outbox and durable consumer

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** maintainer

## Context

Organizers needed to trigger a Cosplay2 / TicketsCloud sync from the web app.
Until now the only manual trigger was `docker compose run --rm api cli sync tcloud`,
which requires SSH to the server; everything else was passive (cron, plus an
optional TicketsCloud webhook). Both `SCHEDULER__SYNC_*_CRON` keys default to
`None`, so a deployment can have no automatic sync at all, and an organizer who
fixes a participant mid-contest has no way to make it visible before the next
tick.

Two facts constrain how this can be built:

1. `api`, `faststream` and `scheduler` are **separate containers**
   (`docker-compose.yml`). Work started in-process in the API dies with the API
   container on the next deploy and cannot be deduplicated across replicas.
2. A full TicketsCloud sync is **unbounded** — `TCloudSource.fetch_all_tickets()`
   paginates every order and `SyncTickets` commits in batches — so it can outlive
   an HTTP request.

The broadcast flow (`SendBroadcast` → `Mailing` row → outbox → durable NATS
consumer) already solved the same shape for notifications, so the question was
whether to reuse it or reach for something lighter.

## Decision

We will trigger long-running work over HTTP by **writing a status-row aggregate
and a domain event in one transaction, returning 202, and doing the work in a
durable NATS consumer** — never with in-process background tasks.

Concretely, for sync:

- `SyncRun` (`core/models/sync_run.py`) is the status aggregate, mirroring
  `Mailing`. `RequestSync` authorizes, writes a `PENDING` row, records
  `SyncRequested`, commits, and returns 202 with `Location: /sync/sources`.
- The outbox relay publishes the event; `run_requested_sync`
  (`presentation/faststream/routes/sync.py`) runs the sync in the stream service.
- **All three triggers** — HTTP, cron and CLI — go through `ExecuteCosplaySync` /
  `ExecuteTicketsSync`, so every run is recorded and participates in the guard.
  Calling `SyncCosplay` / `SyncTickets` directly bypasses both.
- Concurrency is enforced by a **partial unique index**,
  `uq_sync_runs_active` on `sync_runs (source) WHERE finished_at IS NULL`, not a
  Redis lock: it gives deduplication and the status resource in one mechanism and
  matches the existing `translate_integrity_error` idiom.
- Unattended runs authenticate as the seeded system user and pass the same
  `ensure(Permission.SYNC_RUN)` check, granted by migration.

## Consequences

- Work survives an API deploy, and a crash between commit and publish cannot
  lose the request (ADR-0004's guarantee, inherited).
- "Last synced" is honest: it reflects cron and CLI runs, not just button presses.
- A manual sync can no longer overlap a scheduled one — previously nothing
  prevented two concurrent full sweeps of the same vendor API.
- The status row is **operational bookkeeping modeled as a domain aggregate**.
  "Sync run" is not in the convention's ubiquitous language. We accept this for
  consistency with `Mailing`, and because the aggregate is load-bearing rather
  than decorative: `record_event()` requires an `AggregateRoot`, so demoting it to
  a plain table would cost the outbox guarantee.
- `SyncRequested` is **a command carried on the event channel**. In EventStorming
  terms "sync Cosplay2" is a command, not a past-tense fact; we name it past-tense
  and route it through the outbox because that is the durable transport we have.
  Pragmatic reuse, not a textbook fit — worth knowing before copying the pattern.
- A crashed worker wedges the unique index, so `SyncRunTracker.reap_stale` must
  exist and stay correct; without it all syncing for that source stops forever.
- Losing the system user's `sync:run` grant silently disables unattended syncing.
  An integration test asserts the grant, and the grant lives in the same migration
  as the enum member so a rebase cannot separate them.
- Two near-identical `Execute*Sync` interactors instead of one. Dishka resolves
  constructor dependencies eagerly and each vendor config provider raises when
  unset, so a single dispatching interactor would fail to resolve on a
  single-vendor deployment. Do not "simplify" them back into one.

## Alternatives considered

- **FastAPI `BackgroundTasks`.** Rejected: the task dies with the API container
  on deploy, cannot be deduplicated across replicas, and leaves no record — the
  standard advice is to use an external worker for anything that matters.
- **Run the sync inline in the request**, like `POST /tickets/generate`. Rejected:
  a full TicketsCloud sweep is unbounded and would outlive the HTTP timeout.
- **A Redis lock with no status row.** Rejected: it gives mutual exclusion but no
  answer to "did it work?" after a page refresh — the actual question an organizer
  on flaky convention wifi is asking — and would need a second mechanism anyway.
- **Let the consumer create the run row**, dropping the `PENDING` state and the
  `run_id` on the event. Simpler, but the 409 would then happen where it cannot
  reach the user, so a busy button would respond with silence.
- **Attribute unattended runs to `NULL`.** Rejected: `NULL` already means "the
  user was deleted" via `ondelete="SET NULL"` on `schedule_changes` and `mailings`;
  reusing it would make the two cases indistinguishable in the audit trail.
