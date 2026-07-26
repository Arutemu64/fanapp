---
name: fanfan-pwa
description: The FAN FAN service worker, web app manifest and offline layer. Use when editing frontend/src/service-worker.ts, frontend/static/manifest.json, the IndexedDB offline cache, the update prompt, or Web Push (VAPID, subscriptions, push payloads, app badge). Also use when a change touches offline behaviour, caching strategy, install/standalone behaviour or "the app shows stale data".
paths:
  - "frontend/src/service-worker.ts"
  - "frontend/static/manifest.json"
  - "frontend/src/lib/utils/offlineCache.ts"
  - "frontend/src/lib/components/UpdatePrompt.svelte"
---

# FAN FAN PWA

This app is a SvelteKit PWA. The service worker is hand-written against
SvelteKit's `$service-worker` module. **There is no Workbox here and none should
be introduced** — generic PWA advice about `workbox-*` packages, `generateSW` or
`workbox-config.js` does not apply.

## Where things live

| Concern | File |
| --- | --- |
| Service worker | `frontend/src/service-worker.ts` |
| Manifest | `frontend/static/manifest.json` |
| Offline data cache (IndexedDB) | `frontend/src/lib/utils/offlineCache.ts` |
| Update prompt | `frontend/src/lib/components/UpdatePrompt.svelte` |
| Push subscription UI | `frontend/src/routes/(app)/(protected)/profile/components/PushNotificationsCard.svelte` |
| VAPID keys | `secrets/*.pem` (gitignored, mounted read-only; `just backend-generate-vapid`) |

## Invariants

Each of these is load-bearing and already cost someone a debugging session. The
service worker documents the *why* inline — read the comment before changing the
line it sits above, and update it in the same edit.

1. **Two caching layers, split by ownership.** The service worker owns the *app
   shell* (`build` + `files` from `$service-worker`, plus `/`). The IndexedDB
   layer (`offlineCache.ts`, via `idb-keyval`) owns *API data*. Never move a
   responsibility across that line.

2. **API requests are never intercepted.** The backend is served from the same
   origin under `PUBLIC_API_URL` (e.g. `/api`), so an origin check cannot
   identify them — `isApiRequest()` prefix-matches the resolved base path
   instead. A cached API response would replay stale user data and make a
   health probe report the server reachable while the device is offline.

3. **Navigations are cache-first from the shell**, before the network. This is
   deliberate: the shell is immutable per deploy and versioned by `version`, so
   startup does not depend on the origin being healthy. A network-first
   navigation would hand the user a 502/503 gateway page instead of the app.

4. **The fetch handler is disabled in dev.** `dev` is derived as
   `build.length === 0` because `build` is only populated in production builds.
   Cache-first assumes an immutable versioned shell, which `vite dev` does not
   provide — leaving it on serves a stale shell across HMR and 404s deep links.
   The `push` / `notificationclick` handlers stay registered in dev.

5. **The origin check before serving precached assets is not redundant.**
   `ASSETS` holds bare pathnames, so without it a cross-origin GET whose path
   collides with a precached file (any host's `/robots.txt`) is answered with
   our copy.

6. **Updates never interrupt a session.** The new worker waits; `UpdatePrompt`
   asks the user, posts `skipWaiting`, and reloads on `controllerchange`. Do not
   call `skipWaiting()` unconditionally on install.

## Web Push

The backend sends `{ title, body, url, tag?, test? }` as JSON.

- `tag` is set to `notification.id`, collapsing re-pushes of the same
  notification while keeping distinct ones separate.
- **When a window is visible, the OS notification is suppressed** — the in-app
  toast and bell already cover it, and showing both double-alerts the user.
  `test: true` is the deliberate exception so the user can verify delivery from
  the profile screen without backgrounding the app.
- The payload carries no unread count, so the worker sets the count-less
  `setAppBadge()` flag; the in-app bell replaces it with the exact number.
- `notificationclick` reuses an open window (exact URL match first, then focus
  and navigate) rather than opening a duplicate tab.

## Manifest

`lang: "ru"`, `display: "standalone"`, `theme_color: "#d61450"` (primary-600 in
`.agents/context/DESIGN.md` — change both together). Icons ship `any` and
`maskable` at 192 and 512. **Shortcut names are user-facing, so they are
Russian** (`Программа`, `Уведомления`, `Карта`).

## Before calling it done

`just frontend-lint` and `just frontend-check`. Service worker changes need a
**production** check — `just run-prod`, not `just frontend-dev`, since the fetch
handler is inert in dev.
