# API Integration Guide

This guide details best practices for using [`@hey-api/openapi-ts`](https://heyapi.dev/) in the SvelteKit frontend to achieve type-safe communication with the FastAPI backend and clean per-request state isolation. The frontend is a client-rendered SPA, so the browser talks to the backend directly.

The generator (config in `frontend/openapi-ts.config.ts`) emits, into `frontend/src/lib/api/generated/`, a typed **SDK** (one function per operation, in `sdk.gen.ts`), the **types** (`types.gen.ts`), and a bundled **fetch client** (`client/`). Each operation function returns `{ data, error, request?, response? }` — the same discriminated shape as before. `data`/`error` are narrowed by the `error` discriminant; `request`/`response` are optional because a network failure produces no response. Output is run through Prettier by the generator (`output.postProcess`), so it stays formatted and is checked by the format gate like any other source.

---

## Core Concept: Single Source of Truth
* **Generated client**: `frontend/src/lib/api/generated/` is the single source of truth for all API contracts — import operation functions and types from `$lib/api/generated`, the TanStack Query helpers from `$lib/api/generated/@tanstack/svelte-query.gen`, and the configured `client` from `$lib/api`.
* **Auto-generation**: Run `just frontend-generate-api` from the workspace root whenever the backend endpoints, routers, or Pydantic schemas change.
* **Binary / file uploads**: hey-api types binary fields as `Blob | File` and serializes `multipart/form-data` (and `application/x-www-form-urlencoded`) bodies for you — pass `body: { file }` and it builds the `FormData`. No custom transform is needed (the earlier `openapi-typescript` setup hand-wrote one).

### Both generated artifacts are enforced in CI

Forgetting to regenerate is not a silent failure — two committed artifacts each have a check, because a stale one still compiles and would quietly disarm every guard below.

| Artifact | Generated from | Checked by |
| --- | --- | --- |
| `shared/openapi/openapi.json` | the routers and DTOs | `backend/tests/unit/presentation/test_openapi_spec.py` (runs with `just backend-test`) |
| `frontend/src/lib/api/generated/` | that spec | `just frontend-check-api` (`pnpm generate-api:check`; its own CI job) |

`just frontend-generate-api` regenerates both and fixes either failure. The frontend check regenerates the client and then runs `git diff --exit-code` over `src/lib/api/generated/` — so a stale committed client (spec changed, client not regenerated) fails CI. Because the drift guard is a `git diff`, the generated files are **committed**, not gitignored.

**`info.version` is compared separately, against `pyproject.toml`.** It is the one field in the spec whose value comes from outside the repo: `APP_VERSION` reads the *installed* distribution metadata, so a stale editable install (common right after a release bump, before `uv sync`) makes it disagree with `pyproject.toml` and would fail a whole-document comparison over a field that has not drifted. The spec test therefore renders with the version the committed file already carries — leaving every other byte compared — and a second test checks `info.version` against `pyproject.toml`. Both of that test's inputs are committed files, so it gives the same answer on a laptop, in CI, and in a cloud session.

The general rule when adding to the spec: **a value that is not derived from committed source does not belong in a committed artifact.** `APP_BUILD` (the commit SHA) is the reason this matters — putting it in `info` would churn the spec, and the generated client with it, on every single commit. Keep build- and environment-derived values on a runtime endpoint (`/debug/`) instead, and if one has to be in the spec, give it its own test against its own source of truth rather than the byte comparison.

---

## Reads go through TanStack Query; the client holds no state

Every network read in the app flows through a single TanStack Query cache, so invalidation, background refetches and offline reads share one source of truth. See [docs/frontend.md](frontend.md) §2 for the offline half and [ADR-0018](adr/0018-tanstack-query-for-frontend-data.md) for why.

There is **one** hey-api client, the generated singleton, configured at creation in `src/lib/api/heyApiConfig.ts` (base URL, `credentials: 'include'`) via the client plugin's `runtimeConfigPath`, with the interceptors registered in `src/lib/api/index.ts`. That is safe precisely because it carries no request- or user-scoped state — only a base URL, a cookie policy and two interceptors. **User-scoped state lives in the QueryClient**, which is built once per boot in the root `+layout.ts` (never a `$lib` module singleton, per AGENTS.md) and has its user-scoped half dropped on logout by `clearUserQueries`.

Because the client is configured, SDK calls no longer pass `{ client }` — though mutations still do, for clarity at the call site.

### Reads: `createQuery` with a generated `*Options()` helper

The `@tanstack/svelte-query` plugin emits `<operation>Options()`, `<operation>QueryKey()`, `<operation>InfiniteOptions()` and `<operation>Mutation()` per operation, so keys and fetchers are derived from the spec rather than hand-written. Pass them straight into the standard hooks:

```svelte
<script lang="ts">
	import { getSettingsOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { createQuery } from '@tanstack/svelte-query';

	const settingsQuery = createQuery(getSettingsOptions);
	let settings = $derived(settingsQuery.data);
</script>
```

App policy on top of a generated helper (nullable identity, offline options, a `select`) belongs in `$lib/api/queries.ts`, which spreads the generated options first so the key still comes from the spec. Everything else passes a generated helper directly.

### Paginated "load more" feeds: `createInfiniteQuery`

The limit/offset feeds (notifications, schedule changes, feedback, broadcasts) use `<operation>InfiniteOptions()` plus `offsetPagination(pageSize, itemsKey)` from `$lib/api/queries.ts`, which supplies the `initialPageParam` / `getNextPageParam` the generator cannot infer. Render `query.data.pages.flatMap(...)` and drive the button from `hasNextPage` / `isFetchingNextPage` / `fetchNextPage()`.

### What still belongs in a `load`

A `load` fetches only when the **route** has to decide something a component cannot: a permission guard, a redirect, a `404`/`503` error page, or a page title. It does that with `queryClient.ensureQueryData(...)` — warming the very cache entry the component then reads with `createQuery`, so there is still one request and one cache, not two flows:

```typescript
import { throwQueryError } from '$lib/api/errors';
import { getSettingsOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { queryClient, user } = await parent();

	if (!canManageSettings(user)) error(403, 'У тебя нет доступа к настройкам фестиваля');

	try {
		await queryClient.ensureQueryData(getSettingsOptions());
	} catch (requestError) {
		throwQueryError(requestError, 'Не удалось загрузить настройки фестиваля');
	}

	return { title: 'Настройки фестиваля' };
};
```

The root `+layout.ts` puts `queryClient` on layout data, so every child load reaches it through `await parent()` and every component through `useQueryClient()`.

> [!NOTE]
> Loads no longer inject SvelteKit's `fetch`. It exists to let SSR inline responses and to make `invalidate()` re-run a load — and this app is `ssr = false` with cache invalidation owned by TanStack Query, so it buys nothing here. The `session_id` cookie is carried by the browser regardless: the client sets `credentials: 'include'` and the frontend is served same-origin with the API (behind Caddy), so it stays first-party.

> Query params go under `query`, path params under `path`, and the request body under `body` — flat on the options object, not nested under `params`.

---

## TypeScript Types
hey-api generates a **named export per schema** into `types.gen.ts` (re-exported from `$lib/api/generated`). Import the type you need directly — do not re-alias it locally. Schema names are normalized to PascalCase, so a backend `…DTO` becomes `…Dto` (e.g. `NotificationDTO` → `NotificationDto`).

```typescript
import type { NotificationDto } from '$lib/api/generated';
```

Request bodies, query params, and responses are named too — `UpdateSettingsData['body']`, `ListUserNotificationsData['query']`, `GetVotingNominationResponse` — so reach for those instead of hand-walking a `paths[...]` tree. **Do not** reintroduce the old pass-through aliases (`type X = components['schemas']['X']`): with named exports they are pure indirection, and the generated name is the single source of truth. A genuine app-composite type (e.g. `ScheduleEventWithSubscription` in `$lib/types/`) is fine — it *adds* structure over a generated type, it doesn't just rename one.

### Enum schemas are the single source of truth
Backend `StrEnum`s that appear on a DTO field (`UserRole`, `Permission` in `core/vo/`) are emitted as OpenAPI enum schemas, so `frontend-generate-api` regenerates them as string-literal unions. Never hand-copy enum values on the frontend — import the generated union. Permission literals in `lib/utils/permissions.ts` type their constants as the generated `Permission`, so a backend rename/removal makes the stale literal fail `pnpm check` instead of silently breaking permission checks (same drift-guard idea as the error `code` union below). To expose a new enum on the wire, type a DTO field with the enum (not a plain `NewType` str) and run `just frontend-generate-api`.

---

## Mutations & Data Recovery
* **UI Consistency**: After a successful mutation, invalidate the queries it affected — `queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() })`. Key off the generated `*QueryKey()` helper: TanStack matches keys partially, so the bare key matches every variant of that operation (every page size, every infinite page) in one call. Invalidate exactly what changed — subscribing to an event touches `getSubscriptions`, not `getSchedule`.
* **No `depends()` / `invalidate()`**: SvelteKit's dependency invalidation is gone. It re-runs a `load`, which would be a second data flow alongside the cache; a route that needs fresher data invalidates the query instead, and the component re-renders from the cache.
* **Return Checking**: Success payload, error payload, and response metadata are checked through the SDK return (`data`, `error`, `response`). `response` is optional (`response?.ok`, `response?.status`) — a network failure yields `error` with no `response`.

### Long-running actions (202 Accepted)

An action that cannot finish inside the request returns **202** with the created record and a `Location` header pointing at a **status resource** the client re-reads, instead of blocking. `POST /sync/{source}` is the first of these: it queues the work, returns the `SyncRunDTO`, and sets `Location: /sync/sources`.

* **The status resource is an existing list endpoint, not a per-run one.** `GET /sync/sources` already reports each source's latest run, including the active one, so a dedicated `GET /sync/runs/{id}` would exist only to satisfy the convention. Add a per-run endpoint if something genuinely needs to poll one run by id — not before.
* **Prefer SSE over polling for progress.** The page subscribes to the relevant `SSEEventName` (here `sync_run_updated`) and calls `queryClient.invalidateQueries(...)`; it also re-invalidates on `connection_established`, so an update missed while the stream was down (or the tab was backgrounded past the pause grace) self-heals on reconnect rather than leaving a stale "in progress" on screen. Treat the SSE payload as a nudge to refetch, never as the source of truth — never splice it into the cache by hand.
* **A second request while one is running is a 409**, mapped to Russian copy by `code` like any other error — not a silent no-op.

---

## Russian Localization & Error Handling
Russian copy is mandatory (AGENTS.md, "Never"). API-specific rule: normalize failures before presenting them — never expose raw backend stack traces or internal identifiers, and show a friendly Russian message explaining how to recover or retry.

* **Error shape**: every error response is `ErrorMessage { code, details }` (see backend `presentation/web/exceptions.py`). Map failures by the machine-readable `code`, not by HTTP status or message text.
* **Single funnel**: `getApiErrorDetail(error)` (`lib/api/errors.ts`) turns a payload into Russian copy. For **mutations/toasts** use `toastService.error(err)`; for **`load` failures** use `throwQueryError(queryError, fallback)` from the same module — it throws a SvelteKit `error()` with the mapped copy (and carries `code` on `App.Error`), so a load failure looks like every other error instead of a bespoke per-page string. Add new copy to the `ERROR_MESSAGES` dictionary there. (Permission guards and offline-miss states still throw `error()` directly — they have no API `code` to map.)
* **Status comes from the `code`, not the response.** The generated query helpers fetch with `throwOnError`, so a rejected query carries the parsed error body and no `Response`. `throwQueryError` therefore derives the status from the code — the not-found family maps to 404, `ACCESS_DENIED` to 403, `USER_NOT_AUTHENTICATED` to 401, everything else to 500. A new not-found code belongs in its `NOT_FOUND_CODES` set.
* **`code` is a typed union**: the backend stamps the closed set of client-facing codes onto `ErrorMessage.code` as an OpenAPI enum (`presentation/web/error_codes.py`), so `frontend-generate-api` regenerates it as a string-literal union. Dictionary keys are checked against it — a typo is a compile error.
* **Drift guard**: a compile-time exhaustiveness check in `errors.ts` fails `pnpm check` if the backend adds a client-facing code that is neither given copy nor listed in `GENERIC_FALLBACK_CODES`. After changing backend error codes, run `just frontend-generate-api` and resolve any new code the guard reports.
