# ADR-0009: External sync runs recorded in an append-only audit log

- **Status:** Accepted
- **Date:** 2026-07-23
- **Deciders:** Project maintainers

## Context

Cosplay2 (nominations/participants) and TicketsCloud (tickets) syncs run via
scheduler cron jobs and CLI commands. Orgs asked for a tools page that can
trigger a sync manually and show when the last sync happened. That needs
persisted sync-run state, and two questions had to be settled:

1. **How to store "last synced"** — a single mutable status row per source, or
   an append-only log of runs?
2. **Who "is" the scheduler/CLI** when a run is recorded — a synthetic system
   user, or no user at all?

Scale is tiny (a handful of runs per day per source), but failures matter: a
sync that quietly stops working before the festival is exactly what this page
must make visible.

## Decision

We will record every finished sync attempt as a row in the append-only
`sync_runs` table (`SyncRun` aggregate; `SqlSyncRunGateway`), and **derive**
"last synced" as the newest `completed` row per source — there is no mutable
status row. This follows the common sync-log design (e.g.
[Hightouch warehouse sync logs](https://hightouch.com/docs/syncs/warehouse-sync-logs),
[Red-Gate on audit-log schema design](https://www.red-gate.com/blog/database-design-for-audit-logging/)):
the log answers both "when did it last work" and "what has been failing since".

Scheduler and CLI keep running under the **system identity**
(`RawIdProvider` in the system DI container) with no permission checks; a run
row is attributed by an explicit `trigger` value (`manual` / `schedule` /
`cli`) plus a nullable `started_by_user_id` that is set only for manual runs.
This mirrors the audit-trail practice of an explicit actor/trigger type instead
of a fake "system user" account (see e.g.
[actor-type audit schemas](https://www.intelligentgraphicandcode.com/development/audit-trails)).
The permission gate (`sync:run`) and the per-source rate lock live only in the
web-facing `RunSync` interactor.

`SyncRunRecorderService` writes the row: on success in the same commit as the
sync's final batch (atomic), on failure after rolling back the broken
transaction so the failed row survives.

## Consequences

- Failure history is first-class: the page shows recent runs with error
  messages, not just a timestamp; a failed run never moves "last synced".
- Deriving the timestamp needs a `MAX(finished_at)` query instead of a single
  row read — negligible at this volume, and the table needs no retention job
  for the same reason. If volume ever grows, add a purge interactor like
  `PurgeOutboxEvents` rather than switching to a status row.
- Runs that die mid-process (crash, OOM) leave no row at all — the log records
  finished attempts, not liveness. Concurrency guards come from the Redis rate
  lock, not the table.
- Scheduler/CLI stay usable without a database user; anyone reading the log
  must join on the trigger, not assume a user is always present.

## Alternatives considered

- **Mutable per-source status row** — simpler reads, but loses failure history,
  needs upsert/locking care, and would still grow an audit table the moment
  "who ran it and why did it fail" is asked. Rejected.
- **Synthetic "system" user row** for scheduler/CLI attribution — pollutes the
  users table, breaks FK semantics (a user that can never log in), and the
  trigger column already answers the question. Rejected.
