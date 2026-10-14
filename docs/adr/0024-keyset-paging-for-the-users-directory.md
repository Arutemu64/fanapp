# ADR-0024: Keyset paging for the users directory; bounded sets stay unpaged

- **Status:** Accepted
- **Date:** 2026-10-14
- **Deciders:** project maintainers

## Context

[ADR-0023](0023-keyset-cursor-pagination-for-feeds.md) moved four feeds to keyset
paging and left the organiser users directory on offset, because it showed a
total and keyset cannot give page numbers. The directory has since moved to
keyset too: it never jumps to page N, and the total it shows is a count of the
current filter, which does not depend on the paging scheme. The offset
`Pagination` type survived only as an unused optional parameter on the voting
nominations read.

## Decision

We will page every list a user scrolls through by keyset, the users directory
included. `GET /users/` takes `cursor` and `limit` and returns `next_cursor` plus
a `total` for the active filter, computed by a separate count.

Lists bounded by the programme — voting nominations and the participants inside
one — are returned whole and are not paged. The voting page searches them in
memory and has to see every participant to find the user's own vote, which a
page boundary would hide. The offset `Pagination` type is removed.

## Consequences

- One paging scheme in the API; no offset path is left to drift.
- A new list endpoint is classified up front: unbounded and scrolled means
  keyset, bounded reference data means unpaged. Google's AIP-158 asks that
  collection endpoints paginate from the start because adding it later breaks
  clients ([AIP-158](https://google.aip.dev/158)); here the app and API ship
  together, so a later change to a bounded list is manageable.
- `GET /users/` runs a count on every page, including "Показать ещё". Returning
  `total` only on the first page is the fix if that ever costs anything.

## Alternatives considered

- **Keep the users directory on offset for the total.** The total never needed
  offset, and a deleted user ahead of the reader would skip a row.
- **Page the voting nominations and participants.** Breaks in-memory search and
  the lookup of the user's own vote, for lists of a few dozen rows.
