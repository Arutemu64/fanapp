# ADR-0014: Cache the schedule in Redis with an ETag; drop request-time schedule timing

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Project maintainers
- **Supersedes:** [ADR-0008](0008-schedule-timing-computed-in-application-layer.md)

## Context

`GET /schedule/` is the app's hottest read. The schedule is **universal** —
identical for every viewer, carrying no per-user data (subscriptions are served
separately by `GetSubscriptions`) — and during a live show it is read far more
often than it changes, since every connected client refetches on each
`schedule_updated` SSE. Each read ran the ranking window query and re-serialized
the whole event list, per request, for a body that had not changed since the last
edit.

The one thing that stopped the response from being cacheable was
`expected_start_time`, the drift-aware predicted start ADR-0008 computed in the
application layer. It depends on wall-clock `now`, so the payload changed every
second even when nothing was edited. ADR-0008 introduced it (and its stored
anchor `actual_start_time`) so the screen could run a live countdown to an
absolute predicted time.

In practice the feature earned less than it cost. The screen already shows the
**drift-proof queue distance** ("осталось N выступлений"), which is exact and
updates as the current-event pointer advances; the predicted clock time was a
secondary, always-approximate label layered on top. Keeping it meant the schedule
could never be cached and forced a request-time projection (and its stored anchor
column, and clock plumbing through the domain) to exist at all.

## Decision

Drop the request-time schedule timing and cache the rendered schedule in Redis.

- **Remove `expected_start_time`** and the `apply_expected_start_times` service,
  and the `actual_start_time` column, DTO field, and `set_current(now)` clock
  plumbing that existed only to anchor it. The schedule screen keeps the
  queue-distance label; the subscription push keeps its queue-distance body and
  drops the "примерно в HH:MM" suffix. `queue` stays in SQL, unchanged — it is
  derived purely from stored columns and drift-proof (ADR-0008's reasoning for it
  still holds).
- With that gone, **every field on `ScheduleEventFullDTO` is derived purely from
  stored columns**, so the response is byte-stable between edits. Cache it whole
  in Redis behind a `ScheduleCacheGateway` port (one entry, since the read is
  universal). `GetSchedule` serves the cached serialized payload on a hit; on a
  miss it reads, serializes, computes a strong `ETag` (SHA-256 of the body), and
  stores `CachedSchedule(etag, payload)`.
- **Serve an ETag and honour `If-None-Match`.** The web route sets
  `ETag` + `Cache-Control: no-cache` and returns `304 Not Modified` when the
  client already holds that version. Server-side (Redis) and client-side (ETag)
  caching are complementary and layer cleanly — the cheap `304` while the
  schedule is unchanged, a full body on an edit. HTTP conditional-request
  semantics stay in presentation; the interactor never touches `Request`.
- **Invalidate explicitly and synchronously.** Every schedule-mutating interactor
  (import, move, set-current, skip, undo) calls `schedule_cache.invalidate()`
  *after* `uow.commit()`. That is what makes the operator's read-your-writes
  refetch — and every SSE-driven refetch — recompute from committed state instead
  of serving a pre-edit body. A long TTL on the entry is a safety net only, for
  out-of-band writes (the demo seeder) and the rare read that repopulates with a
  snapshot taken microseconds before a concurrent commit; it never substitutes
  for the explicit invalidation.

## Consequences

- The hot read is a single Redis fetch between edits, no query and no
  re-serialization; conditional requests short-circuit to a bodiless `304`.
- The domain is clock-free again for the schedule: `set_current()` takes no
  timestamp, and there is no stored start anchor to keep consistent on undo.
- The predicted absolute start time is gone from the screen and the push. If a
  future need for it reappears, it comes back with this ADR superseded — and
  would have to be reconciled with the cache (a `now`-dependent field cannot live
  in a payload cached across time).
- The invalidation contract is now load-bearing: a new write path that changes
  the schedule without invalidating the cache would serve a stale body until the
  TTL lapses. The rule for a future reader is "every committed schedule mutation
  invalidates the cache," documented in [docs/backend.md](../backend.md) §Caching.

## Alternatives considered

- **Keep `expected_start_time`, cache with a short TTL** — rejected: a
  `now`-dependent field is never byte-stable, so any TTL long enough to help trades
  visibly wrong predicted times for hit rate, and a TTL short enough to stay
  accurate barely caches. The field had to go for the read to be cacheable at all.
- **Cache domain objects, serialize per request** — rejected: re-serializing on
  every hit keeps the per-request CPU the cache is meant to remove, and gives no
  stable bytes to hash into an ETag. Caching the rendered payload is what makes
  both the body reuse and the strong validator free.
- **Invalidate from the SSE fan-out consumer instead of the interactors** —
  rejected: that path is asynchronous (DB → outbox → NATS → consumer), so the
  operator's own immediate refetch could beat the invalidation and read a stale
  cache. Invalidating synchronously after commit closes that window.
- **ETag only, no Redis** — rejected: a `304` still recomputes the body server-side
  to hash it, so it saves bandwidth but not the query/serialization the hot read
  actually spends. Redis removes the compute; the ETag adds the bandwidth win on
  top. Best practice is to use both.
