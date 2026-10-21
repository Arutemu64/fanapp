# ADR-0040: Commands are a separate message type from domain events

- **Status:** Accepted; transport (NATS, `EventBroker`) superseded by [ADR-0041](0041-procrastinate-replaces-nats-and-the-outbox.md)
- **Date:** 2026-10-21
- **Deciders:** maintainer

## Context

Every message on the JetStream stream was an `AppEvent` with a past-tense name,
but half of them were instructions, not facts. `SyncRequested`,
`BroadcastQueued` and `NotificationQueued` each meant "do this work", and each
had one handler. `MailingCancelled` meant two things: `Mailing.cancel()`
recorded it as a fact, while the `undo_schedule_change` consumer published it as
an order to cancel. ADR-0010 already flagged `SyncRequested` as "a command
carried on the event channel".

The mixing had costs:

- The only durable path was the outbox, and the only way into the outbox was
  `record_event()` on an aggregate. So an instruction had to be recorded on an
  aggregate as if it were a fact. `QuestAward` recorded `NotificationQueued`,
  although `docs/backend.md` said that message is never recorded on an
  aggregate.
- Past-tense names hid that a message has exactly one handler. A reader can't
  tell a fact that new subscribers may react to from a work order.

The literature agrees on the split: events are past-tense facts, and commands
are imperative instructions to a system
([Verraes](https://verraes.net/2019/06/messaging-patterns-natural-language-message-names),
[Bogard](https://jimmybogard.com/message-naming-conventions)). A command goes to
one handler, while an event's producer does not know who consumes it
([tuhrig](https://tuhrig.de/messages-vs-events-vs-commands)).

## Decision

We will keep **domain events** and **commands** as separate types on the same
transport.

- `Message` (`core/events/base.py`) carries `subject` and `dedup_id`. Two types
  derive from it:
  - `DomainEvent` (`core/events/`): a fact an aggregate records with
    `record_event()`.
  - `Command` (`application/commands/`): an instruction from a use case. It
    lives in the application layer because asking for work belongs to the use
    case, not the domain.
- Commands are named `<Imperative><Subject>Command`. Their subjects are
  `cmd.<context>[.<entity>].<imperative-verb>`. The suffix avoids clashing with
  the interactor that handles the command (`CreateNotification`).
- `UnitOfWork.enqueue(command)` writes a command to the outbox on commit, the
  same way recorded events are written. The outbox guarantee no longer requires
  an aggregate.
- A consumer that is already redelivered on failure may still publish a command
  directly through `EventBroker` (the notification fan-outs, the schedule
  undo).
- Renamed: `NotificationQueued` → `CreateNotificationCommand`,
  `BroadcastQueued` → `ProcessBroadcastCommand`, `SyncRequested` →
  `RunSyncCommand`. The undo's use of `MailingCancelled` → `CancelMailingCommand`.
  The fact `MailingCancelled` is gone: nothing reacted to it other than as that
  command.
- Payloads are unchanged. A data migration renames the subject of every
  undelivered outbox row. Durable names are kept: `sync_consumer_configs`
  updates each durable's filter subject in place, which NATS 2.14 allows (tested
  against `nats:2.14-alpine`).

## Consequences

- Reading a message's type tells you whether it is a fact or a work order, and
  so whether it has one handler or many.
- `QuestAward` no longer records instructions. It builds its notifications
  (`award_notification()`, `cancellation_notification()`) and the interactor
  enqueues them.
- The ADR-0010 consequence that `SyncRun` must be an aggregate so the outbox
  works no longer holds. `enqueue` needs no aggregate.
- A message stored in JetStream under an old subject and not yet consumed when
  the deploy lands is skipped once its durable's filter moves. Undelivered
  outbox rows are safe, because the migration renames them. At this volume
  consumers drain in milliseconds; the exposed case is a sync running at deploy
  time, which `reap_stale` already settles as failed.
- A `subject` remains a published contract. Renaming one is a migration, as
  before.

## Alternatives considered

- **A second stream with `WorkQueue` retention for commands.** It deletes on ack
  and refuses a second consumer on a subject
  ([NATS retention](https://docs.nats.io/learn/jetstream/retention-policies)).
  Deferred: the benefit is small at this volume, retention cannot be changed
  after a stream is created, and the `cmd.` prefix keeps the move open.
- **A separate task queue (Celery, Taskiq).** Rejected: it would duplicate the
  ack, retry and outbox machinery JetStream already gives us.
- **Rename only the classes, keep the wire subjects.** Cheaper to deploy, but
  then the wire keeps calling instructions facts, and the stream cannot be split
  by prefix later.
