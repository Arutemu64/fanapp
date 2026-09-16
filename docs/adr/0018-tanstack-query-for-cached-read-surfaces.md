# ADR-0018: TanStack Query for the cached read surfaces, persisted to IndexedDB

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** @arutemu64

## Context

The pages worth reading offline — the programme, the notification feed, the home
hero's festival config — fetched inside their `load` through a bespoke helper,
`fetchWithCache` (`$lib/utils/offlineCache.ts`). It wrote each response into
IndexedDB under a hand-chosen key and served the last copy back when the backend
was unreachable.

That worked, but everything around a cached read was ours to maintain and to
remember at each call site:

- **Keys were hand-written strings.** `'schedule'`, `'notifications'`,
  `'public-config-v2'` — the `-v2` suffix is the scar from a payload change that
  made older entries unreadable. Nothing tied a key to the operation it cached,
  so a renamed endpoint could not break the cache at compile time.
- **Freshness was per page.** The schedule page tracked document visibility and
  a `lastRefetch` timestamp by hand to re-fetch after a short background trip;
  no other page did, so each surface aged differently.
- **Every read blocked first paint.** A `load` that fetches delays the route
  commit, which is why the app shell grew bespoke per-section skeletons to cover
  the gap.
- **Deduplication did not exist.** The root layout warmed the schedule and the
  schedule page fetched it again on arrival — two requests for one payload,
  because neither knew about the other.

## Decision

We will use **TanStack Query** (`@tanstack/svelte-query` v6, the runes adapter)
as the cache for read surfaces, with query options generated from the same
OpenAPI spec as the SDK, and persist it to IndexedDB.

Concretely:

- The `@tanstack/svelte-query` plugin in `openapi-ts.config.ts` emits
  `<operation>Options()` / `<operation>QueryKey()` / `<operation>Mutation()` next
  to the SDK. Keys are derived from the operation, so a renamed endpoint is a
  compile error rather than a silently orphaned cache entry.
- The `QueryClient` is created by the **root layout component**, never a module
  singleton — it holds per-user data, and a module-level instance would outlive
  login/logout in this SPA (`AGENTS.md`).
- `PersistQueryClientProvider` writes the dehydrated cache into the app's
  existing IndexedDB database through a hand-rolled `idb-keyval` persister.
  Persistence is **opt-in per query**: only queries tagged by `persisted(…,
  scope)` are written, so an admin tool or a voting ballot cannot become
  readable offline just by having been fetched once.
- Queries pause and resume on **backend reachability**, not `navigator.onLine`:
  `onlineManager` is bound to our own health probe, so a captive portal or a
  dead VPN pauses the query and leaves the restored copy on screen instead of
  fetching into a black hole.
- **Identity stays out of it.** `/me` keeps its `load` and its own
  `fetchWithCache` entry, because it is the auth boundary the router is built on:
  `(protected)/+layout.ts` must resolve a user before it can guard, and a `load`
  cannot reach a `QueryClient` the component tree owns.

## Consequences

- One cache, one freshness policy. `staleTime` plus refetch-on-focus and
  refetch-on-reconnect replace the schedule page's hand-rolled visibility
  throttle, and every migrated surface now behaves the same way.
- Migrated pages render their own loading state, because their `load` no longer
  waits on the network. Each reuses the section skeleton the app shell used to
  show during navigation.
- A reachable failure is recoverable in place (a "Повторить" button on the
  query) instead of throwing a 503 into the full error page.
- The offline scopes did not change shape: `universal` survives logout,
  `user` is dropped on it — now by removing the tagged queries from the cache,
  which the persister mirrors into storage on its next write.
- Two persistence paths exist for now (the query cache, and identity's single
  entry). They share one IndexedDB database on purpose — concurrently opening
  two `idb-keyval` databases races in Firefox (idb-keyval#32).
- Entries written by the retired `fetchWithCache` keys are deleted once on boot
  (`dropRetiredCacheEntries`); that sweep can go once the installed base has
  turned over.
- New obligation: a change that makes old snapshots unreadable must bump
  `PERSISTED_CLIENT_BUSTER` in `persister.ts`. It is deliberately not the build
  hash — busting on every deploy would empty the offline cache of anyone who
  updates the PWA while away from the network.

## Alternatives considered

- **Keep `fetchWithCache`.** It works and it is small. But every capability
  above — dedup, shared freshness, background refetch, one storage format —
  would have been ours to write and to keep correct, and the hand-written keys
  stay untyped no matter how good the helper gets.
- **`experimental_createQueryPersister`** (per-query persistence, lazy restore).
  It maps more neatly onto per-key scoping and avoids restoring everything at
  boot, but it is still marked experimental and this app is deployed. The
  whole-client persister is the stable path, and our snapshot is small.
- **Migrate identity too**, moving the `(protected)` guard into a component.
  Rejected: it rewrites the auth boundary — 17 `await parent()` call sites and
  every redirect — to solve a problem the single cached `/me` entry does not
  have.
- **Persist to `localStorage`.** Synchronous, string-quota-bound, and the
  programme snapshot is the largest thing we store. IndexedDB is already open
  for the identity entry.
