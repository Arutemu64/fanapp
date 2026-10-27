# ADR-0048: FestEngine drives the stage over Standard Webhooks

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Project maintainers

## Context

The stage operator runs [FestEngine](https://github.com/DanteBC/FestEngine) on
the venue laptop. They already press F1/F2 to show and play each act, write
`пропуск` in a note to skip one and `>NNN` to move one. An organizer then
repeats the same steps by hand in fanapp, so "now on stage" lags behind the
stage.

The laptop is usually behind the venue's NAT, has no fixed address and may
lose its network mid-show. FestEngine and fanapp share no identifiers except
the act number.

## Decision

We will accept FestEngine's outbound webhooks at
`POST /api/webhooks/festengine` and apply them to the schedule.

- **Push, not poll.** FestEngine sends; fanapp never reaches into the venue
  network.
- **[Standard Webhooks](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md)
  signatures.** HMAC-SHA256 over `id.timestamp.body` with a shared
  `whsec_` secret, a 5-minute replay window and `hmac.compare_digest`. About
  twenty lines of stdlib in `presentation/web/festengine/signature.py`, no new
  dependency. A missing secret, a bad signature or an old timestamp answers 404,
  like `/webhooks/tcloud/{token}`.
- **A dedicated service user, not API keys.** Edits run as the seeded
  `festengine-bot` user, which holds only `schedule:manage` and goes through the
  same permission check as an organizer. The history names it. It is not the
  system user (ADR-0010), so cron, the CLI and NATS consumers gain no right to
  edit the schedule. A webhook still needs an identity: the permission check,
  the change history and the mailing all name a user. Unsetting
  `FESTENGINE__WEBHOOK_SECRET`, or revoking the grant with no redeploy, switches
  the integration off.
- **Editors hear only about human edits.** The console changes the programme
  once per act, so its edits skip the editor notice and appear only in the
  changes feed. Attendee notifications are unchanged. A manual edit is now the
  exception, so it still notifies every editor.
- **Facts, not notes.** fanapp acts on what FestEngine did (`row.show`,
  `row.play`, `row.skip`, `row.unskip`, `row.move`, `row.unmove`) and ignores
  the raw `row.updated` edits. FestEngine is the source of truth for what the
  operator sees, and cancelling a move by deleting the dup row is visible only
  as `row.unmove`.
- **One code path.** `ApplyStageConsoleAction` runs the same
  `ScheduleOperations` as the organizer interactors: edit lock, no-op check
  before the cooldown, change record, mailing.

## Consequences

- A show cue older than 60 seconds is answered `stale` and dropped, so a cue
  delayed by an outage never moves "now on stage" backwards.
- The announcement cooldown applies to the console too. FestEngine retries a
  429 after `Retry-After`; a repeated cue for the current act is a no-op and
  never spends the cooldown.
- `row.unmove` only moves an act back while its latest change is the service
  user's move and it still sits after the cancelled `after_num`. Otherwise it is
  logged and ignored. A move corrected twice in FestEngine unmoves to the
  position before the last correction.
- The service user appears wherever users are listed, as the system user
  already does.
- Notes edited while hooks were off never reach fanapp; there is no snapshot.

## Alternatives considered

- **Parse the notes in fanapp.** Duplicates FestEngine's rules and cannot see a
  move cancelled by deleting the dup row.
- **Per-user API keys.** More setup for a single laptop, and the operator is a
  shift, not a person. Revisit if several consoles or a named operator are
  needed.
- **The shared system user.** Simpler, but every unattended entrypoint would
  inherit `schedule:manage`, and the history could not tell the console from
  other automation.
- **fanapp polls FestEngine.** Impossible through the venue NAT.
