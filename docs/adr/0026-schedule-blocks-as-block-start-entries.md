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
becomes `schedule_entries`, with a `kind` column (`event` | `block_start`,
VARCHAR + CHECK like every other enum). An event belongs to the nearest block
start above it in `order`; events above the first block start belong to none.
Block starts carry no number, duration, queue position or stage state (a CHECK
constraint holds the stage state), and the stage operations — current, skip,
move — refuse them with `BLOCK_START_NOT_ALLOWED`. A block start is a valid
"place after" target, which is how an event moves to the top of a block.

The API stays flat: `GET /schedule/` returns the entries in programme order as a
union discriminated by `kind`, and the client derives the sections.

## Consequences

- Moving an event between blocks is an ordinary move; no block bookkeeping.
- Queue, "next event" and announcements filter on `kind = 'event'`; any new
  query over the table must too.
- A block-less pause between two blocks is no longer expressible — it belongs
  to the block above it. The migration and the import accept that.
- The import spreadsheet gives a block its own row (only `block_title` filled);
  the old one-title-per-event layout is rejected with
  `BLOCK_ROW_WITH_EVENT_DATA` rather than silently imported block-less. Block
  rows are matched to existing block starts by title, so their ids survive a
  re-import.

## Alternatives considered

- **Nested API (blocks containing events).** Rejected: the stored order is one
  list, so nesting would be a second derived shape to keep consistent, and a
  move would change the shape of the response rather than one `order` value.
  The ETag cache (ADR-0014) works on the flat list unchanged.
- **A `blocks` table with an FK from events.** Rejected: an event's block would
  then be independent of its position, so a move would need two writes that
  can disagree, and the block order would need its own ordering column.
- **A `block_end` kind as well**, to keep block-less pauses between blocks.
  Deferred: no screen needs it yet, and it doubles the rules for membership.
