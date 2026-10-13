# Plan: migrate the frontend from SvelteKit (Svelte 5) to Vue 3

- **Status:** Proposed — nothing here is decided until the ADRs in [§9](#9-adrs-and-docs) are accepted
- **Date:** 2026-10-13
- **Target stack:** Vue 3 (`<script setup lang="ts">`, Composition API), Vue Router, Pinia, VueUse, TanStack Query (`@tanstack/vue-query`), `vite-plugin-pwa`, shadcn-vue

## 1. Goal and non-goals

Replace the SvelteKit SPA in `frontend/` with a Vue 3 SPA that behaves the same for users: same URLs, same Russian copy, same offline allowlist, same service-worker update flow, same push. The Playwright suite is the contract: if it passes against the Vue build, we have parity.

Not in scope: redesigning screens, changing API contracts, changing the backend, adding SSR. The SPA decision in [ADR-0007](../../adr/0007-client-rendered-spa-frontend.md) stays (static bundle behind NGINX, build-time `PUBLIC_*`, client guards for UX only). Only the framework changes.

## 2. What we are moving

Measured on `main` at `4a4955a`:

| Area                                                                         | Size                           | Migration cost                                                            |
| ---------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------- |
| App components and pages (`routes/**`, `lib/components/*.svelte`)            | ~93 files, ~11k lines          | **High.** Hand port, one screen at a time                                 |
| shadcn-svelte components (`lib/components/ui/`, 26 components)               | 110 files                      | **Low–medium.** Regenerate with shadcn-vue, then re-apply our local edits |
| Rune services (`lib/services/*.svelte.ts`)                                   | 7 files                        | **Medium.** These become composables or Pinia stores                      |
| `createSubscriber` sources (reachability, minute clock, document visibility) | 3 files                        | **Low.** VueUse covers them                                               |
| Universal loads (`+page.ts`, `+layout.ts`)                                   | 34 files                       | **Medium.** Guards, navbar meta and prefetch, split three ways (§4.1)     |
| Pure TS (`lib/utils`, `lib/api`, `lib/constants`, `lib/data`, `lib/types`)   | ~40 files + 24 unit tests      | **Near zero.** Copy over and swap the few `$app/*` imports                |
| Service worker (`src/service-worker/`)                                       | 1 file + `precacheManifest.ts` | **Medium.** Moves back onto `vite-plugin-pwa` `injectManifest` (§4.6)     |
| Playwright E2E (16 specs + gallery)                                          | framework-agnostic             | **Low.** Selectors are role/text based. Only build/serve wiring changes   |

Framework APIs in use that need a mapping: `$state` ×124, `$derived` ×199, `$bindable` ×134 (mostly `ui/`), `$effect` ×21, `<svelte:head>` ×27 (titles only), `{@attach}` ×5, `goto` ×12, `onNavigate`/`beforeNavigate`/`afterNavigate` ×10, `page.data` ×8, `createContext` ×4.

## 3. Stack mapping

Versions from the npm registry on 2026-10-13. Pin exact versions at the start of Phase 0 and add them to `renovate.jsonc`.

| Today                                                          | Vue replacement                                                                                                                                                                            | Note                                                                                                                                                                                                                                                             |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `svelte` 5.57, `@sveltejs/kit` 3, `adapter-static`             | `vue` 3.5.x + plain Vite 8 SPA (`@vitejs/plugin-vue` 6, peers Vite ^8)                                                                                                                     | `index.html` replaces `app.html`. The SPA fallback is `index.html` instead of `200.html`                                                                                                                                                                         |
| SvelteKit file router + loads                                  | `vue-router` 5.x with built-in file-based routing (`vue-router/vite`, placed **before** `Vue()` in `plugins`)                                                                              | Vue Router 5 merged unplugin-vue-router into core with no breaking changes for v4 users ([InfoQ](https://infoq.com/news/2026/03/vue-router-5), [docs](https://router.vuejs.org/file-based-routing/)). Data loaders are experimental, so we don't use them (§4.1) |
| `createContext` services, module `$state`                      | `pinia` 4.x setup stores + `provide`/`inject` with `InjectionKey`                                                                                                                          | Pinia 4 is ESM-only and requires `@vue/devtools-api` alongside it ([release notes](https://newreleases.io/project/npm/pinia/release/4.0.0))                                                                                                                      |
| `createSubscriber`, `svelte/reactivity`, hand-rolled listeners | `@vueuse/core` 15.x (peers `vue ^3.5`)                                                                                                                                                     | `useDocumentVisibility`, `useEventListener`, `useIntervalFn`, `createSharedComposable`, `useTitle`                                                                                                                                                               |
| `@tanstack/svelte-query` 6 + `svelte-query-persist-client`     | `@tanstack/vue-query` 5.104 + `@tanstack/query-async-storage-persister`                                                                                                                    | `VueQueryPlugin` takes a `clientPersister` that restores before mount and sets `queryClient.isRestoring` (checked in the package's typings). The QueryClient defaults move over unchanged                                                                        |
| hey-api `@tanstack/svelte-query` plugin                        | hey-api `@tanstack/vue-query` plugin                                                                                                                                                       | Same generated names (`…Options`, `…QueryKey`, `…Mutation`, `…InfiniteOptions`). Options with reactive params must be wrapped in `computed`/a getter, or the query runs once ([hey-api docs](https://heyapi.dev/openapi-ts/plugins/tanstack-query))              |
| hand-built precache list from `$app/manifest`                  | `vite-plugin-pwa` 2.0 `strategies: 'injectManifest'`                                                                                                                                       | Peers Vite ^8 and needs Node ≥ 20.19 ([README](https://github.com/vite-pwa/vite-plugin-pwa/blob/main/README.md)). We pin Node 24.21                                                                                                                              |
| `bits-ui` + shadcn-svelte                                      | `reka-ui` 2.x + shadcn-vue 2.x                                                                                                                                                             | Every component we use exists in shadcn-vue, including Empty, Field, Item, Input Group, Spinner, Input OTP, Sonner ([list](https://www.shadcn-vue.com/docs/components))                                                                                          |
| `svelte-sonner`                                                | `vue-sonner`                                                                                                                                                                               | What shadcn-vue's Sonner wraps                                                                                                                                                                                                                                   |
| `@lucide/svelte`                                               | `@lucide/vue`                                                                                                                                                                              | `NavbarAction.icon` becomes a Vue `Component`                                                                                                                                                                                                                    |
| `unplugin-icons` (`compiler: 'svelte'`)                        | same plugin, `compiler: 'vue3'`                                                                                                                                                            |                                                                                                                                                                                                                                                                  |
| `@sveltejs/enhanced-img`                                       | `vite-imagetools` 12 + a small `ResponsivePicture.vue`                                                                                                                                     | enhanced-img is built on imagetools. We keep AVIF/WebP + widths for the hero and maps                                                                                                                                                                            |
| `@sentry/sveltekit`                                            | `@sentry/vue` + `@sentry/vite-plugin`                                                                                                                                                      | `Sentry.init({ app, integrations: [browserTracingIntegration({ router })] })` ([docs](https://docs.sentry.io/platforms/javascript/guides/vue/))                                                                                                                  |
| `svelte-check`                                                 | `vue-tsc` 3.x                                                                                                                                                                              | `pnpm check` = `vue-tsc --build` + the SW tsconfig                                                                                                                                                                                                               |
| `eslint-plugin-svelte`, `prettier-plugin-svelte`               | `eslint-plugin-vue` 10 + `@vue/eslint-config-typescript`; Prettier formats `.vue` natively                                                                                                 | Keep `perfectionist` and `prettier-plugin-tailwindcss`                                                                                                                                                                                                           |
| Unchanged                                                      | Tailwind v4 (`@tailwindcss/vite`), `tw-animate-css`, `tailwind-merge`, Workbox runtime packages, `idb-keyval`, `photoswipe`, `@khmyznikov/pwa-install`, fonts, Vitest, Playwright, hey-api |                                                                                                                                                                                                                                                                  |

## 4. Architecture mapping

### 4.1 Routing, loads and guards

SvelteKit loads do four jobs here. Each gets its own home in Vue:

1. **Guards** go to one `router.beforeEach` in `src/router/guards.ts`, driven by route `meta` (`requiresAuth`, `guestOnly`, `offlineRedirect`) set with `definePage()` in the group layouts. The guard reads identity synchronously with `queryClient.getQueryData(currentUserOptions().queryKey)`, as the loads do today. Redirects stay redirects: `/login?next=…` through `sanitizeNextPath`, guests-only `(auth)`, and tools-offline → `/tools`.
2. **Error outcomes** (`error(403)` for tools, `error(503)` for protected-while-offline) no longer throw. The group layout component (`(protected).vue`, `tools.vue`) computes the condition from the live user query and reachability and renders `ErrorState` in place of `<RouterView>`. The URL stays put, as SvelteKit does today, and the screen reacts when the user or reachability changes without a re-navigation. The `isServerSideHttpError` Sentry filter in `hooks.client.ts` has nothing left to filter, so it is dropped.
3. **Navbar data** (`title`, `back`, `actions`). Static parts go to `definePage({ meta: { title, back } })`. Actions that depend on permissions (schedule → "Изменения программы") go to a `useNavbarActions()` call in the page, which writes into a small navbar store the `AppNavbar` reads. Titles: one `router.afterEach` sets `document.title` from `meta.title`, which replaces all 27 `<svelte:head>` blocks.
4. **Prefetch.** Today a load calls `queryClient.query(...)` when SvelteKit preloads the route on hover/tap. Vue Router has no hover preload. Add `meta.prefetch(queryClient)` per route, called from a global `beforeResolve` (navigation start). If the hover head start turns out to matter, add a `PrefetchLink` wrapper that calls the same hook on `pointerenter`/`touchstart`.

**Boot order.** Guards must not run before identity is settled. `main.ts` creates the QueryClient, restores the persisted cache and runs the `/me` settle (the current root-load logic, moved verbatim into `src/app/bootQueryClient.ts`) **before** `app.use(router)`. The router's first navigation then sees a settled cache. We restore explicitly with `persistQueryClientRestore` + `persistQueryClientSubscribe` instead of `VueQueryPlugin`'s `clientPersister`, because the guards need the result and not only the components. The QueryClient stays document-scoped (main.ts closure, installed with `VueQueryPlugin({ queryClient })`) and is never a module export.

**Navigation transitions.** `onNavigate` + `navTransition.ts` → `router.beforeResolve` that starts `document.startViewTransition` and resolves it in `afterEach`. `navTransition.ts` stays pure and tested.

**Spike gate (Phase 0):** confirm that file-based routing gives us layouts for parenthesised groups (`(app)`, `(protected)`, `(auth)`). Docs confirm that groups don't add URL segments; we did not find docs for a layout file per group. Fallback: a hand-written `src/router/routes.ts` with nested layout routes. That is about 25 routes and loses only typed route names.

### 4.2 Component structure (vue-best-practices)

```text
frontend/src/
├── main.ts                 # createApp, Pinia, VueQueryPlugin, Sentry, bootQueryClient → router → mount
├── App.vue                 # thin: <RouterView>, <Toaster>, <pwa-install>, <UpdatePrompt>
├── pages/                  # file routes; each page is a composition surface only
│   ├── (app).vue           # shell: sidebar, navbar, bottom nav, SSE→cache wiring
│   ├── (app)/(protected).vue, (app)/schedule/index.vue, …
│   └── (auth)/login.vue
├── components/
│   ├── ui/                 # shadcn-vue (vendored)
│   ├── shared/             # EmptyState, ErrorState, StaleDataNotice, … (today's lib/components)
│   └── <feature>/          # schedule/, voting/, profile/, notifications/, tools/, login/, home/
├── composables/            # use<Feature>.ts: today's rune services and createSubscriber sources
├── stores/                 # Pinia setup stores (client state only)
├── router/                 # guards.ts, navigation transitions
├── api/ utils/ constants/ data/ types/   # pure TS, copied from lib/
└── service-worker/
```

The feature components under `routes/**/components/` move to `components/<feature>/` one to one. Their boundaries already follow the project's split rules, so the port does not re-split them. The `#lib/*` import alias stays, pointing at `src/`, to keep diffs of the copied pure modules minimal.

Conventions every ported file follows (from the `vue-best-practices` skill, to be restated in the new `docs/frontend.md` only where it's FAN FAN–specific):

- `<script setup lang="ts">`, sections in order script → template → style. Typed `defineProps<…>()` / `defineEmits<…>()`.
- `$state` primitive → `shallowRef`; object state → `ref` (replaced wholesale) or `reactive` (mutated in place). Never destructure `reactive` or props without `toRefs`.
- `$derived` → `computed`, kept pure. No filtering or sorting inline in templates.
- `$effect` → `watch` with `immediate`/`onCleanup` for side effects. Audit all 21: most become `watch` on a query result, and `Sentry.setUser` becomes a `watch` on the user query.
- `$bindable` → `defineModel`. `{@attach}` → `useTemplateRef` + `onMounted` (or a directive for the captcha mount). `<pwa-install>` is declared in `compilerOptions.isCustomElement`.
- Queries: `useQuery(() => ({ ...getScheduleOptions() }))` / `useMutation(...)`. Reactive params go through a getter or `computed`, never a plain object.

### 4.3 State: what goes where

| Today                                                                | Vue                                                                                                               | Why                                                                                                                                                                        |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Server data (TanStack cache)                                         | stays in TanStack Query                                                                                           | ADR-0021/0022 stand; only the adapter changes                                                                                                                              |
| `Session` (`createContext`)                                          | Pinia setup store `useSessionStore`, injecting the QueryClient, EventsClient and router                           | It is app-wide orchestration with no user data of its own (identity lives in the query cache). `SessionRouter` injection stays, so `session.test.ts` keeps running in Node |
| `EventsClient` (`createContext`, class)                              | stays a class; `app.provide(eventsKey, client)` + `useEvents()` with `InjectionKey`                               | It owns sockets and timers. A class with `destroy()` is clearer than a store                                                                                               |
| `ThemeService`, `PwaService`, `ToastService`                         | Pinia setup stores                                                                                                | Device-scoped client state, the store use case Pinia exists for                                                                                                            |
| reachability, minute clock, document visibility (`createSubscriber`) | `createSharedComposable` over VueUse primitives; reachability keeps its module-level probe, which is device state | Same "one reachability answer" contract                                                                                                                                    |
| `persisted.svelte.ts`, `cooldown.svelte.ts`                          | `usePersisted` (on `safeStorage`, not `useStorage`, to keep the throw-safe wrapper) and `useCooldown`             |                                                                                                                                                                            |

**State-isolation rule (AGENTS.md "Never").** A Pinia store lives as long as the app, which is exactly the module-singleton hazard the rule targets. So any store that ever holds user-scoped data must be reset in the Session's logout/expiry cleanup, next to the query purge. Stores that hold only device state (theme, PWA install, reachability) are exempt. Write this into the new `docs/frontend.md` §1.

### 4.4 Env and build constants

- `$app/env/public` → `import.meta.env.PUBLIC_*` with `envPrefix: 'PUBLIC_'` and `envDir` at the repo root. Never widen the prefix: `SENTRY_AUTH_TOKEN` must stay unreachable (`docs/frontend.md` §1).
- `src/env.ts` currently makes the build fail on a declared-but-missing var. Keep that guarantee with a ~15-line Vite plugin in `vite.config.ts` that checks the same list, and type the list in `src/env.d.ts` (`ImportMetaEnv`). The "register a `PUBLIC_*` var in six places" checklist stays valid.
- `%sveltekit.env.PUBLIC_SITE_URL%` in `app.html` → `%PUBLIC_SITE_URL%` in `index.html` (Vite's HTML env replacement, prefixed vars only).
- `version` from `$app/env` (the persister `buster`, the SW revision) → the existing `__APP_BUILD__` define, with a build-timestamp fallback when `APP_BUILD` is empty. Precache revisions come from vite-plugin-pwa's content hashes.

### 4.5 Errors, Sentry and chunk recovery

- `hooks.client.ts` → `src/app/sentry.ts`, called from `main.ts` with `app` and `router`. Keep `beforeSend` (the stale-chunk filter) and the "no `release` key" rule. Source-map upload moves to `@sentry/vite-plugin` with the same four-var all-or-nothing gate.
- `vite:preloadError` recovery stays as is. Add `router.onError` for lazy route chunks, sharing the same `sessionStorage`-guarded reload.
- `+error.svelte` → a catch-all `[...path].vue` (404) plus `app.config.errorHandler`-driven fullscreen `ErrorState`.

### 4.6 PWA and service worker

- `vite-plugin-pwa` with `strategies: 'injectManifest'`, `injectRegister: false` (keep `registerServiceWorker` and its `.catch`), `manifest: false` (keep `public/manifest.json` as authored), and `injectManifest.globIgnores` reproducing `buildPrecacheManifest`'s rules (no raster images except the PWA icons; responsive variants stay runtime-cached). `buildPrecacheManifest` and its test are deleted, and their rules move to config. ADR-0016's reasons for `injectManifest` over `generateSW` still hold.
- Navigation fallback: `createHandlerBoundToURL('index.html')`. `nginx.conf`: `try_files … /index.html`, and keep the shell `no-cache`.
- **Keep the worker at `/service-worker.js`, same scope, still `type: 'module'`.** Installed PWAs then go through the existing user-prompted update: the old Svelte app's `UpdatePrompt` offers the reload, `skipWaiting` activates the Vue worker, and `cleanupOutdatedCaches` drops the old precache. Verify module output from injectManifest in the spike (`rollupFormat: 'es'`).
- **Keep every storage key byte-identical** (`fanfan:pending-logout`, theme, persisted UI prefs, the IndexedDB entry name), so a pending offline logout and the user's settings survive the cutover. The query cache itself is busted by the new build id, which is intended.

### 4.7 UI kit

1. Before regenerating, list our local edits to each `ui/` component (`git log -p -- frontend/src/lib/components/ui/<name>`). `docs/frontend.md` §3 makes component defaults part of our contract.
2. `components.json` uses shadcn-svelte's `"style": "vega"`. shadcn-vue's docs show only `new-york`. **Spike item:** check whether shadcn-vue's CLI has vega. If not, init with `new-york` and port vega's radius/size/spacing deltas by hand. They are vendored files either way.
3. Regenerate the 26 components with `shadcn-vue add`, re-apply step 1's edits, and re-check the radius, z-index and typography scales from `docs/frontend.md` §3.

## 5. Strategy: a parallel app, then one cutover

`main` deploys to production, so a half-ported frontend can never land there. In-place incremental migration is impossible: one router owns the URL space, and Svelte and Vue can't share a page tree. So:

- Build the Vue app in **`frontend-vue/`** on `main`, behind its own CI job (lint, `vue-tsc`, Vitest, build, Playwright). It is never deployed until cutover. Small PRs, one phase or one screen each.
- **The Playwright suite is the parity oracle.** Point it at `frontend-vue`'s build, and port each screen until that screen's specs pass unchanged. A spec that needs editing marks a behaviour change and needs a reviewer's eye.
- **Dual maintenance.** Frontend changes merged to `frontend/` during the port must be mirrored. Keep a checklist issue that lists `frontend/` commits since the fork point. Freeze frontend feature work for the last two phases.
- **Timing:** do the cutover well away from the festival weekend, never in the weeks before it.

## 6. Phases

Each phase ends with the frontend gates green for `frontend-vue` (`lint`, `check`, `test`, `build`) plus the exit criterion.

### Phase 0: spike and decisions

Scaffold `frontend-vue/` with Vite 8, `@vitejs/plugin-vue`, `vue-router/vite`, Pinia, vue-query, VueUse, vite-plugin-pwa and shadcn-vue. Prove the risky parts with throwaway pages:

- route-group layouts and typed routes (§4.1 spike gate);
- boot order: persisted restore + `/me` settle before the first guard runs, including an offline cold start;
- injectManifest emitting a module worker at `/service-worker.js` that precaches `index.html` and serves it for navigations;
- the hey-api `@tanstack/vue-query` output compiling against our `clientConfig.ts`;
- shadcn-vue `vega` style availability (§4.7);
- `@sentry/vite-plugin` upload skip when unconfigured.

**Exit:** the ADRs from §9 drafted, and every spike item answered or given a fallback.

### Phase 1: foundation

- Copy the pure TS (`api`, `utils`, `constants`, `data`, `types`, `testing`) and its 24 unit tests. Replace the `$app/*` imports (`resolve` from `$app/paths` → typed router locations; env → `import.meta.env`).
- Tooling: `eslint.config.js` (vue + typescript-eslint + perfectionist), Prettier, `vue-tsc`, knip (Vue plugin), Vitest config, `openapi-ts.config.ts` with the vue-query plugin.
- `vite.config.ts`: port the env loading, `define`, dev proxy, `strictPort`, the env-presence plugin, Sentry and PWA plugins.
- `Dockerfile` (output `dist/`) and `nginx.conf` variant. CI job `frontend-vue`. `just` recipes `frontend-vue-*`.

**Exit:** `pnpm test` passes the copied suite. `pnpm build` produces a deployable empty shell.

### Phase 2: app core

- `main.ts` boot: QueryClient defaults, offline allowlist, persister, identity settle, guards.
- Session store, EventsClient provide/inject, SSE→cache invalidation map (root layout's four handlers), `watchApiResponses`, reachability monitor, theme/PWA/toast stores, SW registration, `UpdatePrompt`, Sentry, chunk recovery.
- `(app)` shell: sidebar, navbar (meta + actions store), bottom nav, skip link, view transitions; error and 404 pages.
- Port `session.test.ts`, `cooldown`, `persisted` and `navTransition` tests (composables tested inside `effectScope`, still no DOM: ADR-0011).

**Exit:** `smoke.spec.ts`, `realtime.spec.ts` and the offline-boot part of `offline.spec.ts` pass.

### Phase 3: UI kit and shared components

shadcn-vue components (§4.7), then today's `lib/components` (EmptyState, ErrorState, OfflineUnavailableState, StaleDataNotice, CaptchaWidget, PasswordInput, LoadMoreButton, …) and `offlineWriteGate`.

**Exit:** a scratch page renders every component in light and dark mode, and `accessibility.spec.ts` axe checks pass on it.

### Phase 4: screens

Port in this order (risk first, each with its specs):

1. `login` (OTP, captcha, OAuth error params) → `login.spec.ts`
2. home (hero via imagetools, voting card offline rule) → `smoke`, `native-feel`
3. schedule + `schedule/changes` (largest page, staff actions, subscriptions) → `schedule.spec.ts`
4. profile, account, ticket, notification settings (push subscription) → `profile.spec.ts`
5. notifications feed (infinite query) → `notifications.spec.ts`
6. voting + nomination (online-only rules) → `voting.spec.ts`, `voting-cast.spec.ts`
7. map (photoswipe, imagetools) → `map.spec.ts`
8. feedback, tools (broadcast, import, generate-tickets, settings, sync, users, voting) → `tools.spec.ts`, `broadcast.spec.ts`
9. install flow → `install.spec.ts`

**Exit:** the full Playwright suite passes against `frontend-vue`, including iOS-Safari (WebKit) and the `offline.spec.ts` offline-write gates.

### Phase 5: parity hardening

- `just readme-gallery` against the Vue build. Images should match the Svelte ones; differences are bugs or deliberate.
- Lighthouse / Core Web Vitals and bundle size side by side with the Svelte build on a mid-range phone profile. Budget: no worse LCP/INP. Vue's runtime is a fixed cost Svelte's compiler output doesn't carry (inference, measure it).
- Manual checks on real devices: installed iOS and Android PWA, push delivery and `notificationclick`, offline cold start, SW update prompt **from the Svelte build to the Vue build** (§4.6).
- Russian-copy scan: no English leaked into `.vue` templates.

**Exit:** sign-off from a maintainer on the comparison.

### Phase 6: cutover

One PR: freeze `frontend/`, mirror the outstanding commits, `git rm -r frontend && git mv frontend-vue frontend`, update everything in §7, deploy. Rollback = redeploy the previous GHCR tag. The old SW and storage keys stay compatible both ways because the paths and keys are unchanged. Suggest a **MAJOR** version bump in the PR (whole frontend replaced). The bump itself stays the maintainer's call.

### Phase 7: cleanup

Remove Svelte dependencies and skills from `skills-lock.json`, delete the `svelte-editor` agent, and close the dual-maintenance issue.

## 7. Repo touch points at cutover

- **AGENTS.md:** stack line, "Load before you edit" table (`.svelte` rows → `.vue` with `vue-best-practices`; `shadcn-svelte` → shadcn-vue's skill if one exists; check `vuejs-ai/skills` for router/Pinia skills), codebase map (`frontend/src/` layout from §4.2), "Never keep request- or user-scoped state in a frontend module singleton" gains the Pinia reset clause.
- **`.claude/`:** `post-edit-check.py` English scan `.svelte` → `.vue`; `agents/svelte-editor.md` → `vue-editor.md`; `rules/frontend.md`; `gate-runner.md`, `ru-copy.md` paths; `hooks/session-start.sh`.
- **Tooling:** `justfile`, `.github/workflows/ci.yml` (gates, `PUBLIC_*` env block), `.pre-commit-config.yaml`, `renovate.jsonc` groups, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose*.yml`, `.vscode/extensions.json` (Vue – Official).
- **Docs:** rewrite `docs/frontend.md` (keep every FAN FAN–specific rule, swap the mechanics), `docs/api.md` (`createQuery` → `useQuery`), `docs/testing.md`, `docs/dependencies.md`, `frontend/e2e/README.md`, README stack badges and gallery.

## 8. Risks

| Risk                                                                      | Mitigation                                                   |
| ------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Group layouts in file-based routing don't fit our tree                    | Phase 0 gate; fallback is an explicit route table (§4.1)     |
| shadcn-vue has no `vega` style                                            | Port the deltas by hand (§4.7)                               |
| Lost hover-prefetch head start makes navigations feel slower              | `PrefetchLink` (§4.1), measured in Phase 5                   |
| Pinia stores leak one user's state into the next session                  | Reset clause in Session cleanup + documented rule (§4.3)     |
| Non-reactive query options (plain objects) freeze queries on first params | Review checklist item; hey-api docs call it out              |
| Installed PWAs stuck on the Svelte worker                                 | Same SW path, scope and type; verified on devices in Phase 5 |
| Dual maintenance drifts                                                   | Checklist issue + freeze for Phases 5–6                      |
| Bundle/runtime regressions on low-end phones                              | Phase 5 budget gate                                          |

## 9. ADRs and docs

New ADRs (immutable, per [docs/adr/README.md](../../adr/README.md)):

1. **Vue 3 replaces Svelte 5 for the frontend.** Supersedes the framework part of ADR-0007; the SPA, static-bundle and build-time-env decisions carry over. Records why we are switching (to be written by the maintainers; this plan does not argue it) and the alternatives considered.
2. **Vue Router 5 file-based routing with guards in `beforeEach`**, or the explicit table if the spike fails.
3. **Pinia for client-side app state**, with the reset rule (§4.3).
4. **`vite-plugin-pwa` `injectManifest` returns.** Supersedes ADR-0020: the reason we left the plugin (no SvelteKit 3 support) is gone with SvelteKit. ADR-0016's `injectManifest`-over-`generateSW` reasoning stands.

ADR-0011 (Vitest, no component tests), ADR-0017 (hey-api), ADR-0019 (PhotoSwipe), ADR-0021 and ADR-0022 (TanStack Query, mutations) keep their decisions. The new framework ADR notes that ADR-0021/0022 now apply through `@tanstack/vue-query` (`createQuery` → `useQuery`, `createMutation` → `useMutation`).

## 10. Open questions for maintainers

1. Why switch? ADR #1 needs the motivation (hiring, ecosystem, team familiarity) in writing, so reviewers can weigh it against the cost in §2.
2. Is a frontend feature freeze for Phases 5–6 acceptable, and when is the next festival date the cutover must avoid?
3. Typed file routes vs. an explicit route table, if the spike shows both work: the plan prefers file routes for typed navigation.
