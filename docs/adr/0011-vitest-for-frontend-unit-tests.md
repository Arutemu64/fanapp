# ADR-0011: Vitest for frontend unit tests

- **Status:** Accepted
- **Date:** 2026-07-26
- **Deciders:** Project maintainers

## Context

The backend has had a two-layer pytest suite since early on; the frontend had no
test runner at all. That was tolerable while `frontend/src/lib/` held mostly
thin API wrappers, but it no longer is: several modules there encode rules that
break silently and cannot be checked by reading a diff — search-text
normalization (ё/е folding, diacritic stripping, token semantics), duration and
plural formatters, permission predicates, and offline-cache scoping. A wrong
`ё` fold produces no error, no type failure and no lint warning; it just quietly
stops finding half the schedule.

The trigger was optimizing the schedule/voting search: `utils/search.ts` was
rewritten to pre-normalize its input, and the only way to show the rewrite
preserved matching semantics was to pin those semantics in a test. Writing it
required choosing a runner, which the repository had never done for this side of
the monorepo.

The frontend is a Vite + SvelteKit SPA (ADR-0007) on pnpm, with dependencies
pinned exactly and Renovate auto-merging dev-tooling minors.

## Decision

We will use **Vitest** for frontend unit tests, scoped to plain-TypeScript
modules under `frontend/src/`.

- One dev dependency (`vitest`), pinned like every other; its Vite peer range
  already covers the Vite 8 the app builds with.
- Config lives in `frontend/vitest.config.ts`, deliberately **separate** from
  `vite.config.ts`: the tests import no Svelte and no `$env`, so the SvelteKit
  plugin (and the `PUBLIC_*` variables it resolves at build time) stays out of
  the test run.
- Tests are colocated as `foo.test.ts` next to `foo.ts`, collected via
  `src/**/*.test.ts`.
- Globals are off — test files `import { describe, expect, it } from 'vitest'`.
- Wired as `just frontend-test` / `pnpm test`, added to `just ci` and to the
  frontend gates in `.github/workflows/ci.yml` behind the existing
  `paths-filter`, so a backend-only change does not pay for it.

Component, route and `load` testing is explicitly **out of scope** for this
decision. No DOM environment, no `@testing-library/svelte`, no browser mode.

## Consequences

- Pure logic in `src/lib/` is now testable at near-zero cost, and CI fails on a
  silent regression in it. `utils/search.ts` is the first module covered.
- The frontend CI gate grows by a step measured in hundreds of milliseconds; the
  paths filter keeps it off backend-only changes.
- `docs/testing.md` stops being backend-only and now carries both suites, so the
  "does this change need a test?" judgement call has one home.
- Component testing remains unavailable. When it is genuinely needed, that is a
  **new decision** — it means a DOM runtime, the SvelteKit Vite plugin in the
  test path, and env plumbing — and should arrive as a superseding ADR rather
  than being added quietly to `vitest.config.ts`.
- A second config file means `vite.config.ts` and `vitest.config.ts` can drift.
  Acceptable today because the test config intentionally shares nothing with the
  app build; if tests ever need the app's aliases or plugins, merge them rather
  than duplicating.

## Alternatives considered

- **`node:test` with Node's TypeScript type-stripping.** Zero new dependencies,
  and CI already runs Node 24. Rejected: it needs `.ts` import extensions that
  fight the SvelteKit/TS config the rest of the frontend uses, gives up on
  aliases like `$lib`, and forecloses component tests entirely — a cheaper
  runner that makes the next step more expensive.
- **Jest.** Rejected: a second toolchain (its own transform pipeline) parallel to
  the Vite one the app already builds with, for no benefit here.
- **No frontend tests; keep relying on `svelte-check` and review.** Rejected on
  the evidence — the search rewrite came with a measurable behaviour risk that
  neither a type checker nor a reviewer would have caught, and the module in
  question is used by three pages.
