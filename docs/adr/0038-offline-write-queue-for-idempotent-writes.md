# ADR-0038: An offline write queue for idempotent writes

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Project maintainers
- **Supersedes:** [ADR-0022](0022-createmutation-for-writes.md)'s "mutations never pause offline", for the four writes below

## Context

[ADR-0022](0022-createmutation-for-writes.md) made every write online-only: the
root `QueryClient` sets `networkMode: 'always'`, so a write fails at once with
the connection message instead of firing minutes later, unseen.

The festival runs in Russia, where mobile internet is cut by region for hours
at a time in 2025–2026, often in the evening, and during a cut only a whitelist
of approved services works, if any
([Mediazona](https://en.zona.media/article/2026/01/05/internet)). Wi-Fi keeps
working, so attendees and volunteers move between short Wi-Fi windows. During a
cut, online-only writes block exactly the actions people take at a venue: a
quest station can't award points, an attendee can't subscribe to an act's
reminder, and a feedback message is lost with its draft.

What made ADR-0022 right still holds for most writes: a vote must answer while
its window is open, a profile or password change needs its answer on screen,
and a staff tool's effect must be seen to land. The question is which writes can
wait safely. A write can wait if a resend is harmless, because a queue resends:
the first attempt may land and lose its answer.

## Decision

We will queue four writes, using TanStack Query's paused mutations, and keep
every other write online-only.

| Write       | Why a resend is safe                                                                                                            |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Quest award | client-generated `award_id` ([ADR-0034](0034-client-generated-ids-for-unkeyed-creates.md)): a replay returns the original award |
| Subscribe   | one subscription per user and act: `SUBSCRIPTION_ALREADY_EXISTS` on a replay counts as done                                     |
| Unsubscribe | one target: `SUBSCRIPTION_NOT_FOUND` on a replay counts as done                                                                 |
| Feedback    | not idempotent; a duplicate message is cheap for its reader                                                                     |

- **Defaults per mutation key** (`registerQueuedWrites`, `#lib/api/writeQueue.ts`),
  set before the persisted cache is restored: `networkMode: 'online'`, `retry`
  for as long as there is no API answer, the `mutationFn` and the invalidation.
  A write restored after a restart carries only its key and variables, so it
  needs these defaults
  ([TanStack, persisting offline mutations](https://tanstack.com/query/latest/docs/framework/react/guides/mutations)).
- **Persisted with the queries.** Paused queued writes are dehydrated into the
  same IndexedDB entry; the root layout calls `resumePausedMutations()` after
  the restore.
- **Hand-off.** When a write pauses, the screen says it will go out later and
  detaches (`handOffWhenQueued`); one watcher in the root layout reports the
  outcome (`watchQueuedWrites`), since the screen may be gone by then.
- **Visible while waiting.** Queued subscriptions are laid over the server's
  list and marked «Ждёт связи»; the connection banner counts waiting writes.
- **The quest tool works offline.** A code scanned without a connection becomes
  an unverified player (ID only); the server checks it when the award is sent.
- **Reset with the account.** `Session` drops waiting writes on logout and
  expiry, so they never go out under the next person's cookie.

## Consequences

- Volunteers keep awarding, and attendees keep subscribing and writing feedback,
  through a mobile shutdown; the writes go out in the next Wi-Fi window.
- A queued write can fail long after it was made (an invalid player ID, a quest
  switched off). The failure is a toast that names the action, with no form
  left to fix it in.
- Feedback can arrive twice when a response is lost. Making it idempotent would
  need a client ID on `SubmitFeedbackInput`; not worth it for a duplicate message.
- A write in flight when the app is killed is not saved (only paused ones are),
  and a write logged out of while offline is dropped.
- A deploy discards waiting writes with the rest of the persisted cache, since
  the build `version` is its buster (ADR-0021). Busting only what a deploy
  changed is deferred; until then, a request schema can't change under a
  queued write.
- A new queued write needs: a resend that is harmless, an entry in
  `QUEUED_WRITES` with defaults, a screen built from its `queued…Options()` with
  `handOffWhenQueued`, and copy for its queued, sent and failed outcomes.

## Alternatives considered

- **Workbox Background Sync.** Rejected: Safari and Firefox don't implement the
  Background Sync API ([caniuse](https://caniuse.com/background-sync)), so on
  iPhones it would fall back to replaying on worker start anyway, and it would
  route API requests through the service worker, which never handles them and
  can't see session expiry.
- **TanStack DB offline transactions.** Rejected: a durable outbox with
  leadership and optimistic collections
  ([docs](https://tanstack.com/db/latest/docs/guides/offline-transactions)) is
  a new data layer for four idempotent writes.
- **Queue every write.** Rejected: votes and account changes can be invalidated
  while they wait (a closed voting window, a changed password), and their
  screens need the answer.
- **Keep everything online-only.** Rejected for the shutdown reasons above.
