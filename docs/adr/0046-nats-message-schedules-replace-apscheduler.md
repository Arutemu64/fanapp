# ADR-0046: NATS message schedules replace APScheduler, and the stream worker hosts the outbox relay

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Project maintainers

## Context

A separate `scheduler` container ran APScheduler v3 for four cron jobs (the
TicketsCloud and cosplay2 syncs, outbox retention, notification retention) and
the outbox relay loop of [ADR-0015](0015-listen-notify-wakes-the-outbox-relay.md).
It ran the same image, broker and Dishka container as the `faststream` worker
and needed the same 256M memory ceiling, on a VPS where every container counts.

APScheduler kept its schedule in process memory. A tick that fell while the
container was down (a deploy, a crash) was lost, and a second replica would
have run every job twice.

NATS 2.14 added recurring message schedules to JetStream
([ADR-51](https://github.com/nats-io/nats-architecture-and-design/blob/main/adr/ADR-51.md),
[2.14 release notes](https://docs.nats.io/release-notes/whats_new/whats_new_214)).
A message with a `Nats-Schedule` header (cron, `@every`, or a descriptor) is
stored on its own subject, and the server publishes a copy to a target subject
on every fire. We already run `nats:2.14-alpine`. Testing that image confirmed
four facts:

- The server rejects a stream that allows schedules and uses `DiscardPolicy.NEW`
  (error 10052).
- Five-field crontab is rejected. NATS cron has six fields, with seconds first.
- `Nats-Schedule-Time-Zone` resolves IANA names, because the image ships tzdata.
- A cron fire missed while the server was down is published once on recovery.

## Decision

We will run the periodic jobs as NATS message schedules and remove APScheduler
and the `scheduler` container.

- **Stream.** The schedules live in their own `scheduler` stream
  (`presentation/faststream/jstream.py`), not in the event stream. The event
  stream needs `DiscardPolicy.NEW`, which the server refuses alongside schedules.
  Its 24h `max_age` would also delete each schedule a day after it was written,
  and a schedule stops firing once its message is gone. `allow_msg_schedules`
  cannot be turned off once set. The `scheduler` stream has no `max_age`, keeps
  `DiscardPolicy.OLD`, and sets `max_msgs_per_subject=1`, so it holds exactly one
  schedule and one pending tick per job.
- **Subjects.** Each job's schedule is stored at `scheduler.schedule.<job>`, and
  it fires to `scheduler.tick.<job>`.
- **Reconciliation.** On startup the worker publishes each configured schedule,
  skipping one whose stored headers already match. Republishing would restart an
  `@every` interval on every deploy. It purges the schedule and tick of each
  disabled job. A cron the server rejects is logged and skipped, so it cannot
  keep the other consumers from starting.
- **Consumers.** Each job has its own durable pull consumer, so a long sync does
  not hold the retention purges back. The consumers use the same bounded
  redelivery as every other consumer. A retry ends when the next tick replaces
  its message.
- **Config.** The `SCHEDULER__*_CRON` env keys are unchanged. Five-field crontab
  gets a `0` seconds field before it is sent. The app `TIMEZONE` goes out as
  `Nats-Schedule-Time-Zone` on cron schedules only, because the server refuses
  it on `@every`.

The outbox relay loop moves into the `faststream` worker as a background task
(`presentation/faststream/outbox_relay.py`), started in `after_startup` and
cancelled in `on_shutdown`. This partly supersedes ADR-0015: the LISTEN/NOTIFY
design stands, but the relay no longer runs in a scheduler process.

## Consequences

- There is one container fewer, which frees its 256M memory reservation and its
  database pool. The `faststream` pool overflow goes from 5 to 10, because that
  worker now also runs the relay and the scheduled jobs. The api and faststream
  pools together stay below the old three-service total.
- A tick missed while the worker is down still runs once when it returns. It is
  not lost, and it is not replayed once per missed fire. Two worker replicas
  share each durable, so a tick runs only once.
- The schedule lives in NATS. Changing a cron still means editing `.env` and
  restarting `faststream`.
- `faststream` is now required for event delivery, the syncs, and retention.
  Before this change it was already required for consuming events.
- Disabling a job takes effect after the subscribers start, so a tick that was
  already pending can run once more.
- NATS must stay at 2.14 or later. 2.12 supports only one-shot `@at` schedules.
- Six-field cron and `@every` now work in the env keys. APScheduler accepted
  neither.

## Alternatives considered

- **Keep the event stream and add `allow_msg_schedules` to it.** The server
  refuses this while the stream uses `DiscardPolicy.NEW`, and the stream's
  `max_age` would expire the schedules. Changing either setting would weaken
  event delivery, and the flag could never be removed afterwards.
- **Keep APScheduler and only move it, with the relay, into the worker.** This
  removes the container but keeps the in-memory schedule. A missed tick would
  still be lost, and a second replica would still run every job twice.
- **A FastStream or third-party scheduler library.** It would add a dependency
  to do what the NATS server already does, and the schedule would still be held
  by our process instead of by the server.
