# ADR-0048: FestEngine drives the stage over Standard Webhooks

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Arutemu64

## Context

[FestEngine](https://github.com/Himura2la/FestEngine) is the desktop app the
stage operator runs: it plays each act's track and puts its backdrop on the
projector. Organizers then repeat the same facts in fanapp by hand: "now on
stage", skipped acts, moved acts. During a show they fall behind.

The FestEngine laptop sits at the venue, usually behind NAT and on flaky Wi-Fi.
fanapp cannot reach it, and FestEngine has no API to poll. fanapp has no
machine-to-machine auth either: every write is an interactor acting as a
logged-in user.

## Decision

FestEngine pushes events to `POST /api/webhooks/festengine`, and fanapp turns
them into schedule edits.

- **Wire format:** [Standard Webhooks](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md).
  The receiver verifies the `v1` HMAC-SHA256 signature over the raw body and
  rejects timestamps more than 5 minutes off. A missing secret, a bad
  signature and a stale timestamp all answer 404, as `/webhooks/tcloud/{token}`
  does. The check is a dozen lines in `presentation/web/festengine.py`, so we
  don't add the `standardwebhooks` package.
- **Identity:** the webhook acts as the seeded system user (ADR-0010). It loads
  that user and calls `perm_service.ensure(..., SCHEDULE_MANAGE)` on every
  request. Migration `680b7d27712f` grants the permission.
  `ScheduleEditService.announce(actor=...)` takes the user in place of the
  session's. All writes then run the organizer code path: edit lock, no-op
  detection, cooldown, mailing, `ScheduleChange`.
- **Notes:** an action fires when a marker changes between `previous.notes`
  and `notes`, never because of the note's current text. A leading `-` skips.
  `>NNN`, matched with FestEngine's own regex, moves. Re-saving a note for
  another reason therefore never undoes an organizer's later decision.
- **Unmove** only undoes a move FestEngine made: the act's latest change must be
  `MOVED` by the system user. Anything else is left alone and logged.

[docs/festengine.md](../festengine.md) holds the full contract.

## Consequences

- Turning the integration off takes no deploy: unset
  `FESTENGINE__WEBHOOK_SECRET`, or revoke the grant.
- Cron, the CLI and NATS consumers also run as the system user, so they can now
  edit the schedule too. None of them calls a schedule interactor today. Keep
  it that way, or `MOVED`-by-system stops meaning "FestEngine moved it", and
  unmove would undo those moves too.
- The history shows FestEngine's edits as the system's, not the operator's.
- Each action is one announced edit. A note that both skips and moves (`->305`)
  gets a 429 on the move. FestEngine retries after `Retry-After`. The skip is
  then a no-op and the move goes through.
- Notes edited while FestEngine's hooks were off never reach fanapp. There is no
  snapshot of the table.

## Alternatives considered

- **Poll FestEngine.** The laptop is behind NAT. It would also need FestEngine
  to grow a server.
- **Per-user API keys.** This would be the first general machine-auth surface,
  for a single caller. The URL and custom headers FestEngine sends leave room to
  add keys later without changing FestEngine.
- **Parse the note's current text.** Every unrelated edit would re-apply the
  marker and overwrite an organizer's later change in fanapp.
- **One transaction for all of an event's actions.** Each `ScheduleChange`
  carries its own mailing and the cooldown spaces out announcements, so this
  would need a second edit path. A retry through the cooldown is simpler.
