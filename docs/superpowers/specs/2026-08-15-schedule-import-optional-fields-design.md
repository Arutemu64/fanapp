# Schedule import: optional nomination & block, interlude rendering

**Date:** 2026-08-15
**Status:** Approved, pending implementation plan

## Problem

The schedule import forces every row to carry a non-empty `nomination_title`
and `block_title`. But breaks, the opening, and the closing are not competition
entries and belong to no programme section, so organizers have to invent
placeholder values (`Вне конкурса`, `Открытие`, `Закрытие`) purely to satisfy
the parser — the classic "junk data to pass the validator" anti-pattern.

This is stricter than the domain already is: `ScheduleEvent` declares both
fields `str | None`, the response DTO exposes them as `str | None`, and the
frontend's `buildScheduleGroups` already falls back to `Без блока` /
`Без номинации` for missing values. Only the import parser and the template are
out of step. Conference-schedule tools converge on the same convention — a
session requires its core identity (title, time/duration, type) while breaks and
other non-session items are a distinct lightweight type that carries no
track/category ([Sched](https://sched.com/guide/custom-and-default-session-fields/),
[Whova](https://whova.com/blog/conference-agenda-template/),
[EventPilot](https://support-eventpilot.ativsoftware.com/support/solutions/articles/24000018803-common-conference-app-builder-import-data-errors-and-import-exclusion-reasons)).

## Decisions

- **`nomination_title` and `block_title` become optional per row.** `duration`
  and `title` stay required: every row (breaks included) occupies real stage
  time and feeds the ADR-0008 expected-start projection, and title is a row's
  only human identity. `number` is already optional.
- **Interlude rendering** for rows with no block: a full-width, lighter row in
  the schedule flow, still fully interactive.

## Scope

### 1. Backend — parser & import

- Add `_read_optional_text(value, *, column, row)` alongside
  `_read_optional_int`: `None` for an actually-blank cell, otherwise the trimmed
  string. Whitespace-only follows the same reasoning documented on
  `_read_optional_int` (polars types the whole column as text once one cell is a
  string).
- Read `nomination_title` and `block_title` via `_read_optional_text`; keep
  `title`/`duration` on `_read_text`/`_read_int`.
- `ScheduleEntry.nomination_title` and `.block_title` → `str | None`. The import
  interactor already forwards these into `ScheduleEvent(...)` and
  `update_details(...)`, both of which accept `None` today.
- `REQUIRED_COLUMNS` stays all five. The **columns (headers) remain required;
  only the cells become optional** — identical to how `number` already behaves.
  No change to the core model, response DTO, or the OpenAPI spec, so
  `schema.d.ts` needs no regeneration.

### 2. Template & guide copy

- `scripts/generate_schedule_template.py`: leave `nomination_title` **and**
  `block_title` blank on the break/opening/closing sample rows, and order the
  rows so the break sits *between* blocks, modelling the recommended shape:

  1. `Открытие фестиваля` — interlude (no number, no block, no nomination)
  2. `Дефиле «Наруто»` — Косплей / Одиночное дефиле
  3. `Сценка «Стальной алхимик»` — Косплей / Групповое дефиле
  4. `Перерыв` — interlude between blocks (no number, no block, no nomination)
  5. `Вокал: «Унесённые призраками»` — Караоке / Вокал
  6. `Награждение и закрытие` — interlude (no number, no block, no nomination)

  Regenerate with `just backend-generate-schedule-template`; the parser test
  feeds the committed file back through `parse_schedule_from_excel`.
- `FileFormatGuide.svelte`: update the per-column descriptions for
  `nomination_title`/`block_title` (optional, e.g. пусто у перерыва и
  открытия/закрытия) and rewrite the footnote — blank cells are now allowed in
  `number`, `nomination_title`, and `block_title`; only `title` and `duration`
  are required per row. Add the between-blocks / inside-a-block guidance from §3.

### 3. Data model & grouping

Two rules, keyed on **block presence** rather than a two-field AND:

1. **No `block_title` → interlude.** Renders as a top-level row *between* block
   sections. Block is the top-level grouping key, so a row without one has
   nowhere to nest. A stray `nomination_title` on such a row is simply not shown
   as a header.
2. **`block_title` present, `nomination_title` blank → nests directly under the
   block header, no nomination sub-header** (a bare row inside the block).

This gives organizers a deliberate choice and designs away the mid-block
double-header problem: a break *between* blocks leaves block blank (→ interlude);
a pause *inside* a block gets that block with a blank nomination (→ stays inside,
no stray header). The guide states this explicitly.

`buildScheduleGroups` returns an ordered list of `ScheduleBlockGroup |
ScheduleInterlude` nodes (interludes and blocks interleave in document order).
Within a block, a nomination group's `title` becomes `string | null`; the
sticky nomination sub-header renders only when the title is non-null.
`filterScheduleGroups` handles both node types and null-title nomination groups,
preserving the existing keying contract (keys assigned from the unfiltered
schedule so filtering never re-identifies a group).

### 4. Frontend rendering

- Interlude nodes reuse `EventCard` through a new `variant: 'default' |
  'interlude'` prop so mark-current, skip, the `Сейчас` highlight, and the
  duration/countdown meta all keep working. `variant="interlude"`:
  - drops the bordered block-card chrome for a lighter full-width strip,
  - hides the subscribe bell (a "remind me before the break" reminder is not
    meaningful).

  The staff management strip stays — staff must be able to mark the opening/break
  as the current event. Exact visual polish per the `impeccable` / `ui-ux-pro-max`
  guidance at implementation time; the approved direction is a centered, muted
  `⏸ Перерыв · 10 мин`-style row.
- Sticky block/nomination headers are unaffected; interludes scroll normally
  between them.
- `createSearchIndex` already receives `block_title`/`nomination_title` as
  nullable — confirm it tolerates `null` (the existing fallback `?.trim()`
  implies the type was already nullable) so interludes stay searchable by title.

### 5. Tests

- `backend/tests/unit/adapters/test_schedule_parser.py`: blank
  nomination/block cells → `None` accepted; blank `title`/`duration` still
  rejected; committed-template round-trip still passes.
- `backend/tests/integration/schedule_mgmt/test_import_schedule.py`: import a row
  with null block and null nomination; assert it persists as an interlude-shaped
  event.
- `frontend/src/lib/utils/scheduleGrouping.test.ts`: interlude extraction, a
  null-nomination bare sub-group inside a block, and filtering across both node
  types.

## Out of scope / deferred

- **Merging a block split by a mid-block interlude.** The block-presence rule in
  §3 steers organizers to keep mid-block pauses inside their block, so the
  "transparent interlude that merges two same-block runs" logic is unnecessary
  and not built.
- No data migration or legacy-cache handling — the app has no real users yet.
