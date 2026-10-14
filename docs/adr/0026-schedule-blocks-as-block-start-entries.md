# ADR-0026: Schedule blocks as block-start entries

- **Status:** Accepted
- **Date:** 2026-10-14
- **Deciders:** FAN FAN maintainers

## Context

The programme is one ordered list (a float `order` column, ADR-0008/0014). A
block used to be a `block_title` string repeated on each of its events, and the
schedule page grouped consecutive rows with the same title into a section.
Moving an event therefore never changed its block: it dragged its own title
along, so a moved act landed in the middle of another block still labelled as
the old one — or split a block in two. Organizers need to move acts between
blocks on the day.

## Decision

We will store a block as an entry of its own. The `schedule_events` table
becomes `schedule`, with a `kind` column (`event` | `block_start`,
VARCHAR + CHECK like every other enum). An event belongs to the nearest block
start above it in `order`; events above the first block start belong to none.
Block starts carry no number, duration, queue position or stage state (a CHECK
constraint holds the stage state). A block start is a valid "place after"
target, which is how an event moves to the top of a block.

The two kinds are polymorphic above the table, which is single-table
inheritance ([SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/inheritance.html#single-table-inheritance)):

- **Domain:** `ScheduleEvent` and `ScheduleBlockStart` are separate dataclasses
  over a shared base (`id`, `title`, `order`); `ScheduleEntry` is their union.
  Only `ScheduleEvent` has the stage operations, so misuse fails type checking.
- **ORM:** `ScheduleEventORM` and `ScheduleBlockStartORM` subclass
  `ScheduleEntryORM` with `kind` as the discriminator, so a query for events
  gets `kind = 'event'` added by SQLAlchemy. Every column stays declared on the
  base, because the table-level index and CHECK constraint name them.
- **Gateway:** `get_event` for the stage tools, which find no event behind a
  block start's id (`EVENT_NOT_FOUND`); `get_entry` for move anchors.
- **API:** a Pydantic union discriminated by `kind`, the form Pydantic
  recommends over untagged unions
  ([Pydantic](https://pydantic.dev/docs/validation/latest/concepts/unions/)).

The API stays flat: `GET /schedule/` returns the entries in programme order as a
union discriminated by `kind`, and the client derives the sections.

## Consequences

- Moving an event between blocks is an ordinary move; no block bookkeeping.
- Events-only reads go through `ScheduleEventORM`, which filters on `kind` by
  itself. The one exception is the queue's ranking subquery: the `queue`
  column property builds it while the class is still being mapped, before
  SQLAlchemy can add the criterion, so it spells out `kind = 'event'`.
- A foreign key cannot be limited to one kind: `subscriptions.event_id` could
  point at a block start in SQL. The ORM relationships to `ScheduleEventORM`
  and the gateways keep that from happening in practice.
- A block-less pause between two blocks is no longer expressible — it belongs
  to the block above it. The migration and the import accept that.
- The import spreadsheet gains a `type` column (blank/`event`, or `block`) and
  loses `block_title`: a block is a row of its own whose `title` is the block's
  name. An old-layout file fails on the missing `type` column rather than
  importing block-less. Block rows are matched to existing block starts by
  title, so their ids survive a re-import.

## Alternatives considered

- **Nested API (blocks containing events).** Rejected: the stored order is one
  list, so nesting would be a second derived shape to keep consistent, and a
  move would change the shape of the response rather than one `order` value.
  The ETag cache (ADR-0014) works on the flat list unchanged.
- **One entry class with a `kind` field.** Our first cut. Every stage
  operation needed a runtime guard against block starts, and every events-only
  query had to remember its own `kind` filter.
- **A `blocks` table with an FK from events.** Rejected: an event's block would
  then be independent of its position, so a move would need two writes that
  can disagree, and the block order would need its own ordering column.
- **A `block_end` kind as well**, to keep block-less pauses between blocks.
  Deferred: no screen needs it yet, and it doubles the rules for membership.
