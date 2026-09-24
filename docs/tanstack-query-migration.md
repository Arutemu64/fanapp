# TanStack Query migration plan

> [!NOTE]
> **Status: plan.** Read this whole file before implementing any phase. Phase 0
> records the decision as ADR-0018. After phase 5, move the surviving rules into
> [frontend.md](frontend.md) §2 and delete this file.

## Goal

- Pages render **stale-while-revalidate**: paint from cache instantly, refresh in
  the background. Today every navigation waits for the network (up to 3.5 s) and
  uses the cache only on failure.
- Use **TanStack Query defaults**. Delete hand-rolled caching, refetch,
  reachability and retry code. Do not wrap it.
- Target network is **slow, not offline** (crowded venue: high latency, packet
  loss, many transient failures). Design for "content first, quiet refresh".

## Decisions (do not re-open)

| #   | Decision                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Why (one line)                                                                                                                                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Library: `@tanstack/svelte-query` v6 (runes), `@tanstack/query-persist-client-core`, `@tanstack/svelte-query-devtools` (dev). Pin exact. Svelte ≥ 5.25 required (we have 5.57).                                                                                                                                                                                                                                                                                                                                    | v6 is the runes adapter; options are thunks `createQuery(() => opts)`, results are plain objects, no `$`.                                                                                                                                                             |
| D2  | `QueryClient` + one hey-api client are created in the root `+layout.ts` and returned as load data. Root layout component wraps children in `QueryClientProvider`.                                                                                                                                                                                                                                                                                                                                                  | Loads need the cache for guards. Per app instance, not a module singleton (AGENTS.md rule).                                                                                                                                                                           |
| D3  | Root `+layout.ts` has **no `depends()`**. `invalidateAll` is **banned** (ESLint `no-restricted-imports` on `$app/navigation`).                                                                                                                                                                                                                                                                                                                                                                                     | A re-run recreates the client and drops the memory cache.                                                                                                                                                                                                             |
| D4  | Persistence: `persistQueryClient({ queryClient, persister, maxAge, buster })` **called and awaited in the root load**. Returns `[unsubscribe, restoredPromise]`. `unsubscribe` in root layout `onDestroy`.                                                                                                                                                                                                                                                                                                         | Restore must finish before the `(protected)` guard reads identity, else offline boot redirects to `/login`. Do **not** use `PersistQueryClientProvider`.                                                                                                              |
| D5  | Persister: `idb-keyval` `get`/`set`/`del` on the **existing `fanfan-cache` store**. No migration of old entries; start empty. Phase 5 deletes legacy `g:`/`u:` keys with one `delMany`.                                                                                                                                                                                                                                                                                                                            | Two idb-keyval databases upgrading at once race in Firefox; old and new caches coexist during phases 1–4.                                                                                                                                                             |
| D6  | `maxAge = gcTime = 7 days`. `buster = version` from `$app/environment`. Default `staleTime`, `retry`, `networkMode`, `refetchOnWindowFocus`, `refetchOnReconnect`.                                                                                                                                                                                                                                                                                                                                                 | Docs require `gcTime ≥ maxAge`. Defaults are correct behind visible data.                                                                                                                                                                                             |
| D7  | Persist queries unless `meta.persist === false`. Persist only mutations that have a `mutationKey`.                                                                                                                                                                                                                                                                                                                                                                                                                 | Voting/tools must never render stale. Only the logout mutation is replayable.                                                                                                                                                                                         |
| D8  | **Delete the reachability probe** (`reachability.ts`, `offline.svelte.ts`, `reachabilityTransition.ts`). Use the default `onlineManager` (assumes online, follows browser `online`/`offline`).                                                                                                                                                                                                                                                                                                                     | TanStack's own model; v5 dropped `navigator.onLine`. Under SWR a doomed request is a background retry, not a blocked paint.                                                                                                                                           |
| D9  | Query keys carry scope: `['universal', ...]`, `['user', userId, ...]`, `['me']`. Wrapper `$lib/query/keys.ts` prepends scope to hey-api's generated `xxxQueryKey()`.                                                                                                                                                                                                                                                                                                                                               | Logout = `removeQueries({ queryKey: ['user'] })`; another account's key can never match.                                                                                                                                                                              |
| D10 | Generated options come from hey-api plugin `@tanstack/svelte-query` in `openapi-ts.config.ts`. They call the SDK with `throwOnError: true`. The hey-api **error interceptor** wraps whatever is thrown (parsed error body, text, network `TypeError`) into `ApiError extends Error { status, code, details }` in `$lib/api/errors.ts` (`status: 0` = network).                                                                                                                                                     | TanStack learns of failure only from a rejected `queryFn`, and `query.error` must be an `Error`. Supersedes ADR-0017's "never throws" for code inside queries/mutations.                                                                                              |
| D15 | Error handling layers: (a) components render `isLoadingError` → `ErrorState`, `isRefetchError` → stale notice, narrowing with `error instanceof ApiError` where `.code`/`.status` is needed; (b) `QueryCache.onError` → Sentry only, no toast; (c) `MutationCache.onError` → fallback toast, local `onError` wins; (d) `retry: (n, e) => n < 3 && !(e instanceof ApiError && e.status >= 400 && e.status < 500)` in `defaultOptions`. **No** `Register` augmentation, **no** `throwOnError` / `<svelte:boundary>`. | Query `onError` callbacks were removed in v5; cache callbacks fire once per request. A global error type is invisible magic for 2–3 call sites. A boundary unmounts content, the opposite of SWR. Retrying a 4xx three times delays the error state ~7 s for nothing. |
| D11 | Route guards stay in universal `load`. Identity read: `await queryClient.query({ ...meOptions(), staleTime: 'static' })`. Never `ensureQueryData` / `prefetchQuery` (deprecated).                                                                                                                                                                                                                                                                                                                                  | SvelteKit owns redirects; TanStack owns the data.                                                                                                                                                                                                                     |
| D12 | Session expiry: 401 interceptor → `setQueryData(['me'], null)`, `removeQueries({ queryKey: ['user'] })`, `invalidate('app:current-user')`. The `(protected)` guard is the only `depends`.                                                                                                                                                                                                                                                                                                                          | Guard re-runs, reads `null`, redirects.                                                                                                                                                                                                                               |
| D13 | Offline logout = mutation `mutationKey: ['logout']`, `mutationFn` registered via `setMutationDefaults` at client creation, `onMutate` clears identity, `resumePausedMutations()` after restore.                                                                                                                                                                                                                                                                                                                    | Replaces `pendingLogout.ts`. Accept a possible one-round-trip flash of the old user after reconnect unless E2E shows it.                                                                                                                                              |
| D14 | SSE events invalidate queries from **one table in the root layout**. Mutations invalidate their keys in `onSuccess`.                                                                                                                                                                                                                                                                                                                                                                                               | Replaces 15 per-page `eventsClient.on` handlers and 22 `invalidate('app:*')` calls.                                                                                                                                                                                   |

## Do / Don't

- DO read query state in components with `createQuery(() => ({...}))`. DON'T destructure the result.
- DO keep `+page.ts` to guards, params and `title`. DON'T fetch data in `load` (exception: D11 identity).
- DO throw from any custom `queryFn`. DON'T return `{ error }` objects inside TanStack.
- DO narrow with `error instanceof ApiError` where you need `.code` / `.status`. DON'T add `declare module ... Register` or per-query generics.
- DO handle mutation errors in the mutation's own `onError`. DON'T put toasts in `QueryCache.onError`.
- DO use `refetch()` for retry. DON'T call `window.location.reload()`.
- DO show cached content while fetching. DON'T show a skeleton when `data !== undefined`.
- DO write user-facing text in Russian and route it through the `ru-copy` agent. DON'T ship English.
- DON'T add `fetchWithCache` call sites after phase 0. DON'T add new `invalidate('app:*')` keys.
- DON'T write a "reachability", "probe", "confirm window" or "timeout wrapper" module. Defaults only.

## Files

**New (`frontend/src/lib/query/`)**: `client.ts` (QueryClient, `defaultOptions` incl. the D15 retry, `QueryCache`/`MutationCache` callbacks, hey-api client with the `ApiError` interceptor, `setMutationDefaults`), `persister.ts` (idb-keyval persister), `keys.ts` (scoped keys), `online.svelte.ts` (3-line `createSubscriber` over `onlineManager.subscribe`), `sse.ts` (event → keys table).

**Deleted by the end**:

| File                                                                                                | Phase | Replaced by                              |
| --------------------------------------------------------------------------------------------------- | ----- | ---------------------------------------- |
| `lib/utils/reconnectRefresh.ts`                                                                     | 1     | `refetchOnReconnect` default             |
| `lib/services/feed.svelte.ts`, `feedSnapshotKey` in `lib/utils/feed.ts`                             | 2     | `createInfiniteQuery`; keep `dedupeById` |
| `lib/services/unreadCount.svelte.ts`                                                                | 2     | one query                                |
| `lib/utils/pendingLogout.ts`                                                                        | 3     | paused mutation (D13)                    |
| `lib/utils/offlineCache.ts` (+ test)                                                                | 5     | persister (D4/D5)                        |
| `lib/utils/fetchTimeout.ts`                                                                         | 5     | nothing                                  |
| `lib/services/reachability.ts`, `offline.svelte.ts`, `lib/utils/reachabilityTransition.ts` (+ test) | 5     | `onlineManager` (D8)                     |
| `shouldShowStaleNotice`, `offlineMiss`, `offlineUnavailable`, `stale`, `cachedAt` fields            | 1–4   | query result fields (see UI states)      |

**Kept**: `EventsClient` (SSE), `ConnectionBanner` (reads `online.svelte.ts`), `StaleDataNotice` (new copy), `OfflineUnavailableState`, `offlineWriteGate` (reads `online.svelte.ts`), `ErrorState` (retry via `refetch`), skeletons, `dedupeById`, `formatSyncedAt`, `lib/api/errors.ts` (gains the `ApiError` class; its code → Russian mapping reads `error.code`).

## Queries

| Key                             | `staleTime` | Persist | Notes                                                                         |
| ------------------------------- | ----------- | ------- | ----------------------------------------------------------------------------- |
| `['universal', 'schedule']`     | 1 min       | yes     | SSE-invalidated; 1 min is the safety net for a missed event                   |
| `['user', id, 'subscriptions']` | 1 min       | yes     | `enabled: !!user`                                                             |
| `['user', id, 'notifications']` | 1 min       | yes     | infinite query, `placeholderData: keepPreviousData`, `dedupeById` in `select` |
| `['user', id, 'unread-count']`  | 1 min       | yes     | «mark all read» = `setQueryData(0)` + invalidate                              |
| `['me']`                        | 1 min       | yes     | `queryFn`: 200 → user, 401/403 → `null`, else throw                           |
| voting status / nomination      | 0           | no      | `refetchOnMount: 'always'`; submit disabled while `isFetching`                |
| tools pages                     | 0           | no      | online-only                                                                   |

## SSE → invalidate

| Event                    | `invalidateQueries`                                             |
| ------------------------ | --------------------------------------------------------------- |
| `schedule_updated`       | `['universal', 'schedule']`                                     |
| `notification_created`   | `['user', id, 'notifications']`, `['user', id, 'unread-count']` |
| `config_updated`         | voting status                                                   |
| `connection_established` | `queryClient.invalidateQueries()` (everything)                  |

## UI states

| Condition                                                              | Render                                                                                                                  |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `data === undefined && isFetching`                                     | Skeleton (existing 250 ms delay)                                                                                        |
| `data !== undefined && isFetching`                                     | Content unchanged. «Обновляем…» line only after `isFetching` ≥ 1 s. No skeleton, no loader.                             |
| `data !== undefined && (isRefetchError \|\| fetchStatus === 'paused')` | Content + `StaleDataNotice` (neutral, not warning): «Обновлено в HH:MM» from `dataUpdatedAt` + «Обновить» → `refetch()` |
| `data === undefined && fetchStatus === 'paused'`                       | Offline empty state («недоступно офлайн»)                                                                               |
| `data === undefined && isError`                                        | `ErrorState`, retry → `refetch()`; connectivity wording when `onlineManager.isOnline() === false`                       |

## UX rules (each phase says which it lands)

1. Never block on a request when data exists. Cache first, refresh behind.
2. No spinner for background refreshes (< 1 s needs no feedback). Skeleton only on cold cache.
3. One freshness signal: `ConnectionBanner` = device offline («Нет интернета»); `StaleDataNotice` = this data failed to refresh, with time. Never both for the same cause.
4. Retry = `refetch()`. Never a full reload.
5. Subscribe / unsubscribe are optimistic via cache: `onMutate` snapshot + write, `onError` rollback + toast, `onSettled` invalidate.
6. Lists stay stable during refresh: structural sharing, `keepPreviousData`, notifications feed shows «новые» pill instead of shifting items.
7. `overscroll-behavior-y: contain` on the scrolling `<main>` (stops PWA pull-to-refresh full reload; not Baseline, progressive).
8. Retries: default count and backoff (3, exponential) for network and 5xx; no retry on 4xx (D15 retry function).
9. Candidate, decide in phase 1: queue subscriptions offline as paused mutations («Подпишем, когда появится связь»). Votes/feedback stay online-only. Land it with phase 1 or drop it; do not defer.

All copy is provisional → `ru-copy` agent before shipping.

## Phases

One PR per phase. Every gate green. App deployable after each. PR description states lines removed vs added; net-positive phases are re-scoped.

### Phase 0 — groundwork (no behaviour change)

- [ ] Add D1 dependencies (exact pins; extend `renovate.jsonc` if grouping is needed).
- [ ] Create `$lib/query/*` files (D2, D4, D5, D6, D7, D9, D13 `setMutationDefaults`, D15 retry + cache callbacks). Add `ApiError` to `$lib/api/errors.ts` and the wrapping error interceptor (D10). Nothing uses them yet.
- [ ] Root `+layout.ts`: create client + persister, await restore, return `{ queryClient, api }`. Root `+layout.svelte`: `QueryClientProvider`, devtools (dev only), `unsubscribe` in `onDestroy`.
- [ ] `openapi-ts.config.ts`: add `'@tanstack/svelte-query'` plugin; `just frontend-generate-api`; `just frontend-check-api`.
- [ ] ESLint: ban `invalidateAll` (D3).
- [ ] Write ADR-0018 (decisions D1–D14, rejected: hand-rolled SWR layer, `PersistQueryClientProvider`, reachability probe).
- [ ] Record `vite build` size report for comparison.

Exit: gates green, no runtime change.

### Phase 1 — schedule

- [ ] `schedule/+page.ts` → `({ title: 'Программа' })`. Page: two `createQuery` (schedule, subscriptions) merged in `$derived`.
- [ ] `SubscribeModal`, `UnsubscribeModal`, `MoveEventModal`, `EventCard`: `createMutation`; subscribe/unsubscribe optimistic (UX 5). Decide UX 9.
- [ ] SSE table rows `schedule_updated`, `connection_established` live. Remove page's visibility `$effect` and `eventsClient.on` handlers.
- [ ] `warmCache(schedule)` → `void queryClient.query(getScheduleOptions(...))` in root layout `onMount`.
- [ ] Delete `reconnectRefresh.ts`; remove `OfflineService.#commit` refresh.
- [ ] UX 2, 3, 4, 7: «Обновляем…» gate, neutral `StaleDataNotice` + «Обновить», `ErrorState` retry → `refetch()`, `overscroll-behavior-y: contain`. Delete `shouldShowStaleNotice`.
- [ ] E2E: `realtime.spec.ts` still passes; new cache-first spec (online load → `context.setOffline(true)` → reload → list renders, notice shows, banner shows «Нет интернета», not both for one cause).

Exit: tab switch paints from memory; offline reload paints from IndexedDB; throttled network shows content, no skeleton; net lines removed.

### Phase 2 — notifications, bell, unread count

- [ ] `notifications/+page.ts` → title only. Page: `createInfiniteQuery` (offset/limit, `keepPreviousData`, `dedupeById` in `select`) (UX 6).
- [ ] `(app)/+layout.ts` stops streaming the seed. `NotificationBell` reads the two queries.
- [ ] Delete `UnreadCountService`. «Mark all read» = `setQueryData(count, 0)` + invalidate.
- [ ] SSE row `notification_created` live; remove bell/feed handlers. «новые» pill for live arrivals (UX 6).
- [ ] `schedule/changes` → same infinite-query shape. Delete `PaginatedFeed`, `feedSnapshotKey`.
- [ ] `notifications.spec.ts` re-verified.

### Phase 3 — identity and logout (riskiest; do last among data phases)

- [ ] `['me']` query per table. Root `+layout.ts` no longer fetches `/me` (UX 1 at boot).
- [ ] `(protected)` and `(auth)` guards: `queryClient.query({ ...meOptions(), staleTime: 'static' })` (D11). `(protected)` keeps `depends('app:current-user')`.
- [ ] 401 interceptor per D12.
- [ ] Logout mutation per D13; delete `pendingLogout.ts`; `AppNavbar.handleLogout` = one `mutate()`.
- [ ] Subscriptions warm-up → `queryClient.query()` after login.
- [ ] E2E: offline boot with persisted user stays logged in; logout offline → reconnect → `POST /auth/logout` observed. Decide the D13 flash trade-off here.

### Phase 4 — remaining surfaces

- [ ] Voting (`voting/+layout.ts`, `voting/+page.ts`, `voting/[nominationCode]/+page.ts`), feedback, `tools/*`: loads → guards/params/title; pages → `createQuery` with the voting/tools row of the table.
- [ ] `offlineUnavailable` → `fetchStatus === 'paused'`; keep `OfflineUnavailableState`.
- [ ] Voting boundary timer → `refetchInterval` function (ms to next boundary).

### Phase 5 — cleanup

- [ ] Delete `offlineCache.ts` (+ test), `fetchTimeout.ts`, `reachability.ts`, `offline.svelte.ts`, `reachabilityTransition.ts` (+ test). `ConnectionBanner`, `ErrorState`, `offlineWriteGate` read `online.svelte.ts`. Banner keeps only «Нет интернета» (UX 3 app-wide).
- [ ] One `delMany` of legacy `g:`/`u:` keys in `fanfan-cache`.
- [ ] Docs, same PR: frontend.md §2 (replace the offline/identity/connectivity bullets with the tables above), api.md «Client Isolation» + «Mutations & Data Recovery» + «Russian Localization & Error Handling» (D2, D10, D15), testing.md frontend section (new E2E specs), codebase map (`lib/query/`). Delete this file.

## Risks

| Risk                                                    | Mitigation                                                                                                    |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| v6 adapter is young                                     | Exact pins; Renovate bumps run E2E                                                                            |
| Root load re-runs → client recreated                    | D3; persisted cache restores anyway                                                                           |
| Restore delays first paint                              | One small IndexedDB read; measure cold start in phase 3                                                       |
| Optimistic write lost on refresh before invalidation    | Every mutation invalidates in `onSettled`; showing pre-mutation state is honest                               |
| Logout / `me` refetch race after reconnect              | D13; decide with phase 3 E2E                                                                                  |
| Captive portal + empty cache → ~7 s skeleton then error | Accepted (first-ever open only). 4xx already skip retries (D15); network errors keep the 3 retries on purpose |
| Thrown errors reach code written for returned errors    | Only generated options throw; direct SDK calls keep ADR-0017 until migrated                                   |
| Stale schedule shown confidently                        | SSE + focus refetch while online; time-stamped notice when refresh fails                                      |
| Silent refresh hides changes                            | Stable rows; «новые» pill; `notification_created` already toasts; `schedule_updated` stays silent by design   |

## Sources

- Defaults — <https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults>
- Svelte adapter v6 — <https://tanstack.com/query/latest/docs/framework/svelte/overview>, <https://tanstack.com/query/latest/docs/framework/svelte/migrate-from-v5-to-v6>, SvelteKit — <https://tanstack.com/query/latest/docs/framework/svelte/ssr>
- persistQueryClient — <https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient>; signature — <https://github.com/TanStack/query/blob/main/packages/query-persist-client-core/src/persist.ts>
- `queryClient.query()` / deprecations — <https://tanstack.com/query/latest/docs/reference/QueryClient>
- onlineManager — <https://tanstack.com/query/latest/docs/reference/onlineManager>, source — <https://github.com/TanStack/query/blob/main/packages/query-core/src/onlineManager.ts>, v5 note — <https://tanstack.com/query/latest/docs/framework/react/guides/migrating-to-v5>
- Offline / WebSockets (TkDodo) — <https://tkdodo.eu/blog/offline-react-query>, <https://tkdodo.eu/blog/using-web-sockets-with-react-query>
- Focus refetch — <https://tanstack.com/query/latest/docs/framework/react/guides/window-focus-refetching>; network mode — <https://tanstack.com/query/latest/docs/framework/react/guides/network-mode>; retries — <https://tanstack.com/query/latest/docs/framework/react/guides/query-retries>
- Mutations persist/resume — <https://tanstack.com/query/latest/docs/framework/react/guides/mutations>; optimistic updates — <https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates>
- useQuery fields — <https://tanstack.com/query/latest/docs/framework/react/reference/useQuery>
- hey-api plugin — <https://heyapi.dev/openapi-ts/plugins/tanstack-query>; generated example — <https://github.com/hey-api/openapi-ts/blob/main/examples/openapi-ts-tanstack-svelte-query/src/client/%40tanstack/svelte-query.gen.ts>
- SvelteKit auth — <https://svelte.dev/docs/kit/auth>
- Offline UX (web.dev) — <https://web.dev/articles/offline-ux-design-guidelines>; response times (NN/g) — <https://www.nngroup.com/articles/response-times-3-important-limits/>; `overscroll-behavior` — <https://developer.mozilla.org/en-US/docs/Web/CSS/overscroll-behavior>
- Crowded-venue cellular — <https://web.cs.ucdavis.edu/~zubair/files/crowded_sigmetrics.pdf>, <https://arxiv.org/abs/2607.16008>
- Error handling (TkDodo) — <https://tkdodo.eu/blog/react-query-error-handling>; v5 migration (query callbacks removed, `throwOnError`) — <https://tanstack.com/query/latest/docs/framework/react/guides/migrating-to-v5>; global error type (not used, see D15) — <https://tanstack.com/query/latest/docs/framework/react/typescript>; `<svelte:boundary>` — <https://svelte.dev/docs/svelte/svelte-boundary>
- Maintainer notes — <https://github.com/TanStack/query/discussions/8696>, <https://github.com/TanStack/query/discussions/9585>
