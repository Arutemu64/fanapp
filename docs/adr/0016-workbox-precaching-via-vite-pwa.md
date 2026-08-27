# ADR-0016: Workbox precaching via vite-pwa for the service worker

- **Status:** Accepted
- **Date:** 2026-08-27
- **Deciders:** arutemu64

## Context

The service worker was hand-written from the SvelteKit `$service-worker`
template. It assembled its own precache list from `build`/`files`, opened a
`cache-${version}` cache on `install`, deleted superseded caches on `activate`,
and ran a bespoke `fetch` handler (cache-first shell, runtime image caching,
API bypass). That worked, but the precache assembly and cache-versioning were
boilerplate we maintained by hand: the `version`-keyed cache name, the manual
`cache.addAll`, the opportunistic `cache.put`, and the activate-time cleanup are
all mechanics [Workbox](https://developer.chrome.com/docs/workbox/) exists to
provide. A drifted `version` or a missed asset in the list is a silent offline
bug, and nothing enforced that the precache list matched the real build output.

An earlier note in [frontend.md](../frontend.md) said to keep the worker
hand-written and avoid `workbox-*`. This ADR supersedes that guidance for the
precaching layer specifically.

## Decision

We will generate the precache manifest and run precaching through **Workbox**,
wired by **`@vite-pwa/sveltekit`** in `injectManifest` mode. SvelteKit still
compiles `src/service-worker.ts` (so `$env/static/public` and the SW context
keep working); vite-pwa then injects the build manifest at `self.__WB_MANIFEST`
and emits the worker at the unchanged `/service-worker.js` path.

The worker uses `precacheAndRoute` + `cleanupOutdatedCaches` for the shell, a
`NavigationRoute` bound to the precached `200.html` fallback for SPA
navigations, and a `CacheFirst` runtime route (bounded by an `ExpirationPlugin`)
for the content-hashed responsive image variants (kept out of the precache via
`globIgnores`). We keep everything
that carried real product logic: the manual registration wrapper (its `.catch`
suppresses benign Sentry noise), the user-prompted update flow (`clientsClaim`
without `skipWaiting`; the waiting worker activates only on the prompt's
`skipWaiting` message), the same-origin API bypass, and the push /
notificationclick handlers. Caching setup is gated on the manifest's presence,
so the worker stays inert in `vite dev` exactly as before.

## Consequences

- Precache assembly, cache naming, and old-cache cleanup are now Workbox's job;
  the manifest is derived from the real build, so it can't silently drift.
- New dependencies: `@vite-pwa/sveltekit`, `workbox-precaching`,
  `workbox-routing`, `workbox-strategies`, `workbox-core`. The core plugin
  tracks Vite (Vite 8 supported) and precaching is Google-maintained.
- The worker still can't be exercised by `just frontend-dev` (inert in dev);
  verify SW changes against a production build (`just run-prod`, or serving
  `build/` and driving it headless).
- Generic Workbox `generateSW` guidance still does **not** apply — we use
  `injectManifest` and keep our own handlers. Reverting to a fully hand-written
  worker now needs a superseding ADR.

## Alternatives considered

- **Keep the worker fully hand-written.** Rejected: it left precache assembly
  and cache versioning as hand-maintained boilerplate with no guard against
  drift, for no offsetting benefit.
- **`generateSW` (fully generated worker).** Rejected: it can't host the push,
  update-handshake, and API-bypass logic without `injectManifest`-style custom
  code anyway, and it would replace the deliberate user-prompted update flow
  with its own.
