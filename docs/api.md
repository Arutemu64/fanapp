# API Integration Guide

This guide details best practices for using `openapi-typescript` and `openapi-fetch` in the SvelteKit frontend to achieve type-safe communication with the FastAPI backend and clean per-request state isolation. The frontend is a client-rendered SPA (`ssr = false`), so the browser talks to the backend directly.

---

## 🛠️ Core Concept: Single Source of Truth
* **Generated Types**: `frontend/src/lib/api/v1.d.ts` is the single source of truth for all API contracts.
* **Auto-generation**: Run `just frontend-generate-api` from the workspace root whenever the backend endpoints, routers, or Pydantic schemas change.
* **Custom Type Transforms**: Any modifications to how types are outputted (e.g. converting FastAPI file uploads or binary schema formats to `Blob` objects) must be registered in `frontend/scripts/generate-api.mjs`.

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
The generated types in `v1.d.ts` contain type definitions for all schemas, query params, paths, requests, and responses. Avoid duplicating types; extract them directly:

### 1. Extracting DTOs and Schemas
Use Svelte 5 / TypeScript syntax to extract specific schemas from `components['schemas']`:
```typescript
import type { components } from '$lib/api/v1';

// Extract the specific Notification model type
export type Notification = components['schemas']['NotificationDTO'];
```

### 2. Extracting Request Parameters and Bodies
To strongly type request parameters or payloads (e.g. inside form submission handlers):
```typescript
import type { paths } from '$lib/api/v1';

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
import type { paths } from '$lib/api/v1';

// Extract the success data payload for GET /voting/nominations
export type NominationsList =
	paths['/voting/nominations']['get']['responses']['200']['content']['application/json'];
```

---

## 🔄 Mutations & Data Recovery
* **UI Consistency**: Define how the UI becomes consistent after mutations (e.g. invalidate layout cache, optimistic update, or full state refetch).
* **Dependency Invalidation**: When a route uses dependency invalidation, call `depends(...)` in the page load and trigger it with `invalidate('app:something')` after a successful mutation.
* **Return Checking**: Success payload, error payload, and response metadata must be checked through `openapi-fetch` returns (`data`, `error`, `response`).

---

## 🇷🇺 Russian Localization & Error Handling
* **No Raw Stack Traces**: Log or normalize API failures before presenting them. Never expose raw backend stack traces or internal identifiers to users.
* **User-friendly Russian Messages**: Show friendly Russian messages in the UI explaining how the user can recover or retry the action.
