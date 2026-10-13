# ADR-0023: Workbox precache list from `vite-plugin-pwa` `injectManifest`

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Project maintainers

## Context

[ADR-0020](0020-workbox-precache-list-from-app-manifest.md) built the Workbox
precache list inside the worker from SvelteKit 3's `$app/manifest`, because
`@vite-pwa/sveltekit` did not support Kit 3. The frontend is now a plain Vue 3
SPA on Vite, so the reason for that choice is gone: there is no `$app/manifest`,
no `200.html` fallback, and no framework-owned build output to read. The only
build output left to list is what Vite writes to `build/`.

`vite-plugin-pwa` is framework-agnostic and has a first-class mode for a
hand-written worker: `strategies: 'injectManifest'` compiles the worker file
and replaces `self.__WB_MANIFEST` with the precache list it globs from the
output directory
([guide](https://vite-pwa-org.netlify.app/guide/inject-manifest.html),
[workbox-build `injectManifest`](https://developer.chrome.com/docs/workbox/modules/workbox-build#method-injectmanifest)).

## Decision

We will take the precache list from `vite-plugin-pwa`'s `injectManifest` and
delete the hand-built `buildPrecacheManifest`.

- The worker stays hand-written in `frontend/src/service-worker/service-worker.ts`
  and calls `precacheAndRoute(self.__WB_MANIFEST)`. It is compiled by the plugin
  (`srcDir`, `filename`, `rollupFormat: 'es'`) to `/service-worker.js` and still
  registered by our own wrapper with `type: 'module'` (`injectRegister: false`).
- The ADR-0020 filter rules move into `injectManifest.globPatterns` and
  `globIgnores` in `vite.config.ts`: JS, CSS and fonts under `assets/`, the PWA
  icons, and the root `svg/ico/html/json` files, minus `og-image.png` and the
  font subsets a Russian UI never renders.
- Revisions come from the plugin. Files under `assets/` are content-hashed by
  Vite, so the plugin's default `dontCacheBustURLsMatching` (`^assets`) leaves
  them keyed by URL alone; every other file gets an MD5 content revision, which
  is finer than ADR-0020's per-build `version` (an unchanged icon no longer
  re-downloads on each deploy). No `manifestTransforms` are needed.
- SPA navigations are served by `createHandlerBoundToURL('/index.html')`, the
  precached Vite shell, with the API path still denylisted.
- Kept from ADR-0020 and ADR-0016: the hand-written worker, the user-prompted
  update (`skipWaiting` message), push handlers, the cache-first runtime cache
  for responsive images (now the vite-imagetools output under `/assets`), and
  the network-only API bypass.
- The worker is its own TypeScript project (`src/service-worker/tsconfig.json`,
  `WebWorker` lib, no framework base config), checked by `tsc -p src/service-worker`.

## Consequences

- The list-building rules are plugin configuration again instead of code with
  tests, and the `precacheManifest` module and its test are gone.
- Dev and unit tests do not exercise the list: `self.__WB_MANIFEST` is only
  filled by a production build, and the worker stays inert under `vite dev`
  (`import.meta.env.DEV`).
- One more build dependency (`vite-plugin-pwa`, plus `workbox-build`), which
  tracks Vite majors; the cost ADR-0020 avoided, accepted now because the
  plugin no longer depends on a meta-framework adapter.
- Module service workers still need Firefox 147+, Chrome 91+ or Safari 15+;
  older browsers stay online-only, as before.

## Alternatives considered

- **Keep the hand-built list.** Rejected: with no `$app/manifest`, it would need
  its own walk of the output directory, which is exactly what the plugin's glob
  already does and maintains.
- **`strategies: 'generateSW'`.** Rejected for the reasons in ADR-0016: the push,
  update-prompt and image-cache logic is custom and clearer as a plain worker
  than as generated-config callbacks.
