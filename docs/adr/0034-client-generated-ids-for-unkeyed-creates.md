# ADR-0034: Client-generated IDs for creates without a natural key

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Project maintainers

## Context

ADR-0022 keeps writes online-only with no automatic retries, and `isPending`
blocks a double tap. That leaves one way to create a row twice: the server
commits, the response is lost (convention Wi-Fi, a timeout), the client shows
an error, and the person presses again.

Most create endpoints already survive this because a unique natural key turns
the second request into a 409: one vote per user and nomination, one schedule
subscription per user and event, one push subscription per endpoint, one ticket
per user, one active sync per source. A create with **no** natural key has
nothing to catch the repeat. `POST /notifications/broadcast` was one. A second
press sent the whole mailing to every targeted role again, and delivered
pushes cannot be recalled.

Two standard fixes exist:

- **The client picks the resource ID.** Google's
  [AIP-133](https://google.aip.dev/133) has APIs let the caller set the ID on
  create, and answer a taken ID with `ALREADY_EXISTS`. The ID is the primary key,
  so the duplicate check is the PK constraint itself.
- **An `Idempotency-Key` header**, with the server storing key → response for a
  window. The IETF draft for it
  ([draft-ietf-httpapi-idempotency-key-header](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/))
  expired at revision 07 (2025-10-15) without becoming an RFC.

## Decision

We will have the client generate the ID for every create that has no natural
key and whose duplicate would do harm. `POST /notifications/broadcast` is the
first: `SendBroadcastInput.mailing_id` is required.

- **Format: UUIDv7** ([RFC 9562 §5.7](https://www.rfc-editor.org/rfc/rfc9562.html#section-5.7)),
  validated with pydantic `UuidVersion(7)`. That matches the server's `uuid7()`
  IDs, which `read_broadcasts` uses as its time-ordered tiebreaker. The
  frontend makes them with `#lib/utils/uuidv7`, because `crypto.randomUUID()`
  only makes v4. The client sets the timestamp bits, so never read a creation
  time out of a client ID. The row's `created_at` is the server's.
- **One ID per intent.** The form draws it when it opens and keeps it across
  submits. It draws a fresh one only once that intent is settled: on success,
  or when the server says the ID is taken.
- **Replay = same caller and same payload.** The interactor loads the row by
  ID. If the author and payload match, it returns the existing resource with
  the original success status and does no work. Otherwise it raises a
  `Conflict` exception (`MAILING_ALREADY_EXISTS`), which becomes a 409.
- **The race is the gateway's.** Two overlapping requests with one ID both miss
  the lookup. The second INSERT hits the PK, and `translate_integrity_error`
  maps `pk_<table>` to the same 409.

Creates whose natural key already makes a repeat a 409 stay server-generated.

**State edits are idempotent by their target state, not by an ID.** The
announced schedule edits (set current, skip/unskip, move) pass
`ScheduleEditService.announce` an `already_applied` check. Under the edit lock
and before the announcement cooldown, a request for the state the schedule
already has returns 204 and writes and announces nothing.

## Consequences

- A lost response followed by a second press on the broadcast form returns the
  original mailing; nothing is sent twice.
- Each new endpoint that adopts this needs the four pieces above: a v7-validated
  ID on the input, a replay check, the PK translation, and a form that holds the
  ID per intent.
- A replay after the payload was edited is a 409, not a silent overwrite. The
  first send already went out, so that 409 is accurate. The broadcast page
  shows "already sent" and draws a new ID, so the next press sends the edit.
- Another organizer who could guess a mailing ID would get a 409, not that
  mailing. Organizers can already read every broadcast in the history, so we
  return 409 rather than AIP-133's `PERMISSION_DENIED`, which is for callers who
  cannot see the existing resource.

## Alternatives considered

- **`Idempotency-Key` header + response store.** Rejected. It needs a Redis or
  table store with an expiry policy and a request fingerprint, all to protect
  what the primary key already protects. Its draft has also lapsed.
- **Server-side dedup on payload (same author, text and roles within N
  minutes).** Rejected. It guesses intent: an organizer who deliberately
  repeats an announcement gets it swallowed.
- **Client IDs on schedule edits.** Rejected. They are PATCHes to a target
  state, not creates, so there is no row to replay. A client ID would also catch
  only the same device repeating itself, while the state check also catches two
  operators making the same call.
- **Client IDs on every create.** Rejected. Votes, subscriptions, push and
  ticket links already turn a repeat into a 409 by their natural key. A second
  key there adds a column of code for nothing.
