# ADR-0041: A notification fan-out stores in chunks and sends in parallel

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** maintainer

## Context

A schedule change or a broadcast reached its recipients through a chain that
handled one message at a time at every hop:

- The fan-out published one `CreateNotificationCommand` per recipient. Each
  one locked the mailing row, inserted a row, incremented the count,
  committed, read the row back for the live toast, and published
  `NotificationCreated`. That is about eight round trips per recipient, and
  the mailing row lock kept them in a single file however many consumers ran.
- Each channel's consumer (push, Telegram, VK) was a pull subscriber with
  FastStream's defaults: one message per fetch, one handler at a time. A push
  service answers in about 0.1–0.3 s, so a change reaching a thousand people
  finished its push delivery minutes after the change.
- The senders also held a pooled database connection, and row locks on the
  mailing and the user's linked account, through the external call, so simply
  running more of them would have exhausted the small faststream pool and
  queued them behind each other.

A schedule notification ("on stage now") loses its meaning within minutes, so
this latency is a correctness problem rather than a nuisance.

## Decision

We will store a fan-out's notifications in bulk and deliver them in parallel.

- `NotificationFanOut` (`application/services/notification_fan_out.py`) is the
  one path every notification takes. It inserts a mailing's notifications 500
  per transaction (`INSERT … ON CONFLICT DO NOTHING RETURNING id`), adds the
  count of new rows to `sent_count` under the mailing row lock, commits, sends
  the live toasts, and publishes `NotificationCreated` for the chunk. The
  broadcast and schedule-change fan-outs call it directly. A
  `CreateNotificationCommand` (a quest award, a personal message) is a fan-out
  of one.
- `NotificationCreated` carries a dedup id, so a rerun fan-out republishing a
  chunk inside JetStream's window does not resend it.
- The channel consumers run 32 (push) and 8 (Telegram, VK) handlers each
  (`max_workers`, FastStream's `ConcurrentPullStreamSubscriber`) and fetch 16
  messages per pull. Telegram and VK share a per-process rate limiter, kept
  under each provider's published limit (about 30 messages/s for a bot,
  20 requests/s for a community token).
- Senders read without row locks where nothing is written back, and end their
  transaction before every external call.
- Push sends a `Topic` and a ten-minute TTL for schedule notifications
  (RFC 8030 §5.2–5.4), and `Urgency: high` for every type
  `NotificationType.is_time_sensitive` names (schedule changes, broadcasts,
  personal messages). A schedule notification older than ten minutes is
  dropped by every channel instead of sent.

## Consequences

- A fan-out's database work is O(N/500) transactions instead of O(N), and its
  first chunk is being sent while later chunks are stored.
- Fan-out redelivery reruns the whole fan-out. Inserts and counts stay
  idempotent through the deterministic ids; the live toasts repeat, as they
  did before, and `NotificationCreated` is deduplicated only inside the
  two-minute window.
- A cancellation now lands between chunks rather than between rows. The chunks
  already stored are deleted by the cancellation itself, as before.
- Parallel senders do not keep order. Build order still decides which chunk
  goes first (subscription notices, then the stage announcement, then
  editors), and a schedule notification a later mailing of the same type has
  overtaken is dropped at send time, so the newest stays on top. Subscription
  notices take their own push lane, so a change's stage announcement cannot
  replace a reader's own act on the shade.
- More handlers are in flight at a deploy, so the faststream service's
  `stop_grace_period` (20 s) is kept above the broker's 15 s graceful timeout.
- The rate limiters are per process. Running a second faststream container
  would double the rate sent to Telegram and VK; scaling out needs a shared
  limiter first.
- The send consumers can outnumber the faststream DB pool only because no
  sender holds a connection across a send. A future sender that reads after
  its external call must keep that property.

## Alternatives considered

- **Keep one command per recipient and only raise `max_workers` on
  `create_new_notification`** — rejected: the mailing row lock serializes those
  handlers whatever their number.
- **Drop the per-insert count and compute `sent_count` at the end** — rejected:
  the count is how a mailing finishes, and a fan-out that dies halfway would
  leave it SENDING with no one to finish it.
- **Batch VK sends with `peer_ids` (up to 100 recipients a call)** — deferred:
  the channel consumers handle one notification per message, and a
  multi-recipient call returns per-recipient errors that would each need their
  own ack decision. The rate limiter plus parallel workers keeps VK at its
  documented quota without it.
