# ADR-0013: The schedule API publishes anchors; the wait is derived at each edge

- **Status:** Accepted
- **Date:** 2026-07-31
- **Deciders:** Project maintainers

Supersedes the transport half of
[ADR-0008](0008-schedule-timing-computed-in-application-layer.md). That ADR's
core rule — request-time-dependent values are computed in the application layer,
never in SQL and never in the core domain — still holds and is unchanged.

## Context

ADR-0008 put an absolute predicted start (`expected_start_time`) on the schedule
DTO so "clients can run their own live countdowns instead of relying on values
that only refresh on the next poll." In practice they could not.

The projection's defining rule is a floor: never predict a start that is already
in the past, because an overrunning act pushes everything behind it. That floor
is evaluated against the server's `now` at the instant it answers, so the
published value stops satisfying its own rule seconds later. The screen coped by
*hiding* the `≈ HH:MM` once it fell into the past — so the time disappeared
exactly when the show was slipping, which is when people check. Publishing a
value the client cannot refresh or verify also meant the API was shipping a
derived quantity while withholding one of its inputs (`transition_buffer`, which
was reachable only through `GET /settings`, behind `SETTINGS_MANAGE`).

Separately, attendees read the schedule to answer "how long until my act?", not
"what wall-clock time will it be?". An absolute time makes the reader do the
subtraction, and do it against a phone clock nobody has checked.

## Decision

We will publish **anchors and inputs** on `GET /schedule/` and derive the wait
at each edge that renders it.

- The response carries `actual_start_time` (when the current act really began),
  `duration_seconds` per event, and `transition_buffer_seconds`. It no longer
  carries `expected_start_time`.
- `application/services/schedule_timing.py` exposes `project_seconds_until`,
  returning seconds-until keyed by event id. Subscription push text renders it
  at dispatch, because there is no client there to do the work.
- `frontend/src/lib/utils/scheduleTiming.ts` mirrors it, re-run against a ticking
  clock corrected by the `Date` response header (RFC 9110 §6.6.1) so a mis-set
  device clock cannot skew the wait.
- Both render it as an approximate wait — `≈ 25 мин`, `≈ 1 ч 30 мин` — rounded to
  the minute and floored at one minute.

## Consequences

- The wait counts down while the page is open and self-corrects when an act
  overruns, without a refetch. The `≈` is honest about it being a projection.
- **No relative value goes on the wire.** A seconds-until field would be stale
  on arrival — the same defect that made `expected_start_time` unusable, and the
  reason ADR-0008 deleted the older `time_until`. Anchors are absolute and stay
  true; only their interpretation depends on `now`. A future reader must not
  "simplify" this by publishing the computed wait.
- The projection now exists in Python and TypeScript. The Python copy was never
  removable (push text), so this is one added implementation, not two. The unit
  suites mirror each other case for case
  (`tests/unit/application/test_schedule_timing.py` ↔ `scheduleTiming.test.ts`)
  so a divergence fails CI rather than showing a wrong time on a phone.
- Push notifications now say «примерно через 25 мин» rather than a clock time.
  This is a **known trade-off, accepted deliberately**: a push is read whenever
  the phone is next picked up, so the wait it quotes is the wait as of dispatch
  and drifts while the notification sits unread. An absolute time would not.
  Revisit this first if attendees report confusion.
- `transition_buffer_seconds` is now public. It is a domain parameter, not an
  implementation detail — the same class of thing as `duration_seconds`, which
  was already published — and not sensitive.

## Alternatives considered

- **Keep `expected_start_time` and let the client re-floor it.** Rejected: it
  needs the buffer on the wire anyway, and leaves two published values for one
  quantity with the client's silently winning.
- **Publish `seconds_until` computed server-side.** Rejected: stale on arrival,
  and it re-creates the drift-blind `time_until` ADR-0008 removed.
- **Leave everything server-side and accept the staleness.** Rejected: the
  countdown is the schedule screen's most-read element during a slipping show,
  and hiding it there is the worst moment to hide it.
- **Absolute clock time in push text.** Rejected by the maintainers in favour of
  consistent wording across screen and push; recorded above as the trade-off.
