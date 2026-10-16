# ADR-0035: Quest points as an award ledger

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Project maintainers

## Context

The quest gives every user a points balance. Volunteers add points for tasks
done at the festival, and the top of the leaderboard wins merch. Points are
never spent. A volunteer can take back a mistaken award shortly after making
it, and an organizer can take one back at any time when there is a dispute.

Because merch rides on the ranking, someone will eventually ask "why do I have
120 and not 130?". The answer has to come from data: who gave which points,
when, for what, and who took them back.

The scale is one festival day: thousands of players and tens of thousands of
awards at most.

## Decision

We will store points as an append-only ledger, `quest_awards`, with one row
per award (player, amount, message, who gave it, when). The ledger is the only
record of points. A balance is `SUM(amount)` over a player's awards with
`cancelled_at IS NULL`, and the leaderboard ranks those sums.

- Cancelling sets `cancelled_at` and `cancelled_by` on the row. Rows are never
  updated otherwise, and never deleted.
- `amount > 0` is a CHECK constraint. Points only grow, so a balance can't go
  negative and needs no lock.
- A partial index on `user_id WHERE cancelled_at IS NULL` covers the rows the
  balance and leaderboard read.
- Ties rank by the time of the player's latest live award, earliest first, with
  the user id as a final tiebreaker. `row_number()` therefore gives every place
  to exactly one player.

## Consequences

- Every balance can be explained row by row, and a cancellation stays visible
  with who made it.
- A balance or leaderboard read aggregates the ledger instead of reading a
  column. At festival scale this is a sub-millisecond `GROUP BY`. If it ever
  stops being one, add a balance cache maintained in the same transaction as
  the award and checked against the ledger. The cache must never become the
  source of truth.
- Cancelling an award moves the player's tie-break time back to their
  previous live award. We accept that: it is still the moment they last
  reached a score they hold.
- Introducing spending would need either negative amounts or a separate
  spends table, plus locking so a balance can't go below zero. Revisit this
  ADR if that happens.

## Alternatives considered

- **A `points` column on users.** It loses who gave what, and it gives a
  cancellation nothing to reverse. Concurrent updates also need care so one
  award doesn't overwrite another. Ledger guides treat a stored balance as a
  cache of the entries, never as the record
  ([youngju.dev, 2026](https://www.youngju.dev/blog/2026-07-01-double-entry-ledger.en);
  [pgrs.net, 2025](https://pgrs.net/2025/03/24/pgledger-ledger-implementation-in-postgresql/)).
- **A column plus a trigger-maintained balance.** It pays off only when
  summing gets expensive, at tens of millions of rows
  ([pgsql-general](https://postgresql.org/message-id/49468515.2000904%40iol.ie)).
  This app is far below that, and the trigger is one more thing that can drift.
- **Deleting an award to cancel it.** Simpler, but it erases the evidence a
  dispute needs, and a volunteer could quietly undo awards.
- **A reversing entry instead of a cancelled flag.** This is the accounting
  norm. Here it would need negative amounts and a link between rows. The flag
  records the same facts with a CHECK that keeps every amount positive.
