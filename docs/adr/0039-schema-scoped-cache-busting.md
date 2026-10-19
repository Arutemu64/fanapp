# ADR-0039: Schema-scoped busting of the persisted query cache

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Project maintainers
- **Supersedes:** [ADR-0021](0021-tanstack-query-for-server-state.md)'s "the build `version` is the `buster`"

## Context

ADR-0021 passes the build `version` as `persistQueryClient`'s `buster`. A cache
saved under another buster is discarded whole on restore
([persistQueryClient, `buster`](https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient)),
so every deploy, a frontend-only one included, wipes the saved programme.

That is worst at the moment the cache exists for. `AppUpdateService` downloads a
new build in the background and applies it at the next link tap. An attendee
who picked up the build on venue Wi-Fi and then walked into a mobile shutdown
taps a link and loses the programme, the leaderboard and, since
[ADR-0038](0038-offline-write-queue-for-idempotent-writes.md), any writes waiting
in the queue. TanStack's guidance is to change the buster when cached data
becomes invalid; the build version is a proxy for that which is almost always
wrong.

What the buster protects against is real: a new build reading a saved body whose
shape its types no longer describe. That depends only on the response schema of
each saved query, which the OpenAPI spec already states.

## Decision

We will stamp each saved query with a hash of its operation's response schema
and drop, on restore, only the queries whose hash changed.

- `frontend/scripts/responseSchemaHashes.ts` runs in `pnpm generate-api` after
  hey-api and writes `src/lib/api/generated/responseSchemaHashes.gen.ts`: for
  each operation with a JSON 2xx body, the first 16 hex digits of the SHA-256 of
  that schema with `$ref`s inlined and documentation keys (`description`,
  `title`, `example`, `examples`, `default`) removed.
- `createIdbPersister({ schemaHashOf })` stores `{ client, schemaHashes }` and
  filters the queries on restore. Mutations are kept.
- The `buster` becomes a constant, `QUERY_CACHE_FORMAT`, bumped only when the
  persister's stored format changes.

## Consequences

- A deploy keeps every saved query whose response shape it didn't change. A
  change to another endpoint, a request body or a description busts nothing; a
  change to the schedule DTO, or a DTO nested in it, drops the schedule only.
- The hash file is generated and committed, so `just frontend-check-api` catches
  a spec change that wasn't regenerated. A unit test fails if an allowlisted
  query has no hash, which would drop it on every restart.
- A server-side change in meaning without a change in shape (a field that now
  means something else) is not caught. The next refetch corrects the data, as it
  would for any stale copy.
- The first restore after this ships finds an entry in the old format and starts
  empty, once.

## Alternatives considered

- **Hash the whole spec.** Rejected: any API change, however unrelated, wipes
  every saved screen, which is most of the problem with the build version.
- **A hand-bumped constant.** Rejected: it depends on someone remembering, and a
  forgotten bump feeds a new build an old shape.
- **Validate restored data against a runtime schema (zod/valibot from hey-api).**
  Rejected for now: it catches meaning-preserving shape drift too, but it ships a
  validator for every saved response and costs a parse of the whole programme
  on each restore, to protect against what the hash already detects at build time.
- **Keep the build version.** Rejected for the shutdown scenario above.
