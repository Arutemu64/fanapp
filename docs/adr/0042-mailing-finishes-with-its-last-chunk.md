# ADR-0042: A mailing finishes with its fan-out's last chunk

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** maintainer

## Context

[ADR-0041](0041-notification-fan-out-stores-in-chunks.md) kept the mailing's
progress counter: `SENDING` while the fan-out ran, `sent_count` raised per
stored row, and FINISHED once it reached `total_count`. It had been built for
one command per recipient, where no single step knew when the last row was in.
Once the fan-out was batched, that counter caused problems
([#1035](https://github.com/Arutemu64/fanapp/issues/1035)):

- It was almost never visible. A few thousand rows are stored in seconds.
- It misled. It counted rows stored, not messages a channel accepted.
- A schedule-change retry dropped as stale left its mailing `SENDING` forever,
  because only a `PENDING` mailing could fail. A retry also recounted
  `total_count` while `sent_count` kept the first attempt's rows.
- A fan-out trigger that ran out of redeliveries was terminated, and nothing
  settled its mailing at all.

ADR-0041 rejected computing completion at the end because a fan-out that died
halfway would have no one to finish it. Redelivery reruns the whole fan-out, so
the rerun is that someone. The case left over is the trigger that is never
redelivered again.

## Decision

We will finish a mailing in the transaction that stores its last chunk, and
drop the counter.

- The lifecycle is `PENDING → FINISHED | FAILED`, and any status but
  `CANCELLED` can be cancelled. `SENDING` and `sent_count` are gone.
- `NotificationFanOut(notifications, mailing_id=…)` takes every notification
  of one mailing and calls `Mailing.finish(n)` with the last chunk, or on its
  own for an empty list. `CreateNotification` handles mailing-less
  notifications only.
- A fan-out that will not run again fails its mailing: a stale schedule change,
  and a broadcast or schedule-change trigger on its last delivery
  (`is_last_delivery`, checked by the handler before re-raising). Synadia
  describes the same worker-side check on the delivery count
  ([NATS Weekly #33](https://synadia.com/newsletter/nats-weekly-33)).
  `MAX_DELIVERIES` advisories ([NATS docs](https://docs.nats.io/reference/jetstream/advisory/max-deliver))
  are lost if no one is subscribed when they fire.
- FINISHED means stored, not delivered. Telegram and VK can still be sending
  for a minute or two after it, so a finished broadcast stays cancellable:
  cancelling stops the queued sends (`ensure_active`) and clears the feeds.
- The broadcast history shows the recipient count, `total_count`.

## Consequences

- No per-chunk counter write, and no completion rule split between an atomic
  increment and the aggregate.
- There is no "in progress" state to show. A partly stored mailing reads as
  `PENDING` until it finishes or fails.
- A mailing that fails halfway keeps the notifications it stored. They are still
  delivered, and cancelling the mailing removes them.
- A redelivery of a finished fan-out stores nothing and finishes it again with
  the recounted recipients.
- Whether a channel accepted a message is still recorded nowhere. Per-channel
  receipts would be a separate decision.

## Alternatives considered

- **Keep a counter fallback for one release** for mailing-bound
  `CreateNotificationCommand`s queued by an older build. Rejected: the app was
  not live yet, so there was no such queue to drain.
- **FINISHED for a stale mailing that had started.** Rejected: without
  `SENDING` there is no stored "started". Telling it apart would take a count of
  stored rows, and FAILED is the honest word for a fan-out that never finished.
