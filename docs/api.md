# API Integration Guide

How the SvelteKit frontend uses [`@hey-api/openapi-ts`](https://heyapi.dev/) to call the FastAPI backend with typed requests, and [TanStack Query](https://tanstack.com/query/latest/docs/framework/svelte/overview) to cache what it reads. The frontend is a client-rendered SPA, so the browser talks to the backend directly.

The generator (config in `frontend/openapi-ts.config.ts`) emits, into `frontend/src/lib/api/generated/`, a typed **SDK** (one function per operation, in `sdk.gen.ts`), the **types** (`types.gen.ts`), a bundled **fetch client** (`client/`), and, from the [`@tanstack/svelte-query` plugin](https://heyapi.dev/openapi-ts/plugins/tanstack-query), the **query options and keys** for every operation (`@tanstack/svelte-query.gen.ts`: `getScheduleOptions()`, `getScheduleQueryKey()`, `listFeedbackInfiniteOptions()`, …). Each operation function returns `{ data, error, request?, response? }`. `data`/`error` are narrowed by the `error` discriminant; `request`/`response` are optional because a network failure produces no response. Output is run through Prettier by the generator (`output.postProcess`), so it stays formatted and is checked by the format gate like any other source.

## Core Concept: Single Source of Truth

- **Generated client**: `frontend/src/lib/api/generated/` is the single source of truth for all API contracts — import operation functions and types from `#lib/api/generated`, query options and keys from `#lib/api/generated/@tanstack/svelte-query.gen.js`, the app wiring (`queryForLoad`, `watchApiResponses`) from `#lib/api`, and identity (`currentUserOptions`) from `#lib/services/identity`.
- **Auto-generation**: Run `just frontend-generate-api` from the workspace root whenever the backend endpoints, routers, or Pydantic schemas change.
- **Binary / file uploads**: hey-api types binary fields as `Blob | File` and serializes `multipart/form-data` (and `application/x-www-form-urlencoded`) bodies for you — pass `body: { file }` and it builds the `FormData`. No custom transform is needed.

### Both generated artifacts are enforced in CI

CI checks both committed artifacts, because a stale one still compiles and would quietly disarm every guard below.

| Artifact                          | Generated from       | Checked by                                                                             |
| --------------------------------- | -------------------- | -------------------------------------------------------------------------------------- |
| `shared/openapi/openapi.json`     | the routers and DTOs | `backend/tests/unit/presentation/test_openapi_spec.py` (runs with `just backend-test`) |
| `frontend/src/lib/api/generated/` | that spec            | `just frontend-check-api` (`pnpm generate-api:check`; its own CI job)                  |

`just frontend-generate-api` regenerates both and fixes either failure. The frontend check regenerates the client and then runs `git diff --exit-code` over `src/lib/api/generated/` — so a stale committed client (spec changed, client not regenerated) fails CI. Because the drift guard is a `git diff`, the generated files are **committed**, not gitignored.

**`info.version` is compared separately, against `pyproject.toml`.** It is the one field in the spec whose value comes from outside the repo: `APP_VERSION` reads the _installed_ distribution metadata, so a stale editable install (common right after a release bump, before `uv sync`) makes it disagree with `pyproject.toml` and would fail a whole-document comparison over a field that has not drifted. The spec test therefore renders with the version the committed file already carries — leaving every other byte compared — and a second test checks `info.version` against `pyproject.toml`. Both of that test's inputs are committed files, so it gives the same answer on a laptop, in CI, and in a cloud session.

The general rule when adding to the spec: **a value that is not derived from committed source does not belong in a committed artifact.** `APP_BUILD` (the commit SHA) is the case in point: putting it in `info` would churn the spec, and the generated client with it, on every commit. Keep build- and environment-derived values on a runtime endpoint (`/debug`) instead, and if one has to be in the spec, give it its own test against its own source of truth rather than the byte comparison.

## One configured client, one query cache

There is **one** API client: the generated singleton in `client.gen.ts`. The generator's `runtimeConfigPath` points it at `#lib/api/clientConfig.ts`, which sets the base URL and `credentials: 'include'` before any call, so SDK functions and generated query options never take a `client` argument. The client holds configuration only — no user data. Its two response interceptors (reachability, session expiry) are registered by the root layout through `watchApiResponses(queryClient)`, which returns their teardown.

Everything the app **reads** goes through TanStack Query. The cache — the `QueryClient` — is the per-session state, so it is created in the root `+layout.ts` load and returned as `data.queryClient`, never as a module singleton ([TanStack's SvelteKit setup](https://tanstack.com/query/latest/docs/framework/svelte/ssr)). Components get it from context (`useQueryClient()`), loads from `await parent()`.

### 1. Components read with `createQuery`

Pass the generated options straight in; override only what the page needs (`enabled`, a custom `getNextPageParam`):

```svelte
<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { getScheduleOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';

	const scheduleQuery = createQuery(() => getScheduleOptions());
</script>
```

The query renders the cached copy at once and refetches in the background (stale-while-revalidate: refetch on mount, on window focus and on reconnect once the copy is older than the client's 60s `staleTime`). The `staleTime` is what keeps a load's hover/tap prefetch from being refetched the moment the page mounts; live data doesn't wait it out, because SSE events and mutations invalidate, which refetches regardless. A load that promises a fresh copy (a form seeded from it) passes `staleTime: 0`. Queries retry only a request that got no API answer (network failure, timeout, gateway page) — an API error is the server's verdict and shows at once. A page keeps showing its last data when a refetch fails, so that failure gets a toast instead (`watchBackgroundRefetchErrors`, wired in the root layout): only for a query on screen with data, never for a failed «Показать ещё» (the feed shows its own error), a missing answer (the connection banner's) or session expiry; a query that should fail quietly, like a glanceable poll, sets `meta: { quietRefetchErrors: true }`. Paginated feeds use `createInfiniteQuery` with the generated `…InfiniteOptions` and keyset paging ([ADR-0023](adr/0023-keyset-cursor-pagination-for-feeds.md)): each response carries an opaque `next_cursor` (null on the last page) that `getNextPageParam` hands back as `cursor`, and `initialPageParam: {}` asks for the first page (hey-api reads an object page param as request overrides, a string as the cursor). A refetch recomputes every later page's cursor from the fresh page before it, so loaded pages never overlap and the feeds need no dedupe; "Показать ещё" is disabled while the query fetches at all (`isFetching`), since fetching the next page during a background refetch can overwrite it ([infinite queries](https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries)).

### 2. Loads guard, prefetch, and only sometimes wait

A `load` keeps three jobs: permission guards (reading identity from the cache, `queryClient.getQueryData(currentUserOptions().queryKey)`), the navbar data (`title`, `back`, `actions`), and starting the page's fetch early — SvelteKit preloads a route's data on hover/tap, so `void queryClient.query(getScheduleOptions()).catch(() => {})` there puts the request on the wire before the page mounts. A load **awaits** a query only when the page can't render without it — a form seeded once from it (festival settings, the voting dashboard), a navbar title (a nomination), a staff card whose load maps a 404 (a user) — through `queryForLoad(queryClient, options)` (`#lib/api`), which runs the request at once and once only — no retries, no pausing for reachability — and rejects with a `TimeoutError` after `FIRST_PAINT_TIMEOUT_MS`, so a stalled server or a dropped connection can't hang the navigation; the load turns that failure into an error page with `throwApiError(apiError, fallback)`.

### 3. Writes go through `createMutation`

A user-triggered write is a `createMutation` over the generated `…Mutation()` options, and the mutation's own `onSuccess` invalidates what it changed ([ADR-0022](adr/0022-createmutation-for-writes.md)):

```svelte
<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import {
		getSubscriptionsQueryKey,
		newSubscriptionMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';

	const queryClient = useQueryClient();
	const subscribeMutation = createMutation(() => ({
		...newSubscriptionMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() })
	}));

	function handleSubmit() {
		formError = '';
		subscribeMutation.mutate(
			{ body: { event_id: event.id, lead_minutes: leadMinutes } },
			{
				onSuccess: () => toastService.add('Подписка оформлена', 'success'),
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? 'Не удалось оформить подписку';
				}
			}
		);
	}
</script>

<Button onclick={handleSubmit} disabled={subscribeMutation.isPending}>Подписаться</Button>
```

- **Mutations never pause offline.** The root client sets `networkMode: 'always'` for mutations, so a write made with no connection fails at once with the connection message. It is not held and fired on reconnect. Writes are online-only, and the controls for them are gated (`offlineWriteGate`, `offlineUnavailable`).
- **Invalidation goes on the mutation; UI work goes on the call.** `createMutation`'s callbacks run even after the component unmounts. `mutate(vars, { onSuccess, onError })` callbacks are skipped once it has unmounted ([Mutations](https://tanstack.com/query/latest/docs/framework/react/guides/mutations)), so toasts, closing a dialog and form errors go there. A toast that must survive the refetch removing its own component goes on the mutation instead (`UserVoteNotice`, `ScheduleChangeCard`).
- **Return the invalidation** so `isPending` lasts until the fresh data arrives ([TkDodo](https://tkdodo.eu/blog/mastering-mutations-in-react-query)). Use `void` when the refetch would change the open dialog's own content (`ChangePasswordModal`, `ChangeEmailModal`), or when it is heavy and the user doesn't need it first (schedule edits).
- **`isPending` is the busy flag.** Disable the trigger with it, so a double-tap can't send twice.
- **`mutate` by default.** Use `mutateAsync` in `try/catch` only when the caller needs a promise: a browser-API sequence (push subscribe), a child that awaits the action (`SocialConnectionRow`), or calls that can overlap (sync sources). `mutate` only runs the callbacks of its latest call.
- **Forms keep their own `formError`**, set in `onError` and cleared on input, because they mix client-side and API errors. Don't derive it from `mutation.error`. If you do call `mutation.reset()` from an `$effect`, wrap it in `untrack`: reading any field of a mutation result makes the effect depend on all of them.
- **Errors are thrown bodies.** The generated `mutationFn` passes `throwOnError: true`, so `onError` gets the API error body (or the `fetch` TypeError) with no HTTP status, the same as `query.error`. Branch on `getApiErrorCode(error)`.

A plain SDK call (`await sdkCall()`, then check `error`) remains only where no component submits anything: the offline-logout flush, notifications read-on-view, and the `currentUserOptions` query function.

> Query params go under `query`, path params under `path`, and the request body under `body` — flat on the options object, not nested under `params`.

## TypeScript Types

hey-api generates a **named export per schema** into `types.gen.ts` (re-exported from `#lib/api/generated`). Import the type you need directly — do not re-alias it locally. Schema names are normalized to PascalCase, so a backend `…DTO` becomes `…Dto` (e.g. `NotificationDTO` → `NotificationDto`).

```typescript
import type { NotificationDto } from "#lib/api/generated/index.js";
```

Request bodies, query params, and responses are named too — `UpdateSettingsData['body']`, `ListUserNotificationsData['query']`, `GetVotingNominationResponse` — so reach for those instead of hand-walking a `paths[...]` tree. **Do not** reintroduce the old pass-through aliases (`type X = components['schemas']['X']`): with named exports they are pure indirection, and the generated name is the single source of truth. A genuine app-composite type (e.g. `ScheduleEventWithSubscription` in `#lib/types/`) is fine — it _adds_ structure over a generated type, it doesn't just rename one.

### Enum schemas are the single source of truth

Backend `StrEnum`s that appear on a DTO field (`UserRole`, `Permission` in `core/vo/`) are emitted as OpenAPI enum schemas, so `frontend-generate-api` regenerates them as string-literal unions. Never hand-copy enum values on the frontend — import the generated union. Permission literals in `lib/utils/permissions.ts` type their constants as the generated `Permission`, so a backend rename/removal makes the stale literal fail `pnpm check` instead of silently breaking permission checks (same drift-guard idea as the error `code` union below). To expose a new enum on the wire, type a DTO field with the enum (not a plain `NewType` str) and run `just frontend-generate-api`.

### Field conventions

- **An ordered list is ordered by the server.** Clients keep the array's order. Internal sort keys (the schedule's float `order`) stay off the wire, so changing how the server orders rows never breaks a client.
- **A number with a unit names it**: `duration_seconds`, `lead_minutes`.
- **A `PATCH` body is a JSON Merge Patch** ([RFC 7396](https://www.rfc-editor.org/rfc/rfc7396.html)): a missing field is left alone and `null` clears the value. A field that can't be cleared refuses `null` with a 422, so its type is `x?: T`, never `x?: T | null`. On the backend that is `x: T | MISSING = MISSING` (Pydantic's sentinel); `model_dump()` leaves missing fields out. A write that replaces a whole value (the voting window) is a `PUT`.
- **A value that holds for one row at most is named once at the top**, not flagged on every row: the schedule's `current_event_id`, not a per-event `is_current`. The client derives the per-row flag in its view model (`mergeSubscriptions`).

## Mutations & Data Recovery

- **UI Consistency**: after a successful mutation, invalidate the queries it changed — `queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() })` — so what is on screen refetches and the rest refetches when next shown. Keys match by prefix, so a list key covers its infinite variant too. Optimistic writes follow TanStack's order: `cancelQueries`, `setQueryData`, then `invalidateQueries` (mark-all-read zeroing the badge). A local optimistic value can key off the mutation itself instead (a vote counts `+1` while `isPending` and the refetched row doesn't carry it yet).
- **No SvelteKit invalidation**: loads hold no data, so nothing calls `depends`/`invalidate`/`invalidateAll`/`refreshAll` — the last two would also re-run the root load and replace the cache.
- **Return Checking** (plain SDK calls only): success payload, error payload, and response metadata come back on the SDK return (`data`, `error`, `response`). `response` is optional (`response?.ok`, `response?.status`) — a network failure yields `error` with no `response`.
- **A plain SDK call never throws** (`throwOnError` is off on the client): every failure, a dropped connection included, comes back as `error`. So don't wrap one in `try/catch` to handle API failures; that `catch` can't fire for them. The generated query and mutation options are the opposite: they pass `throwOnError: true`, so failures arrive as `query.error` / `onError` (or a rejected `mutateAsync`).

### Client-generated IDs for creates without a natural key

A lost response followed by a second press must not create the row twice. Where a natural key already turns a repeat into a 409 (one vote per nomination, one subscription per event), the server keeps generating the ID. Where nothing would catch the repeat and a duplicate does harm (`POST /notifications/broadcasts` sends to everyone again; `POST /tickets/generate` makes a second batch whose barcodes the organizer never saw), the **client** sends the ID ([ADR-0034](adr/0034-client-generated-ids-for-unkeyed-creates.md)):

- **Generate a UUIDv7 with `uuidv7()` from `#lib/utils/uuidv7`** when the form opens. The server rejects any other version with a 422.
- **Keep it across submits; draw a new one only once the intent is settled**: on success, or on the endpoint's "already exists" 409.
- **The server replays an identical request.** Same caller and payload → the existing resource and the original success status; the side effect does not run again. A different payload under a taken ID → 409.

A `PATCH` that sets a state needs no ID: requesting the state that already holds is a 204 that writes and announces nothing (the schedule edits: set current, skip, move).

### Long-running actions (202 Accepted)

An action that cannot finish inside the request returns **202** with the created record and a `Location` header pointing at a **status resource** the client re-reads, instead of blocking. `POST /sync/{source}` is the first of these: it queues the work, returns the `SyncRunDTO`, and sets `Location: /sync/sources`.

- **The status resource is an existing list endpoint, not a per-run one.** `GET /sync/sources` already reports each source's latest run, including the active one, so a dedicated `GET /sync/runs/{id}` would exist only to satisfy the convention. Add a per-run endpoint if something genuinely needs to poll one run by id — not before.
- **Prefer SSE over polling for progress.** The root layout maps each `SSEEventName` to the query keys it invalidates (here `sync_run_updated` → `getSyncSourcesQueryKey()`), and a reconnect after a gap invalidates the whole cache, so an update missed while the stream was down self-heals rather than leaving a stale "in progress" on screen. Treat the SSE payload as a nudge to refetch, never as the source of truth.
- **A second request while one is running is a 409**, mapped to Russian copy by `code` like any other error — not a silent no-op.

## Inbound webhooks

`/api/webhooks/*` are server-to-server and not called by the frontend. TicketsCloud authenticates with a secret path segment; FestEngine signs per Standard Webhooks. The FestEngine payload contract and event mapping are in [backend.md](backend.md) "FestEngine webhook".

## Russian Localization & Error Handling

Russian copy is mandatory (AGENTS.md, "Never"). API-specific rule: normalize failures before presenting them — never expose raw backend stack traces or internal identifiers, and show a friendly Russian message explaining how to recover or retry.

- **Error shape**: every error response is [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) problem details, `application/problem+json` ([ADR-0044](adr/0044-errors-as-rfc-9457-problem-details.md)): `type`, `title`, `status`, our `code` extension, and problem-specific members (`retry_after`, `reason`, `errors`, …) beside them at the top level (`ProblemDetails`; built by `problem_response()` in backend `presentation/web/exceptions.py`). Map failures by the machine-readable `code`, not by HTTP status, `type` or `title`.
- **Single funnel**: `getApiErrorDetail(error)` (`lib/api/errors.ts`) turns the SDK's `error` into Russian copy — the mapped `code`, or the connection message when the request got no answer (a `TypeError` the network produced, from `fetch` itself or from reading the body after the connection dropped — the client's `fetch` is wrapped to record those, so a `TypeError` from our own code isn't mistaken for one — or a `TimeoutError` from `timeoutSignal`; `isConnectionFailure` exposes that test). Never branch on `response.status` to pick copy. For **inline form errors** use `getApiErrorDetail(error) ?? '<fallback>'`, and first `getApiFieldError(error, '<field>')` for each field that has its own error slot, so a `VALIDATION_ERROR` lands under its input; for **mutations/toasts** use `toastService.error(error, '<fallback>')`; for a **failed query** a page renders `ErrorState` inline with `{ status: 500, message: getApiErrorDetail(query.error) ?? '<fallback>' }`; for a **`load` that awaits a query** use `throwApiError(apiError, fallback)` from the same module — it throws a SvelteKit `error()` with the mapped copy (and carries `code` on `App.Error`), so a load failure looks like every other error instead of a bespoke per-page string. A query rethrows the problem _body_, without the HTTP response, so `throwApiError` takes the page's status from the body's `status` member (a 500 when no API answer came back): a missing record is a 404 page. A load that wants page-specific copy for a "not found" still checks `getApiErrorCode(error)` (`USER_NOT_FOUND`, `NOMINATION_NOT_FOUND`) and throws its own `error(404, …)`. Add new copy to the `ERROR_MESSAGES` dictionary there. (Permission guards and offline-cache-miss states still throw `error()` directly — they have no API `code` to map.)
- **`code` is a typed union**: the backend stamps the closed set of client-facing codes onto `ProblemDetails.code` as an OpenAPI enum (`presentation/web/error_codes.py`), so `frontend-generate-api` regenerates it as a string-literal union. Dictionary keys are checked against it — a typo is a compile error.
- **A distinct failure gets its own `code`, not a sub-reason.** The voting refusals are `VOTING_TICKET_REQUIRED` and `VOTING_DISABLED` (both 403), not `ACCESS_DENIED` plus a `reason`, so the code enum and its drift guard cover them ([AIP-193](https://google.aip.dev/193): one machine-readable reason per failure). Where a code's extension members do steer the copy, the route documents them with a typed model — `InvalidScheduleFileProblem` on the schedule import — so hey-api emits the `InvalidScheduleFileReason` union and `SCHEDULE_FILE_MESSAGES` in `errors.ts` is checked against it with `satisfies Record<…>`; a backend unit test keeps that model and the exception's members in step.
- **A `VALIDATION_ERROR` names the broken limit.** Each error carries Pydantic's `ctx` (`max_length`, `ge`, …), scalars only — never the input, which may be a password — so field copy can say «Максимум 500 символов» rather than «слишком длинное значение».
- **Drift guard**: a compile-time exhaustiveness check in `errors.ts` fails `pnpm check` if the backend adds a client-facing code that is neither given copy nor listed in `GENERIC_FALLBACK_CODES`. After changing backend error codes, run `just frontend-generate-api` and resolve any new code the guard reports.
