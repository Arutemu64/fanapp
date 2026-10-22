# ADR-0043: Estimate the wait to an act from planned durations

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Project maintainers

## Context

[ADR-0014](0014-cache-the-schedule-in-redis-with-etag.md) dropped the predicted
clock time and kept the queue distance ("осталось N выступлений") as the only
countdown, on the schedule screen and in subscription notices alike. The queue
distance is exact, but it says little: acts range from about a minute (a single
defile) to 13 (a mass defile), so "5 acts away" is anywhere from 5 minutes to
over an hour. Subscribers set their reminder in acts for the same reason, and
got a notice on every step of the count.

Every event already carries its planned `duration`. It is self-reported by
participants, often wrong, and an upper limit by the festival's rules, so any
estimate built on it is approximate.

## Decision

We will show and act on an **estimated wait in minutes**, summed from the
planned durations of the acts between the stage and the act, the current act
counted in full, plus a **changeover** after each: the pause while one group
leaves and the next walks on, which the planned durations leave out.

- The changeover is one organizer-set value, `AppSettings.schedule.changeover_seconds`
  (30 s by default, a guess until measured), served to clients in `GET /config`
  so the estimate works offline from the cached config. It lives in the settings
  row, not an env var, so it can be tuned on show day without a deploy.
- The backend computes it when building subscription notices, and fires one
  reminder when the estimate falls within the subscriber's `lead_minutes`, or
  when the act is two positions away, whichever comes first.
- The frontend computes the same sum on the client (`secondsUntilActs`) for the
  schedule rows and the home "up next" card. The schedule payload is unchanged:
  the estimate is relative to the current act, not to the clock, so the
  response stays byte-stable between edits and cacheable per ADR-0014.
- The label always says "примерно". Up to 10 minutes it shows whole minutes;
  past that it rounds up to 5-minute steps. It falls back to the act count when
  the durations add up to nothing.

## Consequences

- A wait reads in the unit people plan by. Counting the current act in full and
  using upper-limit durations makes the estimate run long, so a reminder comes
  early rather than late.
- The estimate does not track the stage: an act that runs over leaves every
  estimate behind it short until the next act is marked current. The two-act
  floor on the reminder covers the stretch where that matters most.
- The backend and frontend sums must stay the same calculation; each names the
  other in its comment.

## Alternatives considered

- **Keep the queue distance.** Exact, but not useful across formats of very
  different lengths; it is what this replaces.
- **Bring back a predicted clock time (ADR-0008).** A clock time depends on
  `now`, which is what made the schedule uncacheable; a relative estimate gives
  the same planning value without that cost.
- **A changeover per block, or none.** A block start is not a pause on stage,
  and a real break is already an act with its own duration; the gap that is
  missing comes between every two acts.
- **Measure real durations from `set_as_current` timestamps.** More accurate,
  and possible later from the schedule change log, but it needs the stage to
  have run first, which is when the estimate matters least.
