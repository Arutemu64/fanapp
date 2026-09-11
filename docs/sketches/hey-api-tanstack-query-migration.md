# Sketch — migrate the data layer to hey-api + TanStack Query (with offline caching)

> **STATUS: ADOPTED.** The codegen and transport swap (§ below, and the traps in
> §1–§6) has landed for the whole app: `openapi-typescript` + `openapi-fetch` are
> gone, every call site is on the hey-api SDK, and `docs/api.md` describes the
> current stack. What has **not** landed is the offline persister (§4) — every
> page's `fetchWithCache`/`warmCache` + `idb-keyval` caching is unchanged, and no
> page has been moved onto `createQuery`/`createMutation` for its data yet except
> `tools/settings` (online-only, no offline story to migrate). The rest of this
> file is kept as the design record for that remaining work — the reasoning below
> is still current, the "not accepted" framing is not. Consider promoting the
> decision to an ADR (the SPA choice is [ADR-0007]) now that it has shipped.

## Why look at this

The frontend today hand-rolls three concerns that a server-state library owns as
one: **fetching** (`openapi-fetch` + per-context `createApiClient`, `docs/api.md`),
**caching/offline** (`fetchWithCache` / `warmCache` / the `{value, cachedAt}`
envelope over `idb-keyval`, `docs/frontend.md` §2), and **freshness**
(SvelteKit `load` + `depends`/`invalidate`, nudged by SSE). It works, but every
read-page re-implements the offline dance by hand, and there is no dedupe,
background refetch, or request-coalescing across components — only SvelteKit's
`load`-level dedupe.

The 2026 stack that covers all three with less bespoke code:

- **[hey-api] (`@hey-api/openapi-ts`)** — same input we already generate from
  (`shared/openapi/openapi.json`), but emits a **type-safe SDK** plus a
  **TanStack Query plugin** (query/mutation options + query keys) instead of just
  types. Replaces `openapi-typescript` + `openapi-fetch`.
- **[TanStack Query] `@tanstack/svelte-query` v6** — the **Svelte 5 runes** adapter
  (the v5 adapter was store-based and unreliable under Svelte 5). Owns dedupe,
  background refetch, stale-tracking, retries, invalidation. The **v6 is only the
  adapter's own version line** (bumped for the runes rewrite); it rides
  `@tanstack/query-core` **v5**, so the cache/persistence engine — and the docs
  for it — are **v5**. `@tanstack/svelte-query-persist-client` is the matching
  Svelte companion (also on the 6.x adapter line, same v5 core).
- **[`persistQueryClient`][persist] + [`createAsyncStoragePersister`][asyncpersister]**
  — the **stable** whole-cache persistence path, wrapped over our existing
  `idb-keyval` store. This is what subsumes `fetchWithCache`/`warmCache`. The
  per-query `experimental_createQueryPersister` is tidier in theory but still
  carries the `experimental` flag — **declined** for a production app; its only
  real edge (per-key granularity) we get through query-key namespacing anyway
  (see §4).

All version/API claims below were checked against current docs (Sept 2026);
**re-verify exact versions at implementation time** — do not trust this file's
memory of them (AGENTS.md "Research the current best practice").

## What each piece replaces

| Today                                                                      | After                                                                     | Notes                                                                    |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `openapi-typescript` → `schema.d.ts` (types only)                          | `@hey-api/openapi-ts` → SDK + types + TanStack options                    | Same spec input; `just frontend-generate-api` rewires to the hey-api CLI |
| `openapi-fetch` `createApiClient()` per context                            | `@hey-api/client-fetch` client + generated SDK fns                        | Interceptors replace middleware (below)                                  |
| `reachabilityWatch` / `sessionExpiryWatch` middleware (`lib/api/index.ts`) | `client.interceptors.response.use(...)`                                   | Straight port — see §3                                                   |
| `fetchWithCache` + `{value,cachedAt}` envelope                             | `persistQueryClient` (async idb-keyval persister) over `fanfan-cache`      | `cachedAt` → query `dataUpdatedAt`; `stale` → query `isStale`            |
| `warmCache` on boot                                                        | `queryClient.prefetchQuery(opts)`                                         | Same fire-and-forget intent                                              |
| `load` + `depends('app:x')` + `invalidate('app:x')`                        | `ensureQueryData` in `load` + `invalidateQueries({queryKey})`             | Keeps blocking-load UX (below)                                           |
| `clearUserCache()` on logout                                               | `queryClient.removeQueries({queryKey})` by scope prefix + persister purge | Scope maps onto query-key prefixes                                       |
| SSE → `invalidate(...)`                                                    | SSE → `invalidateQueries(...)`                                            | Unchanged in spirit                                                      |
| `getApiErrorDetail` / `ERROR_MESSAGES` / typed `code` union                | **kept**, called from a global `QueryCache`/`MutationCache` `onError`     | The Russian-copy funnel stays; see §6                                    |

## The repo-specific traps (this is the actual work)

### 1. QueryClient is a singleton — our rules forbid singletons. Reconcile it.

`docs/api.md` and `docs/frontend.md` §1 **forbid** a module-singleton API client
because mutable per-user state bleeds across login/logout in the SPA. A
`QueryClient` _is_ a long-lived singleton by design — so this rule has to be met,
not ignored:

- The ban is on **mutable session state** leaking, not on a shared stateless fetch
  layer. A configured hey-api client (baseUrl + `credentials:'include'`) holds no
  user state, so one shared client is fine.
- The **cache** is the thing that holds user data. On logout we must do what
  `clearUserCache()` does today: `queryClient.removeQueries({ queryKey: ['me'] })`
  (and every other per-user key), **and** purge those keys from the persister.
  Universal keys (`['schedule']`) survive, exactly as `universalScope` does now.
- Construct the `QueryClient` **inside the root `+layout.svelte`** (component
  instance), passed down via `QueryClientProvider`, rather than as a
  module-level `export const queryClient`. That keeps it out of module scope and
  honours the isolation rule's intent even though its lifetime is app-wide in an
  SPA.

**This is the crux of the review.** If we can't express the scoped-clear cleanly,
the migration isn't worth it.

### 2. `load`-blocking UX must survive (skeletons, section gate)

`docs/frontend.md` §4 "Section loading" relies on `load` **blocking** navigation so
the shell can show a skeleton. Pure component-level `createQuery` breaks that — the
page commits instantly and flickers.

Keep the `load` and have it warm the cache, so blocking + skeletons are unchanged:

```ts
// +page.ts — load still blocks; TanStack owns the cache underneath
export const load: PageLoad = async ({ fetch, parent }) => {
  const { queryClient } = await parent(); // provided from root layout
  await queryClient.ensureQueryData(
    getScheduleOptions({ fetch }), // hey-api-generated options
  );
  return { title: "Программа" };
};
```

Then the component reads the same key reactively and gets background refetch/SSE
invalidation for free:

```svelte
<script lang="ts">
  const query = createQuery(() => getScheduleOptions());   // v6: options as a THUNK
</script>
```

Passing SvelteKit's `fetch` into the `load`-side `ensureQueryData` still matters
(relative `/api` base, cookie carry — `docs/api.md`); the component-side call runs
client-only so the global fetch is fine.

> Open question for review: is the `ensureQueryData`-in-load hybrid worth keeping,
> or do we accept a component-level `createQuery` + a TanStack-driven pending state
> and retire the `load`-blocking skeleton machinery? The hybrid is less churn and
> preserves current feel; the pure version is simpler but changes the loading feel
> on every page.

### 3. Middleware → interceptors (straight port)

The two `openapi-fetch` middleware become response interceptors on the hey-api
client, same logic:

```ts
client.interceptors.response.use((response, request) => {
  // reachabilityWatch: a non-gateway answer proves the backend is up
  markReachable(!isBackendUnreachableStatus(response.status));

  // sessionExpiryWatch: 401 (except /me and credential logins) → reconcile identity
  if (
    response.status === 401 &&
    !CREDENTIAL_CHECK_PATHS.has(new URL(request.url).pathname)
  ) {
    // same debounced invalidate('app:current-user') → invalidateQueries(['me'])
  }
  return response;
});
```

Note the path match is now against the real URL, not openapi-fetch's `schemaPath`;
keep the `CREDENTIAL_CHECK_PATHS` set and the `reconcilingSession` latch verbatim.

### 4. Offline cache → whole-client persistence (reuse the existing IDB store)

Use the **stable** `persistQueryClient` path — **not** the experimental per-query
persister. It dehydrates the whole cache to one key and restores it on boot,
rewriting on a throttle (1s default). For our cache size (schedule +
subscriptions + identity) the single-blob write is a non-issue, and it keeps
production off any `experimental`-flagged dependency. Wrap the existing
`fanfan-cache` `idb-keyval` store in a `createAsyncStoragePersister` so we do
**not** open a second IndexedDB database (the Firefox double-upgrade race the
current code documents still applies):

```ts
const persister = createAsyncStoragePersister({
  storage: {
    getItem: (k) => idbGet(k, cacheStore),
    setItem: (k, v) => idbSet(k, v, cacheStore),
    removeItem: (k) => idbDel(k, cacheStore),
  },
  throttleTime: 1000,
});

persistQueryClient({
  queryClient,
  persister,
  maxAge: OFFLINE_WINDOW_MS, // was implicit in fetchWithCache
  buster: OPENAPI_INFO_VERSION, // bust on schema/deploy — reuse info.version
  dehydrateOptions: {
    // only read-only surfaces persist; mutation-only pages never do
    shouldDehydrateQuery: (q) => PERSIST_PREFIXES.has(q.queryKey[0] as string),
  },
});
```

- Set `networkMode: 'offlineFirst'` on persisted queries (via `defaultOptions`)
  so a restored query paints instantly and only hits the network when reachable —
  this _is_ the `if (!isReachable()) serve cache` branch, now declarative. The
  whole-client persister does not imply it the way the experimental one does, so
  set it explicitly.
- **Scope (user vs universal)** maps onto **query-key prefixes**: per-user keys like
  `['me']`, `['subscriptions', userId]`, `['notifications']`; universal like
  `['schedule']`. Because the blob is re-dehydrated from **live client state**,
  logout just `queryClient.removeQueries({ queryKey: ['me'] })` (+ the other
  per-user keys) and the next throttled save rewrites the blob with only universal
  queries left — no manual persister purge, no `u:`/`g:` string prefixes. Same
  guarantee, expressed through keys. `shouldDehydrateQuery` additionally keeps
  mutation-only surfaces (voting, feedback, tools) out of storage entirely — that
  is today's `offlineUnavailable` contract.
- `StaleDataNotice` reads `query.dataUpdatedAt` (→ `formatSyncedAt`) and
  `query.isStale`; `offlineMiss` = `status==='error' && data===undefined &&
!isReachable()`. The three offline states (`offlineMiss` / `offlineUnavailable` /
  `offlineWriteGate`, §2 of frontend.md) keep their copy; only their _source_ flips
  from `fetchWithCache` bookkeeping to query state + reachability.

**Why not `experimental_createQueryPersister`** (the per-query one): its only real
edge over the whole-client path is per-key storage granularity, which we already
get through query-key namespacing + `removeQueries`. Shipping an
`experimental`-flagged dependency to production is not worth that. Revisit only if
the cache grows large enough that one-blob writes measurably hurt (check via
DevTools timing) — not the case at our size.

### 5. Mutations stay online-only

Votes and settings are online-only today (`docs/frontend.md` §2). `useMutation`
with `networkMode: 'online'` keeps that — no offline write queue (the one exception,
`pendingLogout`, stays hand-rolled; it is an intent latch, not a query). After a
mutation, `invalidateQueries` the affected keys — replacing the current
`invalidate('app:x')` calls. The 202/`Location` long-running pattern (`POST /sync`)
and its SSE-nudge-then-refetch become `invalidateQueries(['sync','sources'])` on the
`sync_run_updated` event.

### 6. Error funnel and the typed `code` union — keep, but re-source the types

`errors.ts` (the `ERROR_MESSAGES` dictionary, `getApiErrorDetail`, `throwApiError`,
and the **compile-time exhaustiveness guard** over the backend `code` enum) is the
part we must not lose — it is what keeps every failure in mapped Russian copy
(`docs/api.md`). Plan:

- Route all query/mutation errors through a global `QueryCache({ onError })` /
  `MutationCache({ onError })` that calls the existing `toastService.error(err)` /
  `throwApiError(...)`. For `load` failures, `ensureQueryData` still throws, so
  `throwApiError` works unchanged.
- The typed `code` union and the `Permission`/`UserRole` enums are currently
  extracted from `schema.d.ts` (`components['schemas'][...]`). hey-api generates
  these too, but under **different type names/paths**, so `errors.ts`,
  `lib/utils/permissions.ts`, and every `paths[...]`/`components[...]` extraction
  (the patterns in `docs/api.md` §TypeScript Type Extraction) churn. This is the
  **widest-blast-radius** edit: 51 files import `createApiClient`/the schema types.
  The drift guards (the exhaustiveness check, `frontend-check-api`) must be
  re-pointed at hey-api's output, and CI (`test_openapi_spec.py` still owns the
  spec; the `schema.d.ts` check becomes a hey-api-output check).

## Incremental path (both stacks coexist)

This does **not** have to be a big-bang. hey-api reads the same spec, and TanStack
can be adopted one route at a time:

1. **Scaffold** — add `@hey-api/openapi-ts`, `@tanstack/svelte-query` (v6),
   `@tanstack/svelte-query-persist-client` + `@tanstack/query-async-storage-persister`;
   rewire `just frontend-generate-api` to emit both
   the SDK and (temporarily) keep `schema.d.ts` types so nothing breaks. Mount
   `QueryClientProvider` in the root layout; build the persister over `fanfan-cache`.
2. **Port the interceptors** (§3) and the error funnel (§6) behind the new client,
   proving parity against `openapi-fetch` on one endpoint.
3. **Migrate one read page end-to-end** — schedule is the best pilot: it is the
   canonical offline + SSE-invalidation + `warmCache`-on-boot case, so it exercises
   every trap at once. Ship it, verify offline with `just run-prod` (the SW/offline
   path is inert in `vite dev`, `docs/frontend.md` §2).
4. **Roll route-by-route**, deleting `fetchWithCache`/`warmCache`/the envelope only
   when the last caller is gone.
5. **Flip the type extraction** (§6) and remove `openapi-fetch` +
   `createApiClient` once all 51 callers are migrated. Update `docs/api.md`,
   `docs/frontend.md` §2, and the codebase map in the same change (AGENTS.md
   "Staying in sync").

## Recommendation / decision needed

- **Worth doing** for the offline-heavy read surfaces (schedule, notifications,
  profile): the persister + background refetch genuinely replaces hand-rolled code
  and gives dedupe/freshness we don't have.
- **The gating decisions for review**: (a) the singleton-vs-isolation resolution in
  §1, (b) keep the `load`-blocking hybrid or not in §2, (c) appetite for the §6
  type-extraction churn across 51 files.
- **Versioning**: this is a new external dependency set + a changed build-gen
  topology → it warrants an **ADR** if accepted, and is at least a MINOR bump
  (human call — `docs/dependencies.md`). Not a self-initiated version edit.

[hey-api]: https://heyapi.dev/openapi-ts/plugins/tanstack-query
[TanStack Query]: https://tanstack.com/query/latest/docs/framework/svelte/overview
[persist]: https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient
[asyncpersister]: https://tanstack.com/query/latest/docs/framework/react/plugins/createAsyncStoragePersister
[ADR-0007]: ../adr/0007-client-rendered-spa-frontend.md
