# ADR-0023: Keyset cursor pagination for the infinite feeds

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** project maintainers

## Context

Four feeds load page by page through TanStack Query's `createInfiniteQuery`:
notifications, schedule changes, feedback and broadcast history. They paged by
`limit`/`offset` and over-fetched one row on the client to detect the last page.

Offset paging is positional. A row inserted ahead of the reader pushes the next
page down by one, so a row repeats; the client deduped by id to hide that. A row
deleted ahead of the reader pulls the next page up by one, so a row is skipped,
and no client-side dedupe can bring it back. Both deletions happen here:
cancelling a broadcast deletes its undelivered notifications, and organisers
delete schedule changes. Offset also grows slower with depth, since the
database reads and discards every skipped row
([Use The Index, Luke: no offset](https://use-the-index-luke.com/no-offset)),
though at a convention's volumes that is not what forced the change.

## Decision

We will page the infinite feeds by keyset. Every feed already sorts
`(created_at DESC, id DESC)` with the unique id as tiebreaker; a page request
carries an opaque `cursor` naming the last row seen, and each response carries
`next_cursor`, null on the last page.

- The contract follows the Slack shape (`cursor` + `limit` in,
  `next_cursor` out; [Slack pagination](https://docs.slack.dev/apis/web-api/pagination)),
  which maps onto `getNextPageParam` directly. An explicit end marker replaces
  inferring the end from a short page, the practice both Slack and
  [Google AIP-158](https://google.aip.dev/158) warn against.
- The token is base64url JSON of `created_at` and `id`. It is opaque by contract
  so its encoding can change; it is not encrypted because both values already
  appear in the page's rows, and it grants nothing — every read keeps its own
  filters and permission checks. A malformed token is a 400 `INVALID_PAGE_CURSOR`.
- The keyset predicate is spelled out with a redundant `created_at <= :t`
  rather than as a row-value comparison, so the existing
  `(user_id, created_at DESC)` notifications index can seek it without id in the
  index ([Use The Index, Luke: fetch next page](https://use-the-index-luke.com/sql/partial-results/fetch-next-page)).

## Consequences

- Deleting or inserting rows ahead of the reader no longer skips or repeats
  rows. On refetch TanStack recomputes each later page's cursor from the fresh
  page before it, so loaded pages never overlap and the client dedupe is gone.
- A feed cannot jump to page N or show a total; none of the four does.
- The sort key must stay immutable (`created_at`, `id`). A feed sorted on a
  column that changes would let rows cross the cursor.
- This changed the four list endpoints' query and response shape — a breaking
  API change shipped together with the client that uses it.

## Alternatives considered

- **Keep offset and live with skips.** Cheapest, but the skip is silent and the
  deletions that cause it are routine organiser actions.
- **Stripe-style `starting_after=<id>`.** Simpler token, but it ties the
  contract to the current sort; an opaque cursor lets the sort change without
  breaking clients.
- **The users directory too.** Left on offset: it is page-numbered with a
  total, which keyset cannot give.
