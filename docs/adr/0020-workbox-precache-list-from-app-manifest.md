# ADR-0020: Workbox precache list from `$app/manifest`, without vite-pwa

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Project maintainers

## Context

[ADR-0016](0016-workbox-precaching-via-vite-pwa.md) put precaching on Workbox
and had `@vite-pwa/sveltekit` (`injectManifest`) build the precache list and
inject it at `self.__WB_MANIFEST`. Moving to SvelteKit 3 breaks that wiring:

- `@vite-pwa/sveltekit` 1.1.0 peers on `@sveltejs/kit` ^1 || ^2. Under Kit 3 it
  hooks the wrong build phase (Kit 3 builds each Vite environment from its own
  `buildApp` hook), so the build either fails or ships a worker whose
  `__WB_MANIFEST` is undefined. Support exists only as an open, unreviewed
  community PR ([vite-pwa/sveltekit#111](https://github.com/vite-pwa/sveltekit/pull/111))
  that would ship as a 2.0 needing `vite-plugin-pwa` 2.
- Kit 3 removed `$service-worker` and exposes the build output to the worker
  through `$app/manifest` (`immutable`, `assets`) and `version` through
  `$app/env` ([service workers](https://svelte.dev/docs/kit/service-workers)).
  That is the list the plugin used to derive by globbing the output directory.

## Decision

We will build the Workbox precache list inside the worker from `$app/manifest`
and drop `@vite-pwa/sveltekit`. Workbox stays: `workbox-precaching`,
`workbox-routing`, `workbox-strategies`, `workbox-expiration` and
`workbox-core` remain direct dependencies, used exactly as ADR-0016 describes.

- `buildPrecacheManifest` (`frontend/src/lib/utils/precacheManifest.ts`, pure and
  unit-tested) filters `immutable` and `assets` with the rules that were
  `globPatterns`/`globIgnores`, and adds the adapter-static `200.html` fallback.
  Hashed files get `revision: null`; `static/` files and `200.html` are
  revisioned with the build `version`.
- The worker moves to `src/service-worker/index.ts` with its own `tsconfig.json`
  extending `$app/tsconfig/service-worker`, as Kit 3 requires, and is registered
  with `type: 'module'`, which is what Kit 3 emits and registers.
- Everything else in ADR-0016 holds: the manual registration wrapper, the
  user-prompted update, the API bypass, the image runtime cache, push.

## Consequences

- One build plugin less, and no wait on a third-party release for each Kit or
  Vite major. The precache list comes from the framework's own manifest rather
  than a directory glob.
- The filter rules are now ours to maintain, in code with tests rather than in
  plugin config.
- `static/` files and `200.html` re-download on every deploy, since `version`
  changes per build where the plugin hashed each file's content. That is about
  ten small files.
- Module service workers need Firefox 147+, Chrome 91+ or Safari 15+
  ([MDN compat data](https://github.com/mdn/browser-compat-data/blob/main/api/ServiceWorker.json)).
  Older browsers reject the registration and stay online-only, the same
  degradation the wrapper already handles for storage-partitioned browsers.

## Alternatives considered

- **Wait for `@vite-pwa/sveltekit` 2.** Rejected: it would block the SvelteKit 3
  upgrade on an unreviewed PR, and it would pull in a `vite-plugin-pwa` major
  that only provides the list `$app/manifest` already gives us.
- **Drop Workbox and hand-write the cache handling again.** Rejected for the
  reasons in ADR-0016. Only the list's source changed. The precaching logic
  that list feeds did not.
- **Stay on SvelteKit 2.** Rejected: Kit 3 deprecates `$env/*` and replaces
  `$lib`, so staying would only defer the same migration and keep the app on
  APIs Kit 4 removes.
