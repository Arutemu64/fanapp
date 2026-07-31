# API Integration Guide

This guide details best practices for using `openapi-typescript` and `openapi-fetch` in the SvelteKit frontend to achieve type-safe communication with the FastAPI backend and clean per-request state isolation. The frontend is a client-rendered SPA, so the browser talks to the backend directly.

---

## 🛠️ Core Concept: Single Source of Truth
* **Generated Types**: `frontend/src/lib/api/schema.d.ts` is the single source of truth for all API contracts.
* **Auto-generation**: Run `just frontend-generate-api` from the workspace root whenever the backend endpoints, routers, or Pydantic schemas change.
* **Custom Type Transforms**: Any modifications to how types are outputted (e.g. converting FastAPI file uploads or binary schema formats to `Blob` objects) must be registered in `frontend/scripts/generate-api.mjs`.

### Both generated artifacts are enforced in CI

Forgetting to regenerate is not a silent failure — two committed artifacts each have a check, because a stale one still compiles and would quietly disarm every guard below.

| Artifact | Generated from | Checked by |
| --- | --- | --- |
| `shared/openapi/openapi.json` | the routers and DTOs | `backend/tests/unit/presentation/test_openapi_spec.py` (runs with `just backend-test` and `just ci`) |
| `frontend/src/lib/api/schema.d.ts` | that spec | `just frontend-check-api` (`pnpm generate-api:check`; its own CI job) |

`just frontend-generate-api` regenerates both and fixes either failure.

**`info.version` is compared separately, against `pyproject.toml`.** It is the one field in the spec whose value comes from outside the repo: `APP_VERSION` reads the *installed* distribution metadata, so a stale editable install (common right after a release bump, before `uv sync`) makes it disagree with `pyproject.toml` and would fail a whole-document comparison over a field that has not drifted. The spec test therefore renders with the version the committed file already carries — leaving every other byte compared — and a second test checks `info.version` against `pyproject.toml`. Both of that test's inputs are committed files, so it gives the same answer on a laptop, in CI, and in a cloud session.

The general rule when adding to the spec: **a value that is not derived from committed source does not belong in a committed artifact.** `APP_BUILD` (the commit SHA) is the reason this matters — putting it in `info` would churn the spec, and `schema.d.ts` with it, on every single commit. Keep build- and environment-derived values on a runtime endpoint (`/debug/`) instead, and if one has to be in the spec, give it its own test against its own source of truth rather than the byte comparison.

---

## 🔒 Client Isolation
A shared global/module singleton API client can accumulate mutable state that bleeds across navigations and login/logout, so **never use one**.

Instead, always instantiate a local client per context using `createApiClient()`.

### 1. Universal load functions (`+page.ts` / `+layout.ts`)
Inside universal load functions, initialize the client locally and **always inject the SvelteKit-provided `fetch`**:

```typescript
import { createApiClient } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, depends }) => {
	depends('app:settings');

	// 1. Initialize client locally (Request isolated)
	const client = createApiClient();

	// 2. Perform request and pass SvelteKit's fetch
	const { data, error, response } = await client.GET('/settings', { fetch });

	if (error || !response.ok) {
		// Handle/log error...
	}

	return { settings: data };
};
```

> [!IMPORTANT]
> **Why inject the SvelteKit-provided `fetch` in load functions?**
> * **Request deduplication**: SvelteKit dedupes identical requests and lets `invalidate()` re-run the load when its data changes.
> * **Relative URL Resolution**: SvelteKit resolves relative routes correctly.
> * **Cookies**: The `session_id` cookie is carried automatically by the browser; the client uses `credentials: 'include'` and the frontend is served same-origin with the API (behind Caddy), so it stays first-party.

---

### 2. Browser & Svelte Component Context
For local component scripts (`.svelte`), page layouts, or event handlers that only run in the browser, initialize a local client at the top of the `<script>` tag:

```svelte
<script lang="ts">
	import { createApiClient } from '$lib/api';
	import { onMount } from 'svelte';

	// Create local client for this component instance
	const client = createApiClient();
	let notifications = $state([]);

	async function loadNotifications() {
		const { data } = await client.GET('/notifications/', {
			params: { query: { limit: 10 } }
		});
		if (data) notifications = data.notifications;
	}

	onMount(() => {
		void loadNotifications();
	});
</script>
```

---

## 🏷️ TypeScript Type Extraction
The generated types in `schema.d.ts` contain type definitions for all schemas, query params, paths, requests, and responses. Avoid duplicating types; extract them directly:

### 1. Extracting DTOs and Schemas
Use Svelte 5 / TypeScript syntax to extract specific schemas from `components['schemas']`:
```typescript
import type { components } from '$lib/api/schema';

// Extract the specific Notification model type
export type Notification = components['schemas']['NotificationDTO'];
```

### 2. Extracting Request Parameters and Bodies
To strongly type request parameters or payloads (e.g. inside form submission handlers):
```typescript
import type { paths } from '$lib/api/schema';

// Extract the Request Body type for PATCH /settings
export type UpdateSettingsPayload =
	paths['/settings']['patch']['requestBody']['content']['application/json'];

// Extract Query Parameter types
export type NotificationQuery =
	paths['/notifications/']['get']['parameters']['query'];
```

### 3. Extracting Response Types
To type-safely extract the success response payload of a specific endpoint:
```typescript
import type { paths } from '$lib/api/schema';

// Extract the success data payload for GET /voting/nominations
export type NominationsList =
	paths['/voting/nominations']['get']['responses']['200']['content']['application/json'];
```

### 4. Enum schemas are the single source of truth
Backend `StrEnum`s that appear on a DTO field (`UserRole`, `Permission` in `core/vo/`) are emitted as OpenAPI enum schemas, so `frontend-generate-api` regenerates them as string-literal unions (`components['schemas']['Permission']`). Never hand-copy enum values on the frontend — derive them. Permission literals in `lib/utils/permissions.ts` are typed as `Permission = components['schemas']['Permission']`, so a backend rename/removal makes the stale literal fail `pnpm check` instead of silently breaking permission checks (same drift-guard idea as the error `code` union below). To expose a new enum on the wire, type a DTO field with the enum (not a plain `NewType` str) and run `just frontend-generate-api`.

---

## 🔄 Mutations & Data Recovery
* **UI Consistency**: Define how the UI becomes consistent after mutations (e.g. invalidate layout cache, optimistic update, or full state refetch).
* **Dependency Invalidation**: When a route uses dependency invalidation, call `depends(...)` in the page load and trigger it with `invalidate('app:something')` after a successful mutation.
* **Return Checking**: Success payload, error payload, and response metadata must be checked through `openapi-fetch` returns (`data`, `error`, `response`).

### Long-running actions (202 Accepted)

An action that cannot finish inside the request returns **202** with the created record and a `Location` header pointing at a **status resource** the client re-reads, instead of blocking. `POST /sync/{source}` is the first of these: it queues the work, returns the `SyncRunDTO`, and sets `Location: /sync/sources`.

* **The status resource is an existing list endpoint, not a per-run one.** `GET /sync/sources` already reports each source's latest run, including the active one, so a dedicated `GET /sync/runs/{id}` would exist only to satisfy the convention. Add a per-run endpoint if something genuinely needs to poll one run by id — not before.
* **Prefer SSE over polling for progress.** The page subscribes to the relevant `SSEEventName` (here `sync_run_updated`) and calls `invalidate(...)`; it also re-invalidates on `connection_established`, so an update missed while the stream was down (or the tab was backgrounded past the pause grace) self-heals on reconnect rather than leaving a stale "in progress" on screen. Treat the SSE payload as a nudge to refetch, never as the source of truth.
* **A second request while one is running is a 409**, mapped to Russian copy by `code` like any other error — not a silent no-op.

---

## 🇷🇺 Russian Localization & Error Handling
Russian copy is mandatory (AGENTS.md, "Never"). API-specific rule: normalize failures before presenting them — never expose raw backend stack traces or internal identifiers, and show a friendly Russian message explaining how to recover or retry.

* **Error shape**: every error response is `ErrorMessage { code, details }` (see backend `presentation/web/exceptions.py`). Map failures by the machine-readable `code`, not by HTTP status or message text.
* **Single funnel**: `getApiErrorDetail(error)` (`lib/api/errors.ts`) turns a payload into Russian copy. For **mutations/toasts** use `toastService.error(err)`; for **`load` failures** use `throwApiError(apiError, response, fallback)` from the same module — it throws a SvelteKit `error()` with the mapped copy and the real HTTP status (and carries `code` on `App.Error`), so a load failure looks like every other error instead of a bespoke per-page string. Add new copy to the `ERROR_MESSAGES` dictionary there. (Permission guards and offline-cache-miss states still throw `error()` directly — they have no API `code` to map.)
* **`code` is a typed union**: the backend stamps the closed set of client-facing codes onto `ErrorMessage.code` as an OpenAPI enum (`presentation/web/error_codes.py`), so `frontend-generate-api` regenerates it as a string-literal union. Dictionary keys are checked against it — a typo is a compile error.
* **Drift guard**: a compile-time exhaustiveness check in `errors.ts` fails `pnpm check` if the backend adds a client-facing code that is neither given copy nor listed in `GENERIC_FALLBACK_CODES`. After changing backend error codes, run `just frontend-generate-api` and resolve any new code the guard reports.
