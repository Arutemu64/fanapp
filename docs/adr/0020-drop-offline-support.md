# ADR-0020: Drop offline support

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** arutemu64

## Context

The app shipped an offline mode spread across every layer of the frontend: a
Workbox-precached shell with a navigation fallback and an image runtime cache
([ADR-0016](0016-workbox-precaching-via-vite-pwa.md)), an IndexedDB cache of API
reads (`fetchWithCache`, `warmCache`, per-user scoping and a write epoch), a
reachability probe with a confirm window and recovery poll, stale-data notices,
"доступно только онлайн" states on voting/feedback/tools, a write gate disabling
mutations, and a persisted offline-logout queue gating identity. Each page load
had to choose between cached, stale, missing and unreachable, and the e2e and
unit suites carried that matrix too.

The maintainer decided the app no longer offers an offline mode.

## Decision

We will run the frontend as a network-only PWA. The service worker stays, for
Web Push and the Badging API only: no `fetch` handler, no precache, no runtime
cache, and it calls `skipWaiting()` on install since there is nothing to keep
consistent across a page's requests. Loads read the API directly; a failure
that matters goes to the error page via `throwApiError`, and optional extras
fall back to showing nothing. The "new version" prompt moves from the waiting
service worker to SvelteKit's `updated` (version polling).

The client keeps the app installable: Chrome no longer requires a fetch handler
for installation ([Chrome blog](https://developer.chrome.com/blog/update-install-criteria),
[install criteria](https://web.dev/articles/install-criteria)).

## Consequences

- Removed: `@vite-pwa/sveltekit`, the `workbox-*` packages and `idb-keyval`, and
  the offline modules built on them.
- With no connection the app shows the error page (or, for a session already
  open, the SSE connection banner); nothing is readable offline, including the
  schedule at a venue with poor signal.
- A transient `/me` failure fails the root load instead of serving a cached
  identity.
- Devices that ran an offline build keep its Workbox caches and IndexedDB
  database (which holds per-user data) until site data is cleared or the
  browser evicts them. No cleanup code is shipped: nothing reads them, and they
  are expected to be gone by the next festival.
- Reintroducing a fetch handler or a client-side data cache needs a superseding
  ADR.

## Alternatives considered

- **Keep the precached shell, drop only the data cache.** Rejected: a cached
  shell with no data still boots into error states, and keeps the update
  handshake and precache configuration for little gain.
- **Unregister the service worker entirely.** Rejected: Web Push needs it.
