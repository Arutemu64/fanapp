# Frontend & SvelteKit Guidelines

This document outlines the codebase-specific constraints, SvelteKit SPA rules, styling standards, layout designs, and custom component inventory.

> [!NOTE]
> **Scope of this doc**: only FAN FAN–specific decisions and bindings live here — chosen scales, tokens, component wiring, conventions. Generic best-practice (Svelte 5 runes and event syntax, accessibility, UX, responsive + dark-mode mechanics) lives in the `svelte-code-writer`, `svelte-core-bestpractices`, `ui-ux-pro-max`, `accessibility` and `core-web-vitals` skills — load those (AGENTS.md, "Load before you edit"). **Rule of thumb**: if a skill that has never seen this repo could state a rule, it belongs in the skill, not here. What only this repo knows belongs *here* — or in a code comment next to the constraint it explains. A `fanfan-*` skill is for the narrow remainder that fits neither: knowledge with no single file to live beside, like the Russian glossary or the migration traps.

---

## 1. Client Rendering (SPA) & State Isolation

The app is a **client-rendered SPA**: `export const ssr = false` lives in the root `src/routes/+layout.ts`, so pages render only in the browser — nothing renders on a server. The app is built with `@sveltejs/adapter-static` (SPA mode, `fallback: '200.html'`) into a static bundle, served in production by a small **NGINX** container (`frontend/nginx.conf`) that falls back to `200.html` for every unknown route so the client router can take over. There is no Node server.

* **Build-time `PUBLIC_*` env**: Because nothing runs at runtime, the app reads its public env via `$env/static/public` (not `$env/dynamic/public`), so `PUBLIC_API_URL`, `PUBLIC_VAPID_KEY`, `PUBLIC_SENTRY_DSN`, `PUBLIC_SENTRY_ENVIRONMENT`, `PUBLIC_SENTRY_TRACES_SAMPLE_RATE` and `PUBLIC_SMARTCAPTCHA_CLIENT_KEY` are **baked into the bundle at build time**. Changing one means rebuilding the image — the server's `.env` cannot inject them into a prebuilt image. In CI they come from GitHub repository variables (see `.github/workflows/docker-publish.yml`); for local `just run-dev`/`run-prod` they come from the root `.env` build args. Every referenced `PUBLIC_*` var must exist (even if empty) at build time, or the build fails. **All env lives in the single root `.env`** — the frontend has no env file of its own: `frontend/svelte.config.js` (`kit.env.dir`) points `$env/static/*` at the repo root, and `frontend/vite.config.ts` sets `envDir` plus a `loadEnv` call for the values the config itself needs (`FRONTEND_PORT`, `VITE_API_PROXY_TARGET`, and the `SENTRY_*` source-map upload settings below) — Vite never injects `.env` files into `process.env` while the config is evaluated, so plain `process.env` reads would miss them. Real environment variables (Docker, CI) always take precedence over file values.
* **Sentry source-map upload is fully env-driven**: `frontend/vite.config.ts` passes `SENTRY_URL`, `SENTRY_ORG`, `SENTRY_PROJECT` and `SENTRY_AUTH_TOKEN` to `sentrySvelteKit()`, and uploads only when **all four** are non-empty. None of them has a hardcoded fallback: the target instance is deployment-specific, so a baked-in default silently outlives the instance it was written for and the upload then fails against a dead host. These are build-time only — unlike `PUBLIC_SENTRY_DSN` they are never inlined into the bundle. The first three are plain build args (`frontend/Dockerfile`, `docker-compose.yml`, CI repository variables); the token is a real secret and arrives as a BuildKit secret mount, so it never lands in layer metadata or the build cache. Leave any of them empty (the default everywhere, including local dev and CI) and the build simply skips the upload.
* **Adding a `PUBLIC_*` var means registering it in five places**: `$env/static/public` fails the build on any referenced var that does not exist, so a new one must be added to **all** of `.env.example`, `frontend/Dockerfile` (`ARG` + `ENV`), `docker-compose.yml` (`build.args`), `.github/workflows/docker-publish.yml` (`build-args`) **and** `.github/workflows/ci.yml` (the frontend job's `env:` block — easy to miss, since it is a second workflow). An empty value is fine everywhere; the name just has to exist. Miss the CI one and lint, check and build all fail together on the PR while local builds stay green, because your own `.env` has the key.
* **Sentry runtime settings must carry a `PUBLIC_` prefix**: `src/hooks.client.ts` configures the SDK from `$env/static/public`, so anything it reads has to be a `PUBLIC_*` var — Vite exposes nothing else to client code, and an unprefixed name silently resolves to `undefined` at runtime while still looking configured in `.env`. Hence `PUBLIC_SENTRY_ENVIRONMENT` and `PUBLIC_SENTRY_TRACES_SAMPLE_RATE`. Do **not** widen `envPrefix` to expose bare `SENTRY_*` instead: that same prefix covers `SENTRY_AUTH_TOKEN`, and the token must never be reachable from client code. The release is the exception — it is deliberately *not* passed to `Sentry.init()`. The build plugin injects the release it uploaded the maps under and the SDK defaults to that, which is the only value guaranteed to match; because `Sentry.init()` spreads caller options over its own defaults, passing `release` at all (even as `undefined`) would clobber it. Set the build-time `SENTRY_RELEASE` to name that release — required in Docker builds, where the `./frontend` context carries no `.git` for the plugin's commit-SHA detection.
* **Relative API base (`PUBLIC_API_URL=/api`)**: The default is a **relative** path, not an absolute URL. The SPA and API are served same-origin (Caddy routes `/api*` to the backend), so a relative base resolves against whatever origin serves the app — keeping the bundle (and the prebuilt GHCR image) domain-agnostic, so the same build runs on any domain with no rebuild. Browser consumers (`openapi-fetch`, the reachability probe, the SSE `EventSource`, the Telegram OAuth `href`s) resolve it against `location.origin`; the service worker resolves it against its own origin (`new URL(PUBLIC_API_URL, self.location.origin)`) since `new URL` throws on a bare path. In dev the frontend and backend are different origins, so `frontend/vite.config.ts` proxies `/api` to the backend (`VITE_API_PROXY_TARGET`, default `http://localhost:8000`; `http://api:8000` in the Docker dev overlay) and strips the `/api` prefix to mirror Caddy. Set an absolute URL only for the opt-in split-origin deployment (then also set `WEB__CORS_ALLOW_ORIGINS`).

* **Browser globals**: `window`, `document`, and `localStorage` are safe in component and module code, since nothing runs on the server. There is deliberately **no `browser` guard anywhere in `src/`** — `ssr = false` is a boolean literal, so SvelteKit evaluates the page option statically and never imports app code in a non-browser context, which makes `if (browser)` and `typeof window !== 'undefined'` dead branches that read as "this might run on a server" and force every consumer to handle an impossible null. Add one only if a module starts running under non-browser tooling (a Vitest `environment: 'node'` test that imports it).
* **Strict State Isolation**: Do not store user/session state in global/module-level variables, legacy stores, or reactive singletons. In a SPA a module singleton persists across client-side navigations and across login/logout — scoping avoids stale data bleeding between sessions.
* **Context API for Shared State**: For state shared across Svelte 5 components, keep logic in classes with `$state` fields instanced per component. Use Svelte 5's type-safe `createContext` utility (rather than global stores or raw module variables) to scope state to the component tree.
* **Effect avoidance**: Prefer (in order) event handlers, `{@attach ...}` for external libs, `<svelte:window>`/`<svelte:document>` for global listeners, and `createSubscriber` for external sources; reach for `$effect` only as a last resort. See `svelte-core-bestpractices`.

---

## 2. Data Loading & SvelteKit Integration

* **Data Fetching boundaries**: Move first-render data requirements into SvelteKit layout or page `load` functions. All loads are **universal** (`+page.ts`/`+layout.ts`) — there are no `.server.ts` loads in a SPA.
* **Pass the load `fetch`**: Always pass the SvelteKit-provided `fetch` (from load functions) inside the request options block of your client calls (e.g., `client.GET('/route', { fetch })`). It gives request deduplication, relative-URL resolution, and integration with `invalidate()`. The session cookie is carried automatically by the browser (the API client uses `credentials: 'include'`).
* **Session-expiry reconciliation (401 middleware)**: Every client from `createApiClient` carries an `openapi-fetch` middleware that reacts to a `401` on any endpoint by firing `invalidate('app:current-user')` (debounced to one refresh per burst). The root layout then re-fetches `/me/`, caches the logged-out verdict, clears per-user caches, and the `(protected)` guard redirects — so an expired session flips the whole app to guest state instead of leaving a stale "logged in" UI. `/me/` itself is excluded (it *is* the verdict — reacting would loop) and so are the credential logins (`/auth/login`, `/auth/login-with-code`), whose 401 means "wrong credentials". Components keep their own inline 401 handling; the middleware is fire-and-forget and never swallows the response.
* **Typed `data`**: Always type page/layout props with the generated `PageProps`/`LayoutProps` (or `PageData`/`LayoutData`) from `./$types`. Never leave `$props()` untyped — typed `data` is what catches load/page mismatches at check time.
### Access Control (don't duplicate guards)

Guards run client-side in **universal `load`** functions (these are UX redirects only — the backend enforces real auth on every endpoint):

* The root `+layout.ts` fetches the current user from `/me/` and returns `user`, so it flows down to **every** page. Do not re-return `user` from a nested layout — it is already inherited.
* Route-group layouts gate by membership: `(app)/(protected)/+layout.ts` requires a logged-in user (else → `/login?next=<attempted path>`); `(auth)/+layout.ts` is guests-only (else → the validated `next` target, or `/`). Putting a route inside the group is the guard — do **not** re-check `user` in that route's `load`.
* **Post-login destination (`?next=`)**: the `(protected)` guard preserves the attempted path in the `next` query param and `completeLogin` (`$lib/utils/auth.ts`) navigates there after login. Any value read from `next` MUST go through `sanitizeNextPath` first — it only accepts in-app absolute paths (rejects absolute URLs, `//host`, and backslash forms) so a crafted login link can't become an open redirect. The Telegram OAuth login goes through a backend redirect and does not carry `next`.
* **OAuth outcomes (`?oauthLoginError=` / `?oauthLinkError=`)**: login and account linking share one backend callback (`/auth/oauth/{provider}/callback`) and are told apart by an intent stored in the OAuth state. It is entered by a top-level browser navigation, so the backend cannot answer with an error body — the browser would render the JSON as the page. Instead it redirects to `/login` or `/profile` (whichever the intent says) with a one-time code. `$lib/utils/oauthErrors.ts` holds the param names, the shared `cancelled`/`failed` codes (mirrored from `presentation/web/oauth.py`) and `readOAuthErrorCode`, which whitelists the value — never render a code straight off the URL. Each page maps its codes to Russian copy and clears the param with `clearOAuthErrorParam` so a reload does not replay the toast. The linking flow adds `linked_to_another_account`, `user_already_has_telegram` and `session_changed` (the browser signed in as somebody else mid-flow, so the link was refused rather than retargeted).
* A nested `+layout.ts` should only add checks the group can't express — e.g. a finer-grained `error(403, …)`. The whole `tools/` section is already gated by `tools/+layout.ts` via the `canManageSettings`/`canImportSchedule`/`canSendNotifications` permission helpers; never re-check organizer access inside individual tools pages.

### PWA & Offline Support

The app is an installable PWA: `static/manifest.json` (icons, standalone display) + a service worker (`src/service-worker.ts`) that the root layout registers via `registerServiceWorker` (`$lib/utils/serviceWorker.ts`). SvelteKit compiles the worker; [`@vite-pwa/sveltekit`](https://vite-pwa-org.netlify.app/frameworks/sveltekit.html) in `injectManifest` mode injects the build manifest at `self.__WB_MANIFEST` and Workbox handles precaching — see [ADR-0016](adr/0016-workbox-precaching-via-vite-pwa.md). SvelteKit's own auto-registration is disabled (`serviceWorker.register: false` in `svelte.config.js`) because it leaves the `register()` promise's rejection unhandled — a browser that refuses registration (storage-partitioned in-app browsers, private modes) degrades to online-only, which is expected, but surfaced an uncaught "Error: Rejected" to Sentry; our wrapper mirrors SvelteKit's defaults (same script path and module/classic type, registered on `load`) with a `.catch()`. Workbox `precacheAndRoute` precaches the app shell from the injected manifest (JS/CSS/fonts, the SVG logo/favicon, and `static/`; responsive raster image sets are excluded and runtime-cached instead, see below), a `NavigationRoute` serves the precached `200.html` shell for navigations, and the SW handles web-push. It **never caches API requests** — the backend is served under a path on the *same* origin (e.g. `/api`, derived from `PUBLIC_API_URL`): no route matches that path and the navigation fallback denylists it, so API calls hit the network directly; their user-specific data is cached by the app layer, never the SW. `UpdatePrompt.svelte` (mounted in the root layout) surfaces a "new version" banner when a fresh build is waiting and reloads on `controllerchange`; the SW activates the waiting worker only when it receives a `'skipWaiting'` message. OS integration: the manifest declares `shortcuts` (long-press app-icon menu: Программа/Уведомления/Карта) and `launch_handler: navigate-existing` (links into the installed app reuse the open window instead of spawning a duplicate), and the Badging API mirrors the unread-notification count onto the app icon via `$lib/utils/appBadge.ts` — `NotificationBell` syncs the exact count, logout clears it, and the SW push handler sets a count-less "flag" badge that the bell replaces on next open.

* **Failed chunk loads self-recover with a guarded reload.** `hooks.client.ts` listens for Vite's [`vite:preloadError`](https://vite.dev/guide/build#load-error-handling) — a dynamically imported chunk that failed to fetch, typically a boot node dropping on a flaky mobile connection before the SW cached it, or version skew after a deploy removed the old hashed chunk a still-open document points at. SvelteKit already recovers this during client-side navigation, but not on the first load, where it strands the user on the error page (`handleError`). The handler does a full-page reload (the shell is served `no-cache`, see `frontend/nginx.conf`), guarded by a `sessionStorage` timestamp so a genuinely-unreachable chunk falls through to the error page instead of looping, and only when the marker can be persisted — a browser whose storage throws is where an unguarded reload would spin.
* **Social share previews are static, baked into the shell.** The app is client-rendered (`ssr = false`), and social crawlers (Telegram, VK, WhatsApp, Facebook, X) don't run JS — they read only `app.html`, never the per-page `<svelte:head>`. So the Open Graph + Twitter Card tags live directly in `app.html` and reach every route via the `200.html` fallback NGINX serves. `og:image`/`og:url` **must be absolute HTTPS** — [Telegram silently drops a relative `og:image`](https://opengraphplus.com/consumers/telegram/images), and the [OG protocol](https://ogp.me/) requires it — so the origin is baked at build time from `PUBLIC_SITE_URL` via SvelteKit's `%sveltekit.env.PUBLIC_SITE_URL%` placeholder (which only substitutes `PUBLIC_`-prefixed vars); an unset value degrades to a relative URL, fine locally but breaks prod unfurls. This means the OG tags, unlike the rest of the bundle, are **not** domain-agnostic — a per-domain rebuild bakes in the domain, same as any other `PUBLIC_*`. The preview image is `static/og-image.png` (currently the 512×512 app icon as a placeholder; swap for a 1200×630 1.91:1 card and update the `og:image:width`/`height` in `app.html`). Preview copy mirrors `manifest.json` (`name` + `description`) — keep them in sync.
* **Responsive image sets are runtime-cached, not precached.** The AVIF/WebP/… variants `<enhanced:img>` emits (the venue maps and the home hero) live in `build`, but precaching a whole set would store every width and format at install when a device only ever displays one — [Workbox's precaching dos-and-don'ts](https://developer.chrome.com/docs/workbox/precaching-dos-and-donts) calls this out specifically. `vite.config.ts` keeps them out of the precache manifest (`injectManifest.globIgnores` on the hashed `_app/immutable/assets` image variants) and the SW serves them **cache-first at runtime** via a Workbox `CacheFirst` route instead: content-hashed, so a cache hit is never stale; available offline after the first online view; and degrading to each component's own fallback (e.g. `HeroCard`'s branded bed) on a cold-offline first load. The route is bounded by an `ExpirationPlugin` (`maxEntries`/`maxAgeSeconds`, `purgeOnQuotaError`) — unlike the precache it isn't version-cleaned, so the cap is what stops superseded variants piling up across deploys. The SVG logo and favicon stay precached — a single SVG is density-independent, so there's no set to bloat.
* **`injectManifest`, not `generateSW`**: Workbox supplies the precache manifest and precaching helpers, but the worker body is ours — push, the update handshake, the API bypass, the image runtime cache all stay hand-written (see [ADR-0016](adr/0016-workbox-precaching-via-vite-pwa.md)). Don't switch to `generateSW` or a `workbox-config.js`; that generic PWA path assumes a fully generated worker and can't host those handlers.
* **The caching setup is inert in `vite dev`** (`self.__WB_MANIFEST` is only injected by a production build; the SW guards on its presence), because cache-first assumes the immutable versioned shell only a real build produces. So a service-worker change is **not** testable with `just frontend-dev` — verify it with `just run-prod`. The `push`/`notificationclick` handlers do stay registered in dev.
* **`manifest.json` shell colours are the dark app surface, not a brand tint.** `theme_color` and `background_color` are both `#111827` (`gray-900`, matching `dark:bg-gray-900` on `<body>` and the `app.html` boot splash). Equal values give a seamless single-colour launch splash — no brand-coloured band seam above the body, and no white flash in a dark hall. The manifest allows only one value each and can't be scheme-aware, so the shell recedes into the dark surface the majority sees; the watermelon accent lives inside the app and, for the *running* status bar, in the `app.html` `theme-color` metas, which vary by `prefers-color-scheme`. On rebrand, match both to the app's dark surface colour rather than the brand hue.
* **Rebranding for another event** — the visual identity is a fixed asset set; swap all of it in one change so no stale mark survives in a precache. Icons live in `static/icons/`: `icon-192.png` / `icon-512.png` (`any` purpose, full-bleed on an **opaque** background), `icon-maskable-192.png` / `icon-maskable-512.png` (`maskable`, mark inside the central 80% — 10% safe-zone padding — on an **opaque** background), `apple-touch-icon.png` (180×180, opaque), and `badge-96.png` (Android push badge: **transparent**, single-colour silhouette — Android tints it from the alpha channel, so an opaque icon renders as a solid blob). Favicons are `static/favicon.svg` + `static/favicon.ico`. The wordmark is `src/lib/assets/logo.svg` (sidebar + login): it's black-on-transparent so `dark:invert` alone covers dark mode (see `AppSidebar.svelte`) — keep that contract or ship a themed asset. Hero key art is `src/routes/(app)/components/home/main.webp`, and the social-share card is `static/og-image.png` (1200×630). Names and colours change in lockstep: `manifest.json` (`name`, `short_name`, `description`, `shortcuts`, `theme_color`, `background_color`), the `theme-color` metas + `apple-mobile-web-app-title` + the Open Graph/Twitter tags (title, description, `og:image` dimensions) in `app.html`, the `PUBLIC_SITE_URL` build var (new domain), and `primary-600` in `app.css` (the manifest shell colours re-derive from the palette per the note above). Event copy (name, date, venue, socials, countdown `TARGET`) lives in `HeroCard.svelte`. The end-to-end fork/rebrand flow (Actions variables, image names, timezone) is in [deployment.md](deployment.md#reusing-this-for-another-event), and the README's license section marks which of these assets are carved out of the MIT grant.
* **Read-only offline data**: For pages worth viewing offline (schedule, notifications; the profile renders from the cached `/me` identity below), wrap the load in `fetchWithCache` (`$lib/utils/offlineCache.ts`, IndexedDB via `idb-keyval`). It encapsulates the whole flow — skip the request when `isReachable()` is false, bound the fetch with `FIRST_PAINT_TIMEOUT_MS`, update reachability, persist the fresh copy, and fall back to the cache on error/timeout. Pass a `key`, a `scope`, and a `fetcher({ signal })` that returns the value to cache, or `undefined` to fall back; it returns `{ data, stale, cachedAt }`. Render `StaleDataNotice` when `stale` and pass `cachedAt` (epoch millis of when the shown copy was persisted) so the notice shows a "synced at" time via `formatSyncedAt`. Entries are stored as a `{ value, cachedAt }` envelope; entries written before this migration are read as bare values with no timestamp and upgraded on the next online write. Every entry is scoped: `userScope` entries (e.g. `subscriptions:${user.id}`, also keyed per user) are wiped by `clearUserCache` on logout so one device's account never serves another's data; `universalScope` entries (e.g. the public schedule, key `schedule`) are identical for everyone and survive logout. The low-level `readCache`/`writeCache`/`clearUserCache` helpers remain for non-`load` callers. Mutations (votes, settings) stay online-only.
* **Complete-miss handling (offline vs. failure)**: When `data` is `undefined` (nothing cached), branch on `isReachable()`: if offline, return a soft empty state with an `offlineMiss: true` flag so the page renders a calm inline "недоступно офлайн" message and keeps the app shell/bottom nav usable; only a *reachable* failure throws `error(503, …)`. The page suppresses `StaleDataNotice` when `offlineMiss` (there is no saved copy to caveat) and swaps the empty-state copy. This is more reliable than `ErrorState`'s render-time offline reframing, which can lag a beat behind the load's reachability verdict.
* **Online-only surfaces (`offlineUnavailable`)**: Some surfaces are deliberately *uncached* because they are all mutation and nothing worth reading offline. Voting (`voting/+page.ts`, `voting/[nominationCode]/+page.ts`) is the read-shaped case: casting a vote is a mutation, and the open/closed and already-voted state must never be shown stale (a cached ballot you can't submit is a dead end). Its load mirrors the complete-miss shape without a cache behind it: skip the request when `!isReachable()`, and in the `catch` re-throw a `throwApiError` result (an `isHttpError` — a *reachable* failure keeps its mapped status) but treat any other throw as a network failure — `markReachable(false)` and return an `offlineUnavailable: true` flag. The same flag also gates the pure submit/admin surfaces that fetch nothing: **feedback** (`feedback/+page.ts` returns `offlineUnavailable: !isReachable()`) and the whole **tools** subtree — `tools/+layout.ts` returns the flag and `tools/+layout.svelte` renders the online-only state in one place instead of gating each tool page, since every tool is an online-only mutation. Each page renders the shared `OfflineUnavailableState` component (`$lib/components/`, a fixed-icon `EmptyState` taking `title`/`message` — the copy stays per-surface because Russian agreement varies), keeping the app shell/bottom nav usable. Name the flag by what the sibling encodes: `offlineMiss` = a cache-backed page with nothing saved yet; `offlineUnavailable` = a surface that never caches. There is no `stale`/`cachedAt` here — there is no saved copy to caveat or timestamp.
* **Write controls on cached pages degrade, they don't fail (`offlineWriteGate`)**: pages that stay *readable* offline (profile, schedule) keep the mutations on top of them online-only — but rather than let a tap fail into an error toast, each write trigger disables with a hint. `offlineWriteGate()` (`$lib/utils/offlineAction.ts`) reads the `OfflineService` from context and returns reactive `{ disabled, title }`; bind them on the control (`disabled={gate.disabled || …}` `title={gate.title}`). One shared gate keeps every write control consistent and impossible to forget — a new button opts in with a single pair, no bespoke per-control logic. Its `OFFLINE_ACTION_HINT` mirrors the page-level "доступно только онлайн" copy so a disabled button and a blocked page speak with one voice. This is the *mixed read+write* answer; a surface that is all mutation uses the page-level `offlineUnavailable` state above instead.
* **Logout works offline, revoke is queued (`pendingLogout`)**: the session lives in an HttpOnly cookie, so JS can't clear it — a purely local logout would let the still-valid cookie silently restore the session on the next `/me`. So `AppNavbar.handleLogout` branches on `offline.isOnline`: online logs out normally; offline calls `markLogoutPending()` (`$lib/utils/pendingLogout.ts`, a persisted intent in `safeStorage`) then tears down local state (`clearUserCache`, badge, guest nav) at once so a shared device stops showing the account. The queued `POST /auth/logout` fires from `OfflineService` — on the offline→online edge and on a fresh boot (a boot that is already online never crosses the edge) — and is idempotent, so it is one intent, not a write queue. Until it succeeds, the root `+layout.ts` gates identity on `isLogoutPending()` (returns `{ user: null }`) so a valid cookie can't resurrect the account and there's no "logged back in" flicker. A fresh login cancels the stale intent: `completeLogin` clears it for password/code, and the VK OAuth click clears it before navigating away (OAuth bypasses `completeLogin`).
* **Identity caching contract (`me:user` in `+layout.ts`)**: the `/me` fetcher distinguishes three outcomes so a transient error can't silently log a user out and orphan their per-user caches: `200` → cache the user; explicit **`401`/`403`** → authoritative logout: cache `null` **and** `clearUserCache()` (mirrors `AppNavbar.handleLogout`, so no per-user entries linger for the next account); any **other** error (`5xx`, parse, empty) → return `undefined` so the last-good cached user is kept. Offline, `/me` throws and the cached user is served unchanged. Because identity only drops on a real logout/expiry (both of which clear the cache), per-user keys never go stale against the live session.
* **Warming a cache before first visit**: `warmCache` (`$lib/utils/offlineCache.ts`) proactively seeds a `fetchWithCache` entry for a page the user hasn't opened, so it works offline from the first run. The root `+layout.ts` warms the schedule on the first online boot. It is fire-and-forget (never `await`ed in a `load`, so it can't block first paint), a no-op when offline or already cached, and never refetches once warmed — the page's own `load` + the `schedule_updated` SSE event keep it fresh after that.
* **Connectivity vs. stream health**: `OfflineService` (`$lib/services/offline.svelte.ts`) exposes reactive *backend reachability* from `$lib/services/reachability.ts` — an active probe of the unauthenticated health endpoint, not `navigator.onLine`, so it stays correct on a captive/dead network that lies about being online. It re-probes on the browser `online` event and on foregrounding, and trusts `offline` as an immediate negative. A probe that fails while `navigator.onLine` is *still true* — typically the mobile radio still waking as the app foregrounds — is not trusted on its own: it opens a short confirm window (`classifyReachabilityChange` in `$lib/utils/reachabilityTransition.ts`) that keeps re-probing for `OFFLINE_CONFIRM_WINDOW_MS` and only commits to the offline banner if none succeed. Meanwhile the app stays "online", so a transient reconnect surfaces the SSE client's honest "Восстанавливаем связь…" strip instead of a premature "Нет связи с сервером" (the transient-fault "let it self-correct before alarming" rule). It polls (3s → 30s backoff) only once actually offline so the banner clears on its own; on recovery it runs a debounced `invalidateAll()` so pages drop their stale copies. `ConnectionBanner` (and the `ErrorState` offline page) shows the strip from it, distinct from the SSE `EventsClient` reconnect state. The banner is designed not to be distracting on flaky cellular: it waits `RECOVERING_GRACE_MS` (8s) before showing the "reconnecting" strip (so a normal SSE reconnect after foregrounding resolves before the user sees anything), enforces a `MIN_DISPLAY_MS` (4s) minimum once shown (so it never flashes on and off), and slides in/out instead of popping. When the server is unreachable it reads `reachability.deviceOnline` (a reactive `navigator.onLine`) to word the state honestly: a trustworthy-negative `navigator.onLine === false` is "Нет интернета" (the device's own connection), otherwise "Нет связи с сервером" (device online, API/captive/VPN unreachable) — never blaming the user's internet for a server outage. `getEventsClient()` returns a non-nullable client — the root layout always constructs one — so subscribe with `eventsClient.on(...)`, not `?.on(...)`. `EventsClient` also runs a liveness watchdog: the backend emits a named `ping` event on stream silence, and the client reconnects if nothing arrives for `HEARTBEAT_TIMEOUT_MS` (see "Realtime (SSE)" in [backend.md](backend.md)). Its reconnect policy never gives up outright — after `MAX_RECONNECT_ATTEMPTS` fast retries it shows the "Соединение потеряно" banner but keeps dialing every `FAILED_RETRY_INTERVAL_MS`, because a stream that breaks while the backend stays reachable produces no reachability transition for the other recovery paths to hook.

---

## 3. Styling & Custom UI Rules

* **Tailwind CSS v4**: Theme styling is configured directly in `frontend/src/app.css`. Avoid adding Tailwind v3 style configurations or tailwind.config files.
* **Component Preference**: Always prioritize the vendored shadcn-svelte components in `$lib/components/ui/` over writing custom elements. They live in the repo as source, so add a missing one with the CLI (`pnpm dlx shadcn-svelte@latest add <name>`) rather than hand-rolling — load the `shadcn-svelte` skill first. Compose them (`Card` + `Field` + `Input`), reach for built-in variants (`variant="outline"`, `size="sm"`) before custom classes, and use semantic tokens for colour. Forms use `Field.FieldGroup` + `Field.Field` (label, control, `Field.FieldError`/`Field.FieldDescription`) — never a raw `div` + `Label` + `<p>`.
* **Icons**: Use `@lucide/svelte` (shadcn's configured `iconLibrary`, set in `components.json`) as the single UI icon set — don't add a second general-purpose icon pack (Heroicons, Tabler, etc.); pick the closest Lucide glyph instead. The one exception is brand logos (Telegram, TikTok, VK, and framework marks), which come from `@iconify-json/simple-icons` via `~icons/simple-icons/*` — those official marks have no Lucide equivalent. An icon inside a `<Button>` carries `data-icon="inline-start"` / `inline-end` (the button owns its size and spacing via CSS) — never a manual `size-*` or `me-*`/`mr-*`; the same applies to a `Spinner` swapped in for a loading state. Add icons only when they improve navigation or scanning.

### Typography Scale

Two fonts are defined in `app.css`: `font-sans` (Inter, body text) and `font-display` (Unbounded, hero headings and countdown numerics only). Apply sizes by role:

| Role | Classes | Notes |
|---|---|---|
| Hero heading | `font-display text-2xl sm:text-3xl lg:text-4xl font-bold leading-tight` | `font-display` here only |
| Page heading | `text-lg sm:text-xl font-semibold leading-tight` | The page title rendered in `AppNavbar` (see "Page titles" below) |
| Card/section heading | `text-base sm:text-lg font-semibold leading-snug` | h2/h3 inside cards |
| Body paragraph | `text-sm sm:text-base leading-relaxed` | Default for descriptive text |
| Secondary/helper | `text-xs sm:text-sm leading-relaxed` | Short helper lines next to controls |
| Label/metadata | `text-xs leading-none font-medium` | Single-line only — timestamps, badges, tags |

**Rules:**
* `text-sm` (14px) is the minimum for any multi-line paragraph.
* `text-xs` is for labels, timestamps, and single-line chips — never for multi-sentence body text.
* Never use arbitrary sizes (`text-[10px]`, `text-[0.6rem]`).
* Always add `sm:` responsive upgrade on headings.
* Body text: `leading-relaxed`. Headings: `leading-tight`.
* Countdown/timer numerics (the `font-display` case): add `tabular-nums` so digit-width stays fixed and the layout never jitters as numbers tick.

### Border-Radius Scale

Three tiers — pick by element role:

| Tier | Class | Use for |
|---|---|---|
| Outer | `rounded-2xl` | Large feature/settings/error cards, modals, sheet containers (`ProfileCardShell`, `HeroCard`, error card, etc.) |
| Inner | `rounded-xl` | Standard content & list cards (voting, notifications, schedule-changes feed — the centralized Card default), icon containers, social/chip buttons, dropdown popovers, pill-shaped elements |
| Sub-group | `rounded-lg` | Sections/rows inside a card, toasts, small interactive elements (icon buttons) |
| Circular | `rounded-full` | Avatars, dot indicators, step-number badges |

**Rules:**
* These tiers govern **your own** layout and custom markup. The vendored `ui/` components carry their own `--radius`-derived radii (e.g. `button.svelte`'s `rounded-md`) — leave those alone; don't override a component to force it onto a tier.
* In custom markup, never use `rounded-sm`, `rounded-md`, or bare `rounded` — they have no role in this scale.
* `rounded-2xl` on the outermost container, `rounded-lg` on inner borders/rows inside it.

### Component defaults live in the component source (don't re-specify them)

shadcn-svelte components are **vendored into the repo as source** under `$lib/components/ui/` — there is no `ThemeProvider` and no central theme object. Each component owns its base classes, usually through a `tv()` (`tailwind-variants`) block at the top of its file (see `button.svelte`, `badge.svelte`). Colour, radius and spacing come from the CSS variables in `src/app.css`, and `cn()` (clsx + `tailwind-merge`) lets a call site's `class` override any base class it needs to — the consumer's `class` is merged *after* the base, so it wins.

**Standing rule:** change an app-wide default in **one** place — the component's own source (its `tv()` base) or the shared token in `app.css` — never by repeating the same override on every instance. `class` on an instance is for *layout* (width, margin, grid placement) and genuine one-off deviations, not for re-setting a colour or radius the component already carries.

Where the app-wide knobs live:

| Knob | Source of truth |
|---|---|
| Radius scale | `--radius` in `src/app.css` (`--radius-sm/md/lg/xl` derive from it); components read it as `rounded-md`/`rounded-lg`/`rounded-xl` |
| Semantic colours | the `--background`/`--foreground`/`--card`/`--muted`/`--primary`/… tokens in `src/app.css` (`:root` + `.dark`), exposed as `bg-*`/`text-*` utilities. `--primary` is wired to the watermelon brand and is mode-aware, so `bg-primary`/`text-primary` are on-brand with **no** `dark:` needed (see Dark Mode) |
| Brand palette | the `--color-primary-*` / `--color-secondary-*` watermelon scales in `@theme`, used directly as `bg-primary-600` / `text-primary-400`; the semantic `--primary` points into this scale (`600` light, `400` dark) |
| A component's own base style | the `tv()` block at the top of that component's `.svelte` file in `ui/` |

So:

* A plain instance of a `ui/` component is already correct — **do not** re-add a class it already carries (`rounded-xl` on a `<Button>` is redundant; the button sets its own radius).
* Reach for a **variant** before a class: `variant="outline"`/`"secondary"`/`"destructive"`, `size="sm"`/`"icon"`. Add `class` only for layout or a genuine one-off (`rounded-2xl` on a large feature card, `class="w-full"` on a stacked CTA); it wins via `cn()`/`tailwind-merge`.
* **`Button` sizes meet the 44px touch target in the base**, one rung above the upstream shadcn defaults (see the comment in `button.svelte`): `default`/`icon` are 44px, `sm`/`icon-sm` 40px, `lg`/`icon-lg` 48px — this is a phone-first app, so a plain `<Button>` is already tappable and needs **no** `min-h-11`. `xs`/`icon-xs` stay 24px (WCAG 2.2 AA min) as a deliberate opt-in for dense desktop-only chrome — never a mobile tap target. Existing `class="min-h-11"` on instances is now redundant on a `default` button (harmless) and only still forces the extra 4px on an `sm` one; don't add it to new buttons.
* Need a different app-wide default (say every `Card` flatter)? Edit `card.svelte` once, or the relevant token in `app.css` — one edit, not a sweep across every call site.

### Z-Index Scale

The cross-component ladder is defined once as CSS variables in `app.css`
(`@theme`) and referenced with the Tailwind v4 shorthand `z-(--z-overlay)`.
Tailwind v4 has no named `z-*` utilities, so CSS variables are the idiomatic
single source of truth — **never invent ad-hoc `z-*` values or hardcode a rung
number in a component.**

| Layer | Token / class | Elements |
|---|---|---|
| Base content | `z-0` / auto | In-flow page content |
| In-page sticky | `z-10` – `z-30` | Page-local sticky headers and FABs that must stay *below* chrome (schedule day-tab bar, sub-headers, floating "now" button; overlay-internal controls). Local stacking, **not** tokenized. |
| Top chrome | `z-(--z-chrome)` = 40 | The hide-on-scroll top chrome overlay in `(app)/+layout.svelte` — the `AppNavbar` and connection banner. The layout owns its positioning (an absolute overlay it slides with `top`), not `AppNavbar`. |
| Overlays | `z-(--z-overlay)` = 50 | Mobile bottom nav, toasts, update prompt, skip link, and the portaled shadcn overlays — `Dialog`, and the `Sheet` behind the mobile sidebar (`AppSidebar`), both portaled to `body` |
| Inline modal | `z-(--z-modal)` = 60 | The one inline (non-portaled) modal that must cover the bottom nav from its source position: the fullscreen map viewer (`map/+page.svelte`) |

**Rules:**
* Top chrome stays *below* overlays (`--z-chrome` < `--z-overlay`) so drawers/modals cover it.
* In-page sticky content stays *below* the navbar (`≤ z-30` < 40) — it scrolls under the chrome, never over it. This band is page-local and intentionally left on plain utilities, not tokens.
* **`--z-overlay` is pinned to `50` to match the vendored shadcn overlays.** `Dialog` and `Sheet` (bits-ui) hardcode `z-50` on their content and backdrop and never read the token, so the two must stay numerically equal — change one, change the other, or the portaled surfaces drift off the ladder.
* **Inline vs portaled overlays.** The shadcn `Dialog` and `Sheet` portal to `body` (via bits-ui, after the bottom nav in the DOM) and carry their own `z-50`, so `--z-overlay` already covers the nav via paint order — don't override it. The mobile sidebar is such a `Sheet` (`AppSidebar`), so it needs nothing extra. An overlay rendered **inline** sits at its source position *before* the bottom nav and so needs `--z-modal` to win: the only one is the fullscreen map viewer (`map/+page.svelte`), a hand-rolled overlay that sets **both** its panel and its backdrop to `z-(--z-modal)` — raising only one would leave the nav tappable through it.

The boot splash (`#app-splash`, `z-index: 9999` in `app.html`) sits off this ladder on purpose: it is plain pre-bundle CSS with no access to the token layer, and must cover everything until the root layout mounts and removes it.

### Dark Mode

Theming is wired via `@custom-variant dark` in `app.css` with `.dark` on `<html>` (toggled by the theme service / `mode-watcher`). Project rules:
* **Neutrals ride the semantic tokens.** Surfaces and text use `bg-background`/`bg-card`/`bg-muted`, `text-foreground`/`text-muted-foreground`, `border-border` — one token is already correct in both modes, so they take **no** `dark:` override. Don't reach for raw `gray-*` + a `dark:gray-*` pair; that's the pattern the shadcn migration removed.
* **The semantic `--primary` is brand-wired and mode-aware** — watermelon `--color-primary-600` in light, the lighter `-400` in dark (so `text-primary` clears AA on the dark surface; `--primary-foreground` flips white→dark to stay AA on the fill). Because it switches by mode itself, `bg-primary`/`text-primary` take **no** `dark:` override.
* **Raw brand-scale and status colours stay explicit.** A fixed brand-scale utility used directly (`bg-primary-600`, `text-primary-400`) or a status hue (green/amber/red/blue) is one shade, so it *does* ship a `dark:` variant for every surface — never light-only. Never raw hex.
* "Active/selected" = ring/border + badge, not a bold fill (don't signal by color alone; keep dark text contrast). Cards: `ring-2 ring-green-600 dark:ring-green-500` (ring only, no fill either mode — keeps neutral card + readable green badge; ring shade tuned per mode for 3:1 non-text contrast). Rows: left accent bar (`border-l-4 border-transparent` everywhere, `border-green-500` active — reserves space, no shift) + `bg-green-100 dark:bg-green-900/40`.

Contrast targets and dark-mode mechanics → `accessibility` / `ui-ux-pro-max`.

---

## 4. Mobile Layout & Forms

* **Mobile-First**: Design for narrow mobile screens first. Keep content inside standard layout containers.
* **Bottom Spacing**: Add bottom padding/spacing to pages to prevent fixed mobile bottom navigation tabs from covering active controls.
* **Touch & Inputs**: Generic mobile rules (≥44px touch targets, semantic input `type`, `autocomplete`, password show/hide) live in `ui-ux-pro-max` — apply them; not restated here.
* **Form Submissions**: Disable submit buttons and display inline spinners/loading messages when submissions are in-flight.
* **Feedback Scopes**: Place validation errors inline (directly near the related input field). Reserve toasts for transient action results.
* **Section loading**: Pages block on their `load`, so a section switch keeps the previous page painted until the new one commits. The app shell (`(app)/+layout.svelte`) covers that gap *locally*: after a short delay gate (skip the flash on fast loads) it swaps the content region for a placeholder — a bespoke skeleton that mirrors the incoming layout where the shape is predictable (schedule, voting, notifications), a centred `SectionSpinner` otherwise. It's gated on `navigating.to` (a route change), so an `invalidate()` data refresh — e.g. the schedule's SSE reload — never triggers it.
  * **When a section earns a skeleton.** All three must hold: the load is genuinely slow (blocks on an *uncached* network round-trip, so it can outlast the delay gate — a synchronous or fully-cached load never reveals a loader, so a skeleton there is dead code); the layout is list/card-shaped and predictable; and the section is **public-facing**. Organiser-only tools under `/tools` (users, voting dashboard, festival settings, sync, feedback) block on the network with predictable shapes too, but take the spinner anyway — the perceived-performance win (users read a skeleton as ~9–12% faster) is worth its upkeep for the thousands of attendees on the public tabs, not for a handful of staff who want to get in and out (internal-tools 80/20). Forms take the spinner regardless of audience. When in doubt, spinner: it's the honest choice for an unknown shape, and it costs nothing to maintain.
  * **Keep a skeleton in sync with the page it mirrors.** A skeleton is a second copy of a layout, and its whole job is that the real page drops in without the layout jumping. When you change that page's structure, update its skeleton in the *same* edit — a drifted skeleton reintroduces the jump it exists to prevent, and reads as a bug. If keeping it faithful becomes a burden the section no longer earns, delete it and fall back to the spinner rather than shipping a stale one.

---

## 5. Cleanups & Memory Management

* **Resource Cleanups**: Any connection opened on the client (e.g., event listeners, timers, sockets, streams) must have a clear cleanup path (e.g., returning a cleanup function in `$effect` or using Svelte's `onDestroy`). Prevent memory leaks that accumulate during long sessions or client navigation.

---

## 6. Language & Copy

Russian copy is mandatory for all user-facing text — buttons, placeholders, errors, toasts, empty states (AGENTS.md, "Never"). Keep sentences brief, direct, and actionable; never surface raw backend exceptions or stack traces.

---

## 7. Modal Conventions

Two overlay families, by intent: informational and form modals use the shadcn `Dialog` (`$lib/components/ui/dialog`); confirmations that gate an action use `AlertDialog` (`$lib/components/ui/alert-dialog`) — see "Confirmations" below. Both are driven by `bind:open`. (`Sheet` and `Drawer` are also in the registry — add them with the CLI if a side panel or bottom sheet is ever needed.) Follow these structural rules:

### Structure: Root → Content → Header → Title + Description

Every modal is a `Dialog.Root` + `Dialog.Content`, and the title is a real `Dialog.Title` — **required**, because bits-ui wires it to the dialog for screen readers (never a raw `<h3>`; use `class="sr-only"` to hide it visually). Add a `Dialog.Description` too — also **required**: bits-ui wires it as `aria-describedby` and logs a dev warning when it is absent. When a modal has a natural lead sentence, make *that* the `Dialog.Description`; when the body speaks for itself (a form), add a concise `class="sr-only"` one stating the purpose. Pair the title with a contextual icon and constrain the width on `Content`:

```svelte
<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title class="flex items-center gap-2">
        <SomeIcon class="size-5 text-muted-foreground" />
        Заголовок
      </Dialog.Title>
      <Dialog.Description class="sr-only">Что делает это окно.</Dialog.Description>
    </Dialog.Header>

    <!-- body -->
  </Dialog.Content>
</Dialog.Root>
```

Open state is a `$bindable` prop on the modal component (`bind:open`); for a click-to-open trigger use `Dialog.Trigger`. There is **no `autoclose`** — close explicitly with `onclick={() => (open = false)}` or a `Dialog.Close`.

### Confirmations: AlertDialog

A modal that confirms an action — especially an irreversible one (the schedule broadcasts fire un-recallable pushes) — uses `AlertDialog`, not `Dialog`. It carries `role="alertdialog"` and, unlike `Dialog`, **does not dismiss on an outside click** (bits-ui defaults `interactOutsideBehavior` to `"ignore"`), so the user must make an explicit choice. Focus lands on the first focusable control, so put `AlertDialog.Cancel` before the confirm in the DOM — the safe choice gets focus (WAI-ARIA APG).

Keep the **library's default layout** — centered header, stacked buttons on mobile — deliberately. It reads as a distinct "stop and decide" surface, and matching the app's left-aligned `Dialog` shape would mean fighting the component's `data-size` widths with `!important`. Do not re-add width/alignment overrides.

```svelte
<AlertDialog.Root bind:open>
  <AlertDialog.Content>
    <AlertDialog.Header>
      <AlertDialog.Title class="flex items-center gap-2">…</AlertDialog.Title>
      <AlertDialog.Description>{message}</AlertDialog.Description>
    </AlertDialog.Header>
    <AlertDialog.Footer>
      <AlertDialog.Cancel>Отмена</AlertDialog.Cancel>
      <AlertDialog.Action variant="destructive" onclick={onconfirm}>Удалить</AlertDialog.Action>
    </AlertDialog.Footer>
  </AlertDialog.Content>
</AlertDialog.Root>
```

`AlertDialog.Action` and `AlertDialog.Cancel` **close on click on their own** (via `bind:open`). That suits a confirm whose work is fired by the parent (errors surface as a toast there). But when the modal fires the request itself and must **stay open on failure** to show an in-dialog error, use a plain `<Button>` for the confirm instead of `AlertDialog.Action` — Action would auto-close and drop the message (see `UnsubscribeModal`).

### Footer: non-form Dialog actions

A `Dialog` whose primary content is neither a form nor a confirmation (a picker, an info panel with a CTA — `SubscribeModal`, `VkNotificationsModal`) puts its action row in `Dialog.Footer`, closing explicitly:

```svelte
<Dialog.Footer class="flex flex-row justify-end gap-2">
  <Button type="button" variant="outline" onclick={() => (open = false)}>Отмена</Button>
  <Button type="button" onclick={handleSubmit}>Подписаться</Button>
</Dialog.Footer>
```

### Form modals: submit button stays in body

When the modal contains a real `<form onsubmit={...}>`, put the submit button **inside the form** in the body — not in `Dialog.Footer`. This keeps the button in the form flow. Lay the fields out with `Field.FieldGroup` + `Field.Field` (see "Component Preference" above and the `shadcn-svelte` skill), not raw `div`s.

### Destructive actions

Destructive confirm buttons use `variant="destructive"`. Always pair with a neutral cancel (`variant="outline"`).

### Curly-quote hazard

Never copy-paste class attribute values from rich-text sources. Unicode curly quotes `"` `"` (U+201C/U+201D) look identical to straight quotes but break Svelte's attribute parser, causing cryptic "Object literal" TypeScript errors. Always verify with `cat -A` if type-check fails on a class attribute.

---

## 8. Component Placement & Reusable Inventory

**Placement rule** — decide where a component lives by *who uses it*:

* Used by **one route subtree** → put it in a `components/` subfolder next to the page that uses it (e.g. `routes/(app)/schedule/components/EventCard.svelte`). Always the `components/` subfolder — never loose in the route folder.
* Used across **different route subtrees** → promote it to `frontend/src/lib/components/` (e.g. `SectionIntro`, `SkipLink`, `EmptyState`). The reusable UI primitives themselves (`Button`, `Dialog`, `Field`, …) are the vendored shadcn set in `frontend/src/lib/components/ui/` — don't hand-roll a component that already has a `ui/` equivalent.
* App-shell pieces used only once (navbar/sidebar/banner) stay colocated under `routes/(app)/components/` — single-use does **not** justify `lib/`.

**Module placement (`.ts` / `.svelte.ts`)** — the same *who-uses-it* test, plus a *what-kind* test. SvelteKit itself prescribes only `$lib` and `$lib/server`; the `utils/` vs `services/` split is our convention, so its value is entirely in keeping it consistent:

* **Pure, stateless helpers** (`.ts`) — formatting, parsing, grouping, a `fetch` wrapper. Shared across route subtrees → `$lib/utils/`. Used by exactly **one** route subtree → colocate next to its consumer (beside `+page.svelte`, or in that route's `components/` when a component is the only caller), so `$lib/utils/` stays the genuinely cross-cutting helpers. `push.ts` (only `PushNotificationsCard`) and `scheduleGrouping.ts` (only the schedule page) live in their routes for this reason.
* **Stateful modules** (`.svelte.ts`, holding `$state`/runes) → `$lib/services/`: either an app-wide singleton (`events`, `offline`, `theme`, `toasts`) or a reusable class instantiated per consumer (`CaptchaGate`, `ResendCooldown`, `PaginatedFeed`). The `.svelte.ts` extension *is* the signal that a module is stateful — never leave one in `utils/`, which reads as pure functions.
* A module that a **shared `lib/` module** imports must stay in `lib/` — a route cannot own a dependency of `lib/components/` or `lib/services/` (e.g. `feed.ts`, `smartcaptcha.ts`, `safeStorage.ts`), even when only one route ultimately renders it.
* Whatever the folder: only `export` what is consumed outside the file, and delete unused exports rather than letting them accumulate.

### When to split a large component

Line count is a *smell*, not a threshold — never split to hit a number. Split when a file carries more than one responsibility or repeats a block; leave a long-but-cohesive file whole. The generic case *for* splitting (single responsibility, don't-repeat-yourself) lives in `svelte-core-bestpractices` — load that. What this repo pins is **where each kind of extraction goes**, so a split lands in the conventional shape instead of a bespoke one:

* **Pure logic** (grouping, formatting, parsing, filtering) → a plain function in a `.ts` module with a colocated `*.test.ts`, placed per the module-placement rule above (`$lib/utils/` if shared, colocated beside the route if single-use — as `scheduleGrouping.ts` is). Keep it a `.ts`, not `.svelte.ts`, unless it genuinely needs runes — a pure function is testable in the node-only Vitest env (DOM is out of scope, ADR-0011). Moving logic out of a `.svelte` file is usually the highest-value split: it shrinks the component *and* buys a test.
* **A repeated markup block** (≥2 near-identical instances, like the Telegram/VK rows that became `SocialConnectionRow`) → a component in the folder the placement rule above dictates. Parameterise the differences with props, and pass variant markup as a `{#snippet}` prop (e.g. an `icon` snippet) rather than a `boolean`-per-shape.
* **Repeated markup used only inside one component** → a local `{#snippet}`, *not* a new file. A file earns its own module only when something else renders it.
* **A self-contained dialog** → its own component, mounted behind `{#if open}` where always-mounting would cost real instances (see `EventCard`'s modals). An extracted modal keeps the §7 conventions.
* **A base style repeated on 3+ instances of a `ui/` component** → the component's own `tv()` base or an `app.css` token (§3), *not* a wrapper component — that's a theming change, not a new abstraction.

Two guardrails on the result:

* **Give the child a real boundary.** Pass only what it needs; it may own its own *local* UI state (a confirm/loading flag, like `SocialConnectionRow`), but never request- or user-scoped state in a way that survives navigation (§1). Hand the actual work back to the parent through a callback prop (`onUnlink`, `onSuccess`) so API/domain knowledge stays with the owner.
* **Don't shatter a cohesive state machine.** A long class like `EventsClient` (`events.svelte.ts`) is length driven by interlocking timer state and constraint comments, not duplication — splitting it would fragment one machine across files. Leave it.

A split that changes rendered layout is not done until you've *seen* it render — spin up a throwaway `routes/` page, screenshot each state (including the in-flight ones), then delete the harness. This mirrors the project constraint on verifying Jinja templates by rendering; a refactor that "should be identical" still has to be shown identical.

Before writing any new component, check existing items in `frontend/src/lib/components/`:
* **Page titles**: The screen title lives in the top `AppNavbar`, not in the page body. Each page sets it by returning `title` from its `load` (`page.data.title`); `AppNavbar` renders it as the page `<h1>`. For optional intro text or extra context below the navbar, use `$lib/components/SectionIntro.svelte` (description + children, no title).
* **Toasts**: Trigger toasts through `$lib/services/toasts.svelte.ts` (`getToastService()` for the context instance): `add(message, type)` for status feedback, `error(err)` for a mapped API error, `push(notification)` for an inbound SSE notification. The service wraps [`svelte-sonner`](https://svelte-sonner.vercel.app/)'s `toast()`; toasts render through the `Sonner` wrapper (`$lib/components/ui/sonner`, theme-aware, Lucide status icons) mounted once as `<Toaster />` in the root `+layout.svelte`. `push` dedupes by notification id (`#seenPushIds`) and strips the notification's HTML to plain text for the toast description. Don't hand-roll toast markup — go through the service.
* **Notification bodies**: A notification `body` arrives as a pre-sanitized, safe HTML subset (the backend's `HtmlSanitizer` is the single source of truth — see [backend.md](backend.md)). Render it with `{@html notification.body}` in `NotificationListItem.svelte`, keeping `whitespace-pre-line` so the stored `\n` line breaks show. The push **toast** shows the same body as *plain text* — the toast service strips its tags before handing it to `svelte-sonner`, whose description is not HTML. The notification `title` is plain text — render it with normal `{title}` interpolation. Do **not** add a client-side sanitizer or `{@html}` any other API field.
* **Page Containers**: Match the spacing/layout patterns established in `frontend/src/routes/(app)/+layout.svelte`.
* **Captcha**: `$lib/components/CaptchaWidget.svelte` wraps the Yandex SmartCaptcha widget in invisible mode (loaded via `$lib/utils/smartcaptcha.ts`). It renders nothing unless `PUBLIC_SMARTCAPTCHA_CLIENT_KEY` is set, so callers must gate their submit logic on the exported `captchaEnabled` flag and pass the bound `token` to the API. Invisible mode mints a token only after `execute()`, so callers bind `execute` and call it when submitting; the bound `reset` fetches a fresh single-use token for the next request. Used on the login-code request and resend. Yandex (rather than Cloudflare Turnstile) because Cloudflare is often throttled in Russia — see [docs/adr/](adr/README.md).

---

## 9. Accessibility

Project a11y bindings — keep wired, don't regress:

* **Skip link**: `$lib/components/SkipLink.svelte` is wired in `(app)/+layout.svelte` and targets `#main-content`. Keep both the link and the target id.
* **Focus on route**: the main scroll region carries the `#main-content` id and is focusable (`tabindex="-1"` + `focus-visible` ring) — keyboard/screen-reader users land in content after navigation.
* **Toast a11y**: `svelte-sonner` owns the toast region's ARIA (`aria-live`, roles) and does not steal focus. Trigger toasts through the toast service (§8) rather than hand-rolling toast markup, so that contract holds.
* **Reduced motion**: a global `@media (prefers-reduced-motion: reduce)` rule in `app.css` near-instantly finishes all CSS animations/transitions and disables `scroll-smooth`. CSS-only motion is covered automatically. JS-driven Svelte transitions are **not** affected by that rule — gate them on `prefersReducedMotion.current` from `svelte/motion` instead (see the `HeroCard` countdown; `svelte-sonner` manages its own toast motion).

Everything generic — contrast ratios, keyboard/tab order, `aria-label` on icon-only buttons, heading hierarchy, color-not-sole-signal — lives in `ui-ux-pro-max`. Load it; don't restate here.

---

## 10. Loading, Empty & Error States

Generic patterns (skeletons for >~300ms loads, empty-state layouts, error-recovery affordances, toast auto-dismiss timing) → `ui-ux-pro-max`. Project bindings only, and they already live elsewhere:
* Copy is Russian; never surface raw backend exceptions — §6.
* Toasts are for action results, not field validation — §4 (Feedback Scopes).

---

## 11. Linting, Formatting & Imports

Stock SvelteKit flat-config tooling (`frontend/eslint.config.js`, `frontend/.prettierrc`); run via `just frontend-lint` (Prettier `--check` + ESLint); auto-format with `pnpm --dir frontend format`.

* **Prettier** owns formatting (tabs, single quotes, `printWidth` 100, `endOfLine` `lf`). `prettier-plugin-svelte` formats `.svelte`; `prettier-plugin-tailwindcss` sorts class lists against `src/app.css`. `eslint-config-prettier` disables conflicting ESLint formatting rules — don't re-add them.
* **Editor baseline**: the repo-root `.editorconfig` mirrors these per tree (frontend tabs/width 2, Python 4-space/88-col, YAML 2-space) and pins `end_of_line = lf`, so editors match the formatters before a commit. `.gitattributes` enforces LF in the repo itself.
* **Import order is autofixed by ESLint**, not Prettier — `eslint-plugin-perfectionist` (`sort-imports` / `sort-named-imports` / `sort-exports` / `sort-named-exports`, `type: 'natural'`). Works inside `.svelte` `<script>` via the Svelte parser. Don't hand-order imports; `eslint --fix` (or save-on-fix in editor) handles it. We deliberately enable only the import/export rules, **not** perfectionist's full `recommended-*` preset, to avoid reordering object keys, union members and JSX/Svelte attributes repo-wide.
* **Type-only imports** use a separate `import type` — `@typescript-eslint/consistent-type-imports` (autofix). Required because `verbatimModuleSyntax` is on (a value import of a type would emit a broken runtime import).
* **Unused bindings**: prefix with `_` (`argsIgnorePattern`/`varsIgnorePattern`/`caughtErrorsIgnorePattern` = `^_`) to intentionally keep an unused param/var/catch binding without a lint error.
* **Type-aware rules** (`typescript-eslint` `recommendedTypeChecked`) are **not** enabled yet — only the syntactic `recommended` preset runs. Adding them is deferred (needs `projectService` wiring for `.ts`, a service-worker carve-out, and a cleanup pass for ~24 pre-existing Promise/`any`-safety findings).
