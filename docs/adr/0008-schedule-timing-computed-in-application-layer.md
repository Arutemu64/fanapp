# ADR-0008: Absolute schedule times computed in the application layer

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project maintainers

## Context

The live schedule only ever had **static, planned** derived values. `queue`
(1..N position) and `time_until` (cumulative sum of preceding durations) are
produced by a single SQL window function in `ScheduleEventORM.ranking_subquery`
— see ADR-0002 for why derived reads live in SQL projections. Those values are
also reused as `WHERE` expressions (`get_by_queue`, subscription-distance
filters), so keeping them in SQL earns its place.

What was missing is any **real-world anchor**. Nothing recorded when an event
actually went on stage, so predicted times could not reflect show *drift* — an
act starting late or overrunning. The frontend approximated "how far ahead"
purely by subtracting cumulative `time_until` values, which shifts only when a
staffer advances the current-event pointer, never while an act runs long.

Handling drift needs an absolute predicted start (`≈ 14:35`) anchored to the
*actual* start of the current event and clamped to the wall clock. That value
depends on `now`, which a SQL column property cannot express without threading a
bind parameter through every query — and it still could not express the
"clamp to now on overrun" rule cleanly.

## Decision

We will record `actual_start_time` when an event becomes current, and compute
`expected_start_time` in a new application service
`application/services/schedule_timing.py` — **not** in SQL and **not** in the
core domain.

- The anchor is the current event's `actual_start_time`; each later non-skipped
  event's `expected_start_time = max(anchor + Σ(durations + transition_buffer),
  now)`. The `max(..., now)` term is what reflects an overrunning current act.
- `transition_buffer` (seconds between events) is an app-level setting on
  `LimitsConfig`, not a per-event column.
- The domain stays clock-free: `ScheduleEvent.set_current(now)` receives the
  timestamp from the interactor (per ADR-0002), rather than reading the clock
  itself.
- `queue` and `time_until` stay exactly as they are in SQL. This ADR **adds** a
  request-time-dependent value; it does not relocate the existing static ones.

## Consequences

- Derived read values that depend on **request-time state** (`now`) are computed
  in the application layer; SQL projections remain the source for values derived
  purely from stored columns (`queue`, `time_until`). This split is the rule a
  future reader should follow, not undo without a superseding ADR.
- The schedule read does one extra in-memory pass over the event list, which is
  already fully loaded by `read_list_schedule` — negligible cost, no extra query.
- `expected_start_time` is exposed on the schedule DTO/API as an absolute anchor
  so clients can run their own live countdowns instead of relying on values that
  only refresh on the next poll.

## Alternatives considered

- **SQL window with a `now` bind parameter** — rejected: pushes wall-clock state
  into every schedule query and still cannot express the clamp-to-now rule
  without post-processing.
- **A per-event `transition_buffer` column** — rejected as premature; nobody
  tunes per-act buffers day-of. One global setting is reversible into a column
  later if a real need appears.
- **A core domain service** — rejected: it needs `now` (impure, violates the
  clock-free core from ADR-0002) and would have to import an application DTO,
  crossing the boundary ADR-0002 enforces.
