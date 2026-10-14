# Plan: migrate the frontend from SvelteKit (Svelte 5) to Vue 3

- **Status:** Draft, for discussion. Nothing here is decided until an ADR records it.
- **Scope:** `frontend/` only. The backend, the OpenAPI spec and the NGINX
  static-hosting topology ([ADR-0007](../../adr/0007-client-rendered-spa-frontend.md)) stay.

## Inventory (what has to move)

| Area | Today | Size |
| --- | --- | --- |
| Components | `.svelte` (runes) | 209 files, ~14.9k lines |
| Rune modules | `src/lib/services/*.svelte.ts` (events/SSE, pwa, push, theme, toasts, captcha, cooldown, persisted) | 8 |
| Route loads | `+page.ts` / `+layout.ts` (guards, prefetch, navbar title/actions) | ~680 lines |
| UI kit | shadcn-svelte on bits-ui (24 primitives in `lib/components/ui`) | 52 files import bits-ui |
| Kit APIs | `$app/paths` (27), `$app/state` (11), `$app/types` (8), `$app/navigation` (6), `$app/env` (2), `$app/manifest` (1) | |
| Server state | `@tanstack/svelte-query` 6 + persist to IndexedDB, hey-api generated options | |
| PWA | Hand-written Workbox worker, precache list from `$app/manifest` ([ADR-0020](../../adr/0020-workbox-precache-list-from-app-manifest.md)) | |
| Images | `@sveltejs/enhanced-img` (hero LCP image, map tiles in `lib/data/maps.ts`) | |
| Other | Sentry (`@sentry/sveltekit`), svelte-sonner, `@lucide/svelte`, unplugin-icons, photoswipe, dicebear, `@khmyznikov/pwa-install` | |

Framework-agnostic already, and carried over unchanged: `src/lib/utils/*`,
`src/lib/api/*` (bar the regenerated TanStack file), `reachability.ts`,
`session.ts`, Tailwind v4 + `app.css` tokens, the Vitest unit tests on pure
logic, and — the most valuable asset — the **Playwright E2E suite**, which
drives a production build through the DOM and is therefore the acceptance
contract for the rewrite.

## Target stack

Versions are the npm `latest` tags on 2026-10-14 (`npm view`).

| Concern | SvelteKit today | Vue target | Notes |
| --- | --- | --- | --- |
| Framework | svelte 5.57 | **vue 3.5.44**, `<script setup lang="ts">`, Composition API | 3.6 (Vapor) is still `rc`; don't start on it. |
| Build | `@sveltejs/kit` + adapter-static | **vite 8** + `@vitejs/plugin-vue` 6.0 | Plain Vite SPA; `vite build` emits `index.html`; NGINX `try_files … /index.html` replaces `200.html`. |
| Routing | filesystem routes + `load` | **vue-router 5.4** with built-in file-based routing (`vue-router/vite`, `vue-router/auto-routes`) | v5 merged unplugin-vue-router into core ([migration guide](https://router.vuejs.org/guide/migration/v4-to-v5)). Its data loaders live under `vue-router/experimental` — **don't adopt**; keep TanStack + guards. |
| Client state | `.svelte.ts` rune classes + `createContext` | **pinia 4.1** for app-wide state (session, theme, pwa, push), plain composables for local logic | See "State" below. |
| Server state | `@tanstack/svelte-query` 6 | **`@tanstack/vue-query` 5.104** + `@tanstack/query-async-storage-persister` + `idb-keyval` | Persist via `VueQueryPlugin`'s `clientPersister` / `@tanstack/query-persist-client-core` ([Vue persister docs](https://tanstack.com/query/latest/docs/framework/vue/plugins/createPersister)). ADR-0021/0022 policies carry over verbatim. |
| API client | hey-api `@tanstack/svelte-query` plugin | hey-api **`@tanstack/vue-query`** plugin ([docs](https://heyapi.dev/openapi-ts/plugins/tanstack-query)) | Regenerate; option factories keep their names. |
| Utilities | `useInterval`, `listen`, `documentVisibility`, `minuteClock`, `keyboardInset` | **@vueuse/core 15** (`useIntervalFn`, `useEventListener`, `useDocumentVisibility`, `useNow`, `useMediaQuery`, `useStorage`, `useOnline`) | Delete our helpers where VueUse covers them 1:1; keep tested domain logic. |
| PWA | Workbox by hand + `$app/manifest` | **vite-plugin-pwa 2.0**, `strategies: 'injectManifest'` | Back to the plugin ADR-0020 had to drop for Kit 3 — it peers on Vite 8. Keep `src/service-worker/index.ts`; swap the hand-built list for `self.__WB_MANIFEST` ([injectManifest guide](https://vite-pwa-org.netlify.app/guide/inject-manifest.html)). |
| Images | `@sveltejs/enhanced-img` | **vite-imagetools 12** (`?w=…&format=avif;webp&as=picture`) + a small `<ResponsivePicture>` component | See "Images" below. |
| UI kit | shadcn-svelte / bits-ui | **shadcn-vue 2.8** on **reka-ui 2.11** | Same shadcn design language and Tailwind v4 classes; re-add each of the 24 primitives with the CLI, then re-apply our local overrides. |
| Toasts | svelte-sonner | **vue-sonner 2** | |
| Icons | `@lucide/svelte`, unplugin-icons (`compiler: 'svelte'`) | **`@lucide/vue`**, unplugin-icons `compiler: 'vue3'` | |
| Errors | `@sentry/sveltekit` | **`@sentry/vue`** with `browserTracingIntegration({ router })` + `@sentry/vite-plugin` for source maps | Keep the 5xx filter from `hooks.client.ts`. |
| Typecheck / lint | svelte-check, eslint-plugin-svelte, prettier-plugin-svelte | **vue-tsc 3.3**, **eslint-plugin-vue 10**, Prettier (formats `.vue` natively) | knip has a Vue plugin. |
| Unchanged | photoswipe, dicebear, pwa-install web component, Tailwind v4, Vitest, Playwright | | `pwa-install` needs `compilerOptions.isCustomElement`. |

## Concept mapping

| SvelteKit / Svelte | Vue |
| --- | --- |
| `$state` | `shallowRef` (primitives), `ref`/`reactive` (objects) |
| `$derived` | `computed` |
| `$effect` | `watch` / `watchEffect` with `onCleanup` |
| `$props` / `$bindable` | `defineProps<T>()` / `defineModel()` |
| callback props (`onsave`) | `defineEmits<T>()` |
| snippets / `{@render}` | slots |
| `createContext` | `provide`/`inject` with `InjectionKey`, or a Pinia store |
| `+layout.svelte` | parent route component with `<RouterView>` |
| `+page.ts` `load` | route `meta` via `definePage()` + `beforeEnter` / `router.beforeResolve` |
| `parent()` → `queryClient` | `useQueryClient()`; the client is created once in `main.ts` |
| `error(503)` / `redirect(303)` in a load | guard returns `{ name: 'login', query }` or routes to an error view |
| `+error.svelte` | an `ErrorView` route + `router.onError` |
| `$app/state` `page` | `useRoute()` |
| `goto`, `beforeNavigate`, `afterNavigate` | `router.push`, `onBeforeRouteLeave`, `router.afterEach` |
| hover/tap preloading of loads | `pointerenter`/`touchstart` → `queryClient.prefetchQuery` in a `PrefetchLink` wrapper |
| `$app/paths` `resolve` | named routes (`{ name: … }`), typed by the generated route map |
| `$app/env` `version` | `define: { __APP_BUILD__ }` (already exists) |
| `$app/env/public` `PUBLIC_*` | `import.meta.env.VITE_*` — **renames env vars**: update `.env.example` in the same change (AGENTS.md "Never"). |

## Key design calls

**State.** Every rune module becomes either a Pinia store (app-wide: `session`,
`theme`, `pwa`, `pushDevice`, `toasts`, `events`) or a composable (`useCooldown`,
`useCaptcha`, `usePersisted` → VueUse `useStorage`). Pinia stores live on the app
instance, not the module, so the "no request/user state in a module singleton"
rule holds — but logout must still `$reset()` the user-scoped stores alongside
`queryClient.clear()`.

**Guards replace loads.** The root load's job — create the `QueryClient`,
restore the IndexedDB cache, settle `/me`, probe reachability — moves to
`main.ts` before `app.mount()`, so every guard sees a settled identity. The
`(protected)` layout load becomes a `beforeEnter` on the protected parent
route with identical branching (offline → 503 view, guest → `/login?next=`).
Navbar `title`/`actions` move to route `meta`. Keep every existing *why*
comment, moved next to the code it explains.

**Images.** `enhanced-img` is a Svelte wrapper over imagetools (inference: its
generated `Picture` shape matches imagetools' `as=picture`), so the build-time
behaviour is reproducible:
- Map tiles (`lib/data/maps.ts`): `import.meta.glob('…/*.webp', { query: { w: '…', format: 'avif;webp', as: 'picture' }, eager: true })`.
- Hero LCP image: an explicit width ladder in the query, since we lose
  enhanced-img's `sizes`-driven ladder (see the comment in `HeroCard.svelte`).
  Keep `loading="eager"` + `fetchpriority="high"` and re-measure LCP.
- `<ResponsivePicture>` renders `<picture>` / `<source>` / `<img>` with
  explicit `width`/`height` to keep CLS at zero.
- Precache rule unchanged: raster variants stay out of `globPatterns`
  and are served cache-first at runtime, as `precacheManifest.ts` decides today.

**PWA.** Port `buildPrecacheManifest`'s filters into `injectManifest.globPatterns`
/ `globIgnores` (shell files, PWA icons, minus unused font subsets) and keep its
unit test against a `manifestTransforms` function. Keep manual registration with a
`.catch()` (the Sentry "Rejected" noise) via `virtual:pwa-register` with
`injectRegister: false`, or keep `serviceWorker.ts` as is. A new ADR supersedes
ADR-0020.

## Strategy: rewrite in place, gated by E2E

A mixed Svelte+Vue app would need two routers sharing one URL space — more
work than it saves. Instead:

1. **Phase 0 — de-Svelte the logic (on `main`, shippable).** Move logic out of
   `.svelte.ts` into plain TS (pure functions + a thin reactive shell), so it
   ports without rewriting. Pure gains on the current app too.
2. **Phase 1 — skeleton (long-lived branch).** Vite + Vue + Router 5 + Pinia +
   Vue Query + persister + Sentry + Tailwind tokens + shadcn-vue primitives +
   vite-plugin-pwa. Port `+layout.ts` boot into `main.ts`. Regenerate the
   hey-api client. Swap the lint/check gates (see "Tooling").
3. **Phase 2 — screens, in E2E-spec order.** Shell (navbar, bottom nav,
   sidebar, connection banner, update prompt) → login → home → schedule (most
   logic: subscriptions, staff actions, modals) → notifications + SSE → profile
   & settings → map (photoswipe + images) → voting → staff tools. Each screen
   lands when its Playwright specs are green; the specs themselves change only
   where they reach into Svelte-specific markup.
4. **Phase 3 — parity pass.** Full E2E incl. iOS-Safari project, axe checks,
   Lighthouse LCP/CLS/INP vs the Svelte build, offline cold start, push,
   deploy with the PWA update path (old Svelte worker → new Vue worker must
   take over cleanly: test an upgrade from a cached install).
5. **Phase 4 — cut over.** Merge, `just readme-gallery`, delete Svelte deps.

## Tooling, docs and agent setup to update in the same change

- `justfile`: `frontend-check` → `vue-tsc --noEmit` (+ the service-worker tsconfig).
- `eslint.config.js`, `.prettierrc`, `knip` config, `vitest` config (drop the
  SvelteKit plugin; component tests stay out of scope per ADR-0011).
- `.claude/hooks/post-edit-check.py`: the Russian-copy markup scan targets `.vue`.
- `.claude/agents/svelte-editor.md` → `vue-editor`; AGENTS.md "Load before you
  edit" table: Svelte skills → `vue-best-practices` (pinned in `skills-lock.json`),
  `shadcn-svelte` → a shadcn-vue equivalent.
- `docs/frontend.md` rewrite; `docs/dependencies.md` + `renovate.jsonc`; the
  frontend `Dockerfile` (output dir `dist/`) and NGINX fallback file name.
- ADRs: one for "Vue 3 replaces Svelte" (supersedes the framework parts of
  ADR-0007), one superseding ADR-0020 (vite-plugin-pwa returns). ADR-0019,
  -0021, -0022, -0023 stand unchanged.

## Risks

- **Effort.** ~15k lines of components is a near-full rewrite; most time goes
  into the 209 components and the 24 UI primitives' local overrides.
- **Offline regressions.** The boot ordering (restore → `/me` → probe) and the
  persister's dehydrate filter are subtle; port them with their comments and
  cover them with the offline E2E specs before anything else.
- **Lost Svelte niceties.** Hover preloading and `sizes`-driven image ladders
  need hand-rolled replacements.
- **Version churn.** Vue 3.6/Vapor and Vue Router 6 (ESM-only) are on the
  horizon; Router 5 is described upstream as a transition release.

## Open questions

1. Is the motivation (hiring, ecosystem, a library only Vue has) strong enough
   to pay for a full rewrite? This plan doesn't argue that; an ADR should.
2. File-based routing vs a hand-written route table? File-based keeps the
   current mental model; a table is more explicit for ~30 routes.
3. Pinia for everything app-wide, or provide/inject composables and no Pinia?
