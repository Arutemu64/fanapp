# ADR-0017: `@hey-api/openapi-ts` for the frontend API client

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** @arutemu64 (PR #834)

## Context

The SPA talks to the FastAPI backend through a client generated from the shared
OpenAPI spec (`shared/openapi/openapi.json`; the contract chain is described in
[docs/api.md](../api.md)). The original setup paired two libraries:
`openapi-typescript` (types only, emitted to `schema.d.ts`) and `openapi-fetch`
(the runtime `client.GET('/path', …)` wrapper).

That combination carried standing friction:

- **File uploads needed a hand-written transform.** `openapi-typescript` cannot
  express FastAPI's binary upload fields as `Blob`, so a custom `transform` in a
  bespoke `scripts/generate-api.mjs` rewrote them, and every upload call site
  built `FormData` / set the urlencoded `Content-Type` by hand.
- **Types were not named exports.** Every DTO had to be reached through
  `components['schemas']['X']`, which spawned a layer of pass-through aliases
  (`$lib/types/*`, inline `type X = components['schemas']['X']`) whose only job
  was to give the schema a usable name.

`@hey-api/openapi-ts` is a maintained generator (used by Vercel, PayPal, others)
that emits named types, a typed SDK (one function per operation), and a bundled
fetch client with request/response/error interceptors.

## Decision

We will generate the frontend API client with `@hey-api/openapi-ts`, replacing
`openapi-typescript` + `openapi-fetch`. Config lives in
`frontend/openapi-ts.config.ts` (plugins: `@hey-api/client-fetch`,
`@hey-api/typescript`, `@hey-api/sdk`); output goes to
`frontend/src/lib/api/generated/` and is **committed**. `createApiClient()` wraps
the generated client and installs the reachability + 401 session-expiry watches
as interceptors; call sites use the SDK functions and pass `{ client }` per call
for per-request isolation. The generated output is formatted by Prettier
(`output.postProcess`) and drift is gated by regenerate-plus-`git diff`
(`just frontend-check-api`), not a byte comparison in the generator.

## Consequences

- File-upload handling and named types are native, so the custom transform
  script and the pass-through alias layer are gone; the generated name is the
  single source of truth.
- The whole generated client (`client/`, `core/`, `sdk.gen.ts`, `types.gen.ts`)
  is committed, so a spec change now churns real code in review, not just a
  types file. It is excluded from ESLint/knip and kept out of hand-editing.
- The client **resolves** every request into `{ data, error, request?, response? }`
  and never rejects (generated default `throwOnError: false`); `response` is
  absent on a network failure. Error handling must check the `error` field and
  use `response` presence to tell a network failure from an HTTP error — never
  `try/catch` or promise-rejection. This differs from `openapi-fetch`, which
  threw on network failure. A future reader must keep this convention (see
  [docs/api.md](../api.md)).
- `@hey-api/openapi-ts` is pre-1.0 with a fast breaking-change cadence, so it is
  pinned to an exact version and its Renovate bumps ride the drift gate.

## Alternatives considered

- **Stay on `openapi-typescript` + `openapi-fetch`.** Mature and stable, but
  keeps the upload transform and the alias tax, which were the concrete pains
  this change removes.
- **Hand-write a typed client.** Rejected — re-derives what the spec already
  describes and drifts from it without an enforced gate.
