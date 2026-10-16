# Plan: migrate the frontend from SvelteKit (Svelte 5) to Vue 3

Status: **proposal**. Nothing here is decided until an ADR lands (Phase 0).
Target stack: Vue 3 + `<script setup lang="ts">`, Vue Router (file-based), Pinia,
TanStack Vue Query, VueUse, shadcn-vue on Reka UI. Everything below follows the
`vue-best-practices` skill (`npx skills use https://github.com/vuejs-ai/skills --skill vue-best-practices`).

## What stays fixed

These are product constraints, not Svelte choices. The port must keep each one
and the E2E suite must prove it:

- Client-rendered SPA, static bundle behind NGINX with a fallback page, no Node
  server (ADR-0007).
- Offline allowlist: the six `OFFLINE_QUERY_KEYS` restored from IndexedDB
  **before first render**, 7-day `maxAge`, version `buster`, custom
  `shouldDehydrateQuery` (root `+layout.ts`).
- Identity settles (`/me` via `queryForLoad`) before any guard runs; the boot
  splash in `app.html` covers that wait.
- Online-only mutations (`networkMode: 'always'`, ADR-0022), `offlineWriteGate`,
  queued logout (`pendingLogout`), one reachability state, one SSE→cache map.
- Hand-written service worker body (push, update handshake, API bypass, image
  runtime cache) at the **same URL and scope**, `/service-worker.js`, so already
  installed PWAs update instead of being stranded.
- All user-facing copy in `messages/ru.json` via Paraglide.
- No request- or user-scoped state in module singletons (AGENTS.md "Never").

## Size of the job

Measured on `main`:

| Surface | Count |
| --- | --- |
| `.svelte` files / lines | 217 / ~15.8k |
| `.svelte.ts` rune modules (services) | 9 |
| Plain `.ts` (utils, api, services, generated client) | ~970 files, mostly the generated client and Paraglide output, all framework-agnostic |
| `createQuery` / `createMutation` / `createInfiniteQuery` / `useQueryClient` | 81 / 67 / 10 / 48 |
| `$derived` / `$props` / `$state` / `$bindable` / `$effect` | 242 / 186 / 140 / 137 / 19 |
| `{#snippet}` / `{@render}` | 41 / 102 |
| `<svelte:head>` / `createContext` / `{@attach}` | 27 / 12 / 6 |
| `$app/paths` / `$app/state` / `$app/navigation` / `$app/env*` | 27 / 10 / 6 / 13 |
| shadcn `ui/` components | 25 |
| `+page.ts` / `+layout.ts` loads | ~40 |
| Vitest files / Playwright specs | 32 / 19 |

Most of `src/lib/utils`, `src/lib/api` and the non-rune services carry over
untouched. The Playwright suite locates elements by role and Russian name, so it
is framework-neutral. It is the parity gate for the whole migration.

## Dependency map

Versions were the npm `latest` tags on 2026-10-16. Pin exact versions and add
them to `renovate.jsonc` when you install.

| Today (Svelte) | Replacement (Vue) | Notes |
| --- | --- | --- |
| `svelte` 5, `@sveltejs/kit` 3 | `vue` 3.5.x, `@vitejs/plugin-vue` 6 | |
| SvelteKit router + `+page.ts` loads | `vue-router` 5.4 with file-based routing (`vue-router/vite`) | v5 merges unplugin-vue-router into core ([migration guide](https://router.vuejs.org/guide/migration/v4-to-v5)). Route groups `(app)`, `(protected)` and `[id]` params are supported ([file-based routing](https://uvr.esm.is/guide/file-based-routing.html)). Skip the data loaders: they live in `vue-router/experimental`. |
| `@sveltejs/adapter-static` (`200.html`) | Plain `vite build` → `dist/index.html` | Point NGINX `try_files` at `index.html`, or emit `200.html`, and update the SW fallback to match. |
| `@tanstack/svelte-query` 6 | `@tanstack/vue-query` 5.104 | |
| `@tanstack/svelte-query-persist-client` | `persistQueryClient` from `@tanstack/query-persist-client-core` 5.104 | Framework-agnostic. Restore before `app.mount()`. I found no first-party Vue persist page, so prove this in the Phase 0 spike. |
| hey-api `@tanstack/svelte-query` plugin | hey-api `@tanstack/vue-query` plugin | Supported by `@hey-api/openapi-ts` ([docs](https://heyapi.dev/openapi-ts/plugins/tanstack-query)). Regenerate, then update every `…svelte-query.gen.js` import. |
| `.svelte.ts` classes + `createContext` | Composables with `provide`/`inject` (`InjectionKey`), Pinia for app-wide client state | See "State" below. |
| hand-rolled listeners, timers, storage | `@vueuse/core` 15 (+ `@vueuse/router`) | See "Services" below. |
| `shadcn-svelte` + `bits-ui` | `shadcn-vue` 2.8 + `reka-ui` 2.11 | Regenerate the 25 `ui/` components with the CLI, then re-apply the local deltas from docs/frontend.md §3 "Syncing ui/". |
| `@lucide/svelte` | `@lucide/vue` 1.58 | Not `lucide-vue-next`. |
| `unplugin-icons` (`compiler: 'svelte'`) | same plugin, `compiler: 'vue3'` | |
| `svelte-sonner` | `vue-sonner` 2 | |
| `mdsvex` (ADR-0028) | `unplugin-vue-markdown` | Six guide articles. Supersedes ADR-0028. |
| `@sveltejs/enhanced-img` | `vite-imagetools` 12 + a small `<ResponsivePicture>` | `enhanced:img` is built on imagetools. The precache exclusion in `precacheManifest.ts` stays. |
| SvelteKit SW build + `$app/manifest` (ADR-0020) | `vite-plugin-pwa` 2 in `injectManifest` mode, worker body unchanged | ADR-0020 dropped vite-pwa only because it did not support SvelteKit 3. That reason does not apply to plain Vite. New ADR. |
| `@sentry/sveltekit` 10 | `@sentry/vue` 11 + `@sentry/vite-plugin` | This is a major version jump, so read the v11 changelog first. Use `browserTracingIntegration({ router })`. Source-map upload keeps the same four env vars. |
| `@inlang/paraglide-js-svelte` (6 rich-text components) | A ~20-line Vue render of Paraglide's markup parts | The `m.*` functions are framework-agnostic and stay. |
| `<svelte:head>` (27) | `useTitle` (VueUse) if only titles are set, otherwise `@unhead/vue` 3 | Audit first. OG tags stay static in `index.html`. |
| `svelte-check` | `vue-tsc` 3 | |
| `eslint-plugin-svelte`, `prettier-plugin-svelte` | `eslint-plugin-vue` 10 + `@vue/eslint-config-typescript`. Prettier formats `.vue` natively. | Keep ADR-0030 (better-tailwindcss) and ADR-0031 (strict type-aware) settings. |
| Vitest `*.svelte.test.ts` | Vitest, `environment: 'node'`. Composable tests run inside `effectScope()`. | ADR-0011 stays: no component tests. |

## Concept map (Svelte → Vue)

| Svelte 5 | Vue 3 |
| --- | --- |
| `$state` (primitive) | `shallowRef` (skill rule: `shallowRef` for primitives) |
| `$state` (object) / `$state.raw` | `ref` / `reactive` / `shallowRef` |
| `$derived`, `$derived.by` | `computed` (pure getters only) |
| `$effect` | `watch` / `watchEffect` with `onCleanup`. Prefer an event handler or a VueUse composable. |
| `$props()` + typed `PageProps` | `defineProps<…>()`. Route params come from `useRoute()` with typed routes. |
| `$bindable` (137, mostly `ui/`) | `defineModel()` |
| `{#snippet}` / `{@render}` | Named and scoped slots |
| `createContext` / `getContext` | `provide`/`inject` with an exported `InjectionKey` |
| `{@attach}` | A template ref plus a composable. Use a custom directive only if it is purely DOM. |
| `<svelte:window>` / `<svelte:document>` | `useEventListener(window \| document, …)` |
| `<svelte:boundary>` | An `ErrorBoundary` component built on `onErrorCaptured` |
| `goto` / `$app/state` `page` | `router.push` / `useRoute()` |
| `resolve()` from `$app/paths` | Typed `RouterLink :to="{ name, params }"` |
| `createQuery(() => opts)` | `useQuery(computed(() => opts))`. Pass a getter or computed, never a snapshot, so reactive params refetch. |
| `createMutation` (ADR-0022) | `useMutation`. The ADR decision holds; amend its wording. |

## Architecture decisions to settle in the ADR

1. **Bootstrap replaces the root load.** `main.ts` builds the `QueryClient`,
   sets the offline defaults, awaits `persistQueryClient` restore and the `/me`
   settle, then installs `VueQueryPlugin({ queryClient })`, Pinia and the router
   and mounts. The client belongs to the app instance, not to a module export,
   which keeps the singleton rule. The `app.html` splash stays until mount.
2. **Guards move to a global `router.beforeEach`.** It reads `to.meta`, which
   each page or layout sets with `definePage({ meta: { access: 'protected' | 'guest' | 'tools' } })`.
   The rule "putting a route in the group is the guard" survives as "the group
   layout's meta is the guard". Per-route prefetch moves into the guard or the
   view as `queryClient.prefetchQuery`/`ensureQueryData`. Navbar data becomes
   route meta.
3. **Pinia holds client state only.** Server state stays in TanStack Query.
   Never copy the user, schedule or anything else from the cache into a store.
   A Pinia store lives as long as the document, the same lifetime as a module
   singleton, so anything account-scoped in one needs `$reset()` inside
   `Session`'s shared logout and expiry cleanup. Good candidates: theme, PWA
   install prompt, app update, toasts queue. `Session` and reachability can be
   setup stores or `provide`d composables. Pick one style and record it.
4. **Env stays `PUBLIC_*`.** Set `envPrefix: ['PUBLIC_']`, never a bare `SENTRY_`
   (that would expose `SENTRY_AUTH_TOKEN`). Keep a typed `env.ts` and fail
   `vite build` on a missing declared var, as `$app/env/public` does today.
   Renaming the variables would also touch `.env.example`, both workflows,
   compose and the Dockerfile for no gain.
5. **The service worker keeps its URL, scope and body.** Only its build changes:
   `$app/manifest` becomes `self.__WB_MANIFEST`, and `$app/env` `version`/`dev`
   become `define` constants.

## Phases

Each phase ends with the gates green: `just frontend-lint`, `just frontend-check`
(now `vue-tsc`), Vitest, and the Playwright suite run against the Vue build.

**Phase 0: decision and spike (go/no-go).**
Write the ADR: why we are moving (a cost-benefit, not a preference), and what
it supersedes or amends (0020, 0021 binding, 0022 wording, 0027 rich text,
0028). Build one vertical slice in a throwaway branch: bootstrap with persist
restore, `(protected)` guard, `/schedule` offline from IndexedDB, one mutation
behind `offlineWriteGate`, SW install in a prod build. Exit when the slice's
existing Playwright specs pass unchanged.

**Phase 1: scaffold side by side.**
Create `frontend-vue/` next to `frontend/` so `main` keeps shipping. Port
config (Vite, Tailwind v4, `app.css` tokens, Paraglide, hey-api with the Vue
plugin, ESLint, Prettier, knip, Vitest, Playwright pointed at the new build).
Copy `src/lib/{utils,api,constants,data,types}` and `messages/` as they are.

**Phase 2: services.**
Port the 9 `.svelte.ts` modules plus `useInterval`/`listen`/`minuteClock`. Port
their unit tests alongside.

| Module | Becomes |
| --- | --- |
| `persisted.svelte.ts` | `useStorage` over `safeStorage` (a custom `StorageLike`) |
| `theme.svelte.ts` | `useColorMode` / `usePreferredDark` |
| `cooldown.svelte.ts` | `useIntervalFn` + `useTimestamp` |
| `minuteClock.ts`, `useInterval.ts` | `useNow({ interval })` / `useIntervalFn` |
| `documentVisibility.ts` | `useDocumentVisibility` |
| `events.svelte.ts` (SSE) | Keep the hand-written `EventsClient`; wrap it in a composable. `useEventSource` has no backoff, watchdog or reporting. |
| `pwa`, `appUpdate`, `toasts` | Pinia setup stores |
| `pushDevice.svelte.ts` | A composable. Its ports and fakes are unchanged. |
| `captcha.svelte.ts` | A composable around `smartcaptcha.ts` |

**Phase 3: UI kit.**
Run `shadcn-vue init` and add the 25 components, then re-apply our deltas
(typography, radius and z-index scales; modal structure from §7). Port the 15
shared `lib/components`. `UserAvatar`, `ErrorState`, `StaleDataNotice` and
`OfflineUnavailableState` come first, since every page uses them.

**Phase 4: shell.**
`main.ts` bootstrap, root and group layouts, guards, `Session` wiring, the 401
interceptor, the SSE→cache map, the bottom nav, the error pages, the SW with
vite-plugin-pwa, Sentry, and the `vite:preloadError` reload.

**Phase 5: routes, in dependency order.**
Each area is one PR that ports its components and passes its E2E specs.
1. `(auth)/login`
2. Home
3. Schedule, then schedule changes
4. Notifications
5. Profile (account, ticket, notifications)
6. Voting
7. Guide and map (markdown, imagetools, PhotoSwipe)
8. Tools (users, broadcast, import, sync, settings, voting, feedback, tickets)

Split components on the skill's triggers (3+ UI sections, state plus
multi-section markup). Keep route views as composition surfaces.

**Phase 6: cutover.**
- Full Playwright parity plus a manual check of the SW update path, run with
  `just run-prod` on a device that has the Svelte PWA installed.
- Swap the directories and update the `Dockerfile` (`dist/`), `nginx.conf`,
  `justfile`, CI, `docker-compose.yml`, `.pre-commit-config.yaml` and
  `renovate.jsonc`.
- Run `just readme-gallery`.
- Delete `frontend-svelte`.

**Phase 7: docs and agent tooling, in the cutover PR.**
- Rewrite `docs/frontend.md` for Vue and update `docs/api.md` and
  `docs/testing.md`.
- AGENTS.md: update the stack, the "Load before you edit" table (svelte skills
  become `vue-best-practices`, the shadcn skill becomes shadcn-vue), the
  codebase map and "Svelte AI tooling".
- Drop the `svelte` MCP from `.mcp.json` and the plugin from
  `.claude/settings.json`.
- Update `.claude/hooks/post-edit-check.py` to scan `.vue` instead of `.svelte`,
  and update `.claude/rules/*`.
- Vendor `vue-best-practices` into `skills-lock.json`.

## Risks

- **Installed PWAs.** If the SW URL or scope changes, or the fallback page name
  changes without a matching worker update, old installs keep serving the
  Svelte shell. Mitigation: same `/service-worker.js`, and test the upgrade
  explicitly in Phase 6.
- **Boot ordering.** If the router resolves before persist restore and `/me`,
  guards misroute offline users. Mitigation: mount only after bootstrap
  resolves, and install the router last.
- **Reactive query options.** A `useQuery(opts)` built from a snapshot won't
  refetch when params change. Mitigation: always pass a getter or `computed`,
  and add a lint or review checklist item.
- **Pinia vs. the singleton rule.** Mitigation: decision 3 above, with stores
  reset in `Session` cleanup.
- **Sentry 10 → 11 and vite-plugin-pwa 2.** Mitigation: read both changelogs in
  Phase 0.
- **A two-tree period** doubles Renovate PRs and CI time. Keep it short by
  freezing feature work on the Svelte tree after Phase 4.

## Open questions for the maintainer

1. What is driving the move (hiring, ecosystem, a specific library)? The ADR
   needs it, and it decides whether a partial port is ever acceptable.
2. Should Pinia also own `Session` and reachability, or only UI-level client
   state?
3. Side-by-side `frontend-vue/` (recommended) or an in-place rewrite on a
   long-lived branch?
