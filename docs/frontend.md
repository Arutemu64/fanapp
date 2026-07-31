# Frontend & SvelteKit Guidelines

This document outlines the codebase-specific constraints, SvelteKit SPA rules, styling standards, layout designs, and custom component inventory.

> [!NOTE]
> **Scope of this doc**: only FAN FAN–specific decisions and bindings live here — chosen scales, tokens, component wiring, conventions. Generic best-practice (Svelte 5 runes and event syntax, accessibility, UX, responsive + dark-mode mechanics) lives in the `svelte-code-writer`, `svelte-core-bestpractices`, `ui-ux-pro-max`, `impeccable`, `accessibility` and `core-web-vitals` skills — load those (AGENTS.md, "Load before you edit"). **Rule of thumb**: if a skill that has never seen this repo could state a rule, it belongs in the skill, not here. What only this repo knows belongs *here* — or in a code comment next to the constraint it explains. A `fanfan-*` skill is for the narrow remainder that fits neither: knowledge with no single file to live beside, like the Russian glossary or the migration traps.

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

The app is an installable PWA: `static/manifest.json` (icons, standalone display) + a service worker (`src/service-worker.ts`, the SvelteKit `$service-worker` template) that SvelteKit auto-registers in production. The SW precaches the app shell (`build` + everything in `static/`; the venue maps live in `$lib/assets/map` and ride `build` as content-hashed assets, so they work offline too), handles web-push, and **never caches API requests** — the backend is served under a path on the *same* origin (e.g. `/api`, derived from `PUBLIC_API_URL`), so the SW excludes it by path (`isApiRequest`), not by origin; its user-specific data is cached by the app layer, never the SW. `UpdatePrompt.svelte` (mounted in the root layout) surfaces a "new version" banner when a fresh build is waiting and reloads on `controllerchange`; the SW activates the waiting worker only when it receives a `'skipWaiting'` message. OS integration: the manifest declares `shortcuts` (long-press app-icon menu: Программа/Уведомления/Карта) and `launch_handler: navigate-existing` (links into the installed app reuse the open window instead of spawning a duplicate), and the Badging API mirrors the unread-notification count onto the app icon via `$lib/utils/appBadge.ts` — `NotificationBell` syncs the exact count, logout clears it, and the SW push handler sets a count-less "flag" badge that the bell replaces on next open.

* **Hand-written, not Workbox**: the SW is the SvelteKit `$service-worker` template, deliberately. Don't introduce `workbox-*`, `generateSW` or a `workbox-config.js` — generic PWA guidance assumes them and does not apply here.
* **The fetch handler is inert in `vite dev`** (`build` is empty outside a production build, which the SW uses as its dev signal), because cache-first assumes the immutable versioned shell only a real build produces. So a service-worker change is **not** testable with `just frontend-dev` — verify it with `just run-prod`. The `push`/`notificationclick` handlers do stay registered in dev.
* **`manifest.json`'s `theme_color` duplicates `primary-600`** from `.agents/context/DESIGN.md` (`#d61450`). Change both together.
* **Read-only offline data**: For pages worth viewing offline (schedule, notifications; the profile renders from the cached `/me` identity below), wrap the load in `fetchWithCache` (`$lib/utils/offlineCache.ts`, IndexedDB via `idb-keyval`). It encapsulates the whole flow — skip the request when `isReachable()` is false, bound the fetch with `FIRST_PAINT_TIMEOUT_MS`, update reachability, persist the fresh copy, and fall back to the cache on error/timeout. Pass a `key`, a `scope`, and a `fetcher({ signal })` that returns the value to cache, or `undefined` to fall back; it returns `{ data, stale, cachedAt }`. Render `StaleDataNotice` when `stale` and pass `cachedAt` (epoch millis of when the shown copy was persisted) so the notice shows a "synced at" time via `formatSyncedAt`. Entries are stored as a `{ value, cachedAt }` envelope; entries written before this migration are read as bare values with no timestamp and upgraded on the next online write. Every entry is scoped: `userScope` entries (e.g. `subscriptions:${user.id}`, also keyed per user) are wiped by `clearUserCache` on logout so one device's account never serves another's data; `universalScope` entries (e.g. the public schedule, key `schedule`) are identical for everyone and survive logout. The low-level `readCache`/`writeCache`/`clearUserCache` helpers remain for non-`load` callers. Mutations (votes, settings) stay online-only.
* **Complete-miss handling (offline vs. failure)**: When `data` is `undefined` (nothing cached), branch on `isReachable()`: if offline, return a soft empty state with an `offlineMiss: true` flag so the page renders a calm inline "недоступно офлайн" message and keeps the app shell/bottom nav usable; only a *reachable* failure throws `error(503, …)`. The page suppresses `StaleDataNotice` when `offlineMiss` (there is no saved copy to caveat) and swaps the empty-state copy. This is more reliable than `ErrorState`'s render-time offline reframing, which can lag a beat behind the load's reachability verdict.
* **Identity caching contract (`me:user` in `+layout.ts`)**: the `/me` fetcher distinguishes three outcomes so a transient error can't silently log a user out and orphan their per-user caches: `200` → cache the user; explicit **`401`/`403`** → authoritative logout: cache `null` **and** `clearUserCache()` (mirrors `AppNavbar.handleLogout`, so no per-user entries linger for the next account); any **other** error (`5xx`, parse, empty) → return `undefined` so the last-good cached user is kept. Offline, `/me` throws and the cached user is served unchanged. Because identity only drops on a real logout/expiry (both of which clear the cache), per-user keys never go stale against the live session.
* **Warming a cache before first visit**: `warmCache` (`$lib/utils/offlineCache.ts`) proactively seeds a `fetchWithCache` entry for a page the user hasn't opened, so it works offline from the first run. The root `+layout.ts` warms the schedule on the first online boot. It is fire-and-forget (never `await`ed in a `load`, so it can't block first paint), a no-op when offline or already cached, and never refetches once warmed — the page's own `load` + the `schedule_updated` SSE event keep it fresh after that.
* **Connectivity vs. stream health**: `OfflineService` (`$lib/services/offline.svelte.ts`) exposes reactive *backend reachability* from `$lib/services/reachability.ts` — an active probe of the unauthenticated health endpoint, not `navigator.onLine`, so it stays correct on a captive/dead network that lies about being online. It re-probes on the browser `online` event and on foregrounding, trusts `offline` as an immediate negative, and polls (5s → 30s backoff) only while offline so the banner clears on its own; on recovery it runs a debounced `invalidateAll()` so pages drop their stale copies. `ConnectionBanner` shows the offline strip from it, distinct from the SSE `EventsClient` reconnect state. `getEventsClient()` returns a non-nullable client — the root layout always constructs one — so subscribe with `eventsClient.on(...)`, not `?.on(...)`. `EventsClient` also runs a liveness watchdog: the backend emits a named `ping` event on stream silence, and the client reconnects if nothing arrives for `HEARTBEAT_TIMEOUT_MS` (see "Realtime (SSE)" in [backend.md](backend.md)). Its reconnect policy never gives up outright — after `MAX_RECONNECT_ATTEMPTS` fast retries it shows the "Соединение потеряно" banner but keeps dialing every `FAILED_RETRY_INTERVAL_MS`, because a stream that breaks while the backend stays reachable produces no reachability transition for the other recovery paths to hook.

---

## 3. Styling & Custom UI Rules

* **Tailwind CSS v4**: Theme styling is configured directly in `frontend/src/app.css`. Avoid adding Tailwind v3 style configurations or tailwind.config files.
* **Component Preference**: Always prioritize official Flowbite-Svelte components instead of writing custom elements.
* **Icons**: Use `flowbite-svelte-icons` as the single UI icon set — don't add a second general-purpose icon pack (Lucide, Heroicons, etc.); pick the closest Flowbite equivalent instead. The one exception is brand logos (Telegram, TikTok, VK, and framework marks), which come from `@iconify-json/simple-icons` via `~icons/simple-icons/*` — those official marks have no Flowbite equivalent. Add icons only when they improve navigation or scanning.

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
| Outer | `rounded-2xl` | Page-level cards, modals, sheet containers (`ProfileCardShell`, `HeroCard`, `EventCard` wrappers, etc.) |
| Inner | `rounded-xl` | Icon containers, social/chip buttons, dropdown popovers, pill-shaped elements |
| Sub-group | `rounded-lg` | Sections/rows inside a card, toasts, small interactive elements (icon buttons) |
| Circular | `rounded-full` | Avatars, dot indicators, step-number badges |

**Rules:**
* Never use `rounded-sm`, `rounded-md`, or bare `rounded` — they have no role in this scale.
* `rounded-2xl` on the outermost container, `rounded-lg` on inner borders/rows inside it.

### Z-Index Scale

Keep stacking on this fixed ladder — never invent ad-hoc `z-*` values:

| Layer | Class | Elements |
|---|---|---|
| Base content | `z-0` / auto | In-flow page content |
| Sticky chrome | `z-40` | Top navbar (`AppNavbar`, `sticky top-0`) |
| Overlays | `z-50` | Mobile bottom nav, mobile sidebar drawer, toasts, modals/backdrops |

**Rules:**
* Sticky navbar stays *below* overlays (`z-40` < `z-50`) so drawers/modals cover it.
* Flowbite `<Modal>` manages its own backdrop + `z-50` — don't override it.

### Dark Mode

Theming is wired via `@custom-variant dark` in `app.css` with `.dark` on `<html>`. Project rules:
* Ship a `dark:` variant for every surface — never light-only.
* Use semantic tokens (`primary-*`, `secondary-*`, `gray-*`), never raw hex.
* "Active/selected" = ring/border + badge, not a bold fill (don't signal by color alone; keep dark text contrast). Cards: `ring-2 ring-green-600 dark:ring-green-500` (ring only, no fill either mode — keeps neutral card + readable green badge; ring shade tuned per mode for 3:1 non-text contrast). Rows: left accent bar (`border-l-4 border-transparent` everywhere, `border-green-500` active — reserves space, no shift) + `bg-green-100 dark:bg-green-900/40`.

Contrast targets and dark-mode mechanics → `accessibility` / `ui-ux-pro-max`.

---

## 4. Mobile Layout & Forms

* **Mobile-First**: Design for narrow mobile screens first. Keep content inside standard layout containers.
* **Bottom Spacing**: Add bottom padding/spacing to pages to prevent fixed mobile bottom navigation tabs from covering active controls.
* **Touch & Inputs**: Generic mobile rules (≥44px touch targets, semantic input `type`, `autocomplete`, password show/hide) live in `ui-ux-pro-max` — apply them; not restated here.
* **Form Submissions**: Disable submit buttons and display inline spinners/loading messages when submissions are in-flight.
* **Feedback Scopes**: Place validation errors inline (directly near the related input field). Reserve toasts for transient action results.

---

## 5. Cleanups & Memory Management

* **Resource Cleanups**: Any connection opened on the client (e.g., event listeners, timers, sockets, streams) must have a clear cleanup path (e.g., returning a cleanup function in `$effect` or using Svelte's `onDestroy`). Prevent memory leaks that accumulate during long sessions or client navigation.

---

## 6. Language & Copy

Russian copy is mandatory for all user-facing text — buttons, placeholders, errors, toasts, empty states (AGENTS.md, "Never"). Keep sentences brief, direct, and actionable; never surface raw backend exceptions or stack traces.

---

## 7. Modal Conventions

All modals use Flowbite-Svelte `<Modal bind:open size="sm">`. Follow these structural rules:

### Required: `{#snippet header()}`

Every modal **must** use the `header` snippet — never put a raw `<h3>` inside the modal body. Always pair the title with a contextual icon:

```svelte
<Modal bind:open size="sm">
  {#snippet header()}
    <div class="flex items-center gap-2">
      <SomeIcon class="h-5 w-5 text-gray-500 dark:text-gray-400" />
      <h3 class="text-lg font-bold text-gray-900 dark:text-white">Заголовок</h3>
    </div>
  {/snippet}

  <!-- body -->
</Modal>
```

### Footer snippet: action-only modals

Use `{#snippet footer()}` for modals whose primary content is not a form — confirmation dialogs, single-action prompts. Flowbite renders a top-border separator automatically:

```svelte
{#snippet footer()}
  <Button type="button" color="alternative" onclick={() => (open = false)}>Отмена</Button>
  <Button type="button" color="red" onclick={handleDelete}>Удалить</Button>
{/snippet}
```

### Form modals: submit button stays in body

When the modal contains a real `<form onsubmit={...}>`, put the submit button **inside the form** in the body — not in the footer snippet. This keeps the button as part of the form flow, and the visual separation is intentional (no footer divider).

### Destructive actions

Destructive confirm buttons use `color="red"`. Always pair with a neutral cancel (`color="alternative"` or `color="light"`).

### No `autoclose`

Do not use the deprecated `autoclose` prop. Wire close explicitly: `onclick={() => (open = false)}`.

### Curly-quote hazard

Never copy-paste class attribute values from rich-text sources. Unicode curly quotes `"` `"` (U+201C/U+201D) look identical to straight quotes but break Svelte's attribute parser, causing cryptic "Object literal" TypeScript errors. Always verify with `cat -A` if type-check fails on a class attribute.

---

## 8. Component Placement & Reusable Inventory

**Placement rule** — decide where a component lives by *who uses it*:

* Used by **one route subtree** → put it in a `components/` subfolder next to the page that uses it (e.g. `routes/(app)/schedule/components/EventCard.svelte`). Always the `components/` subfolder — never loose in the route folder.
* Used across **different route subtrees** → promote it to `frontend/src/lib/components/` (e.g. `SectionIntro`, `OtpInput`, `ToastContainer`).
* App-shell pieces used only once (navbar/sidebar/banner) stay colocated under `routes/(app)/components/` — single-use does **not** justify `lib/`.
* `lib/` modules (`utils/`, `services/`, etc.) follow the same spirit: only `export` what is consumed outside the file, and delete unused exports rather than letting them accumulate.

Before writing any new component, check existing items in `frontend/src/lib/components/`:
* **Page titles**: The screen title lives in the top `AppNavbar`, not in the page body. Each page sets it by returning `title` from its `load` (`page.data.title`); `AppNavbar` renders it as the page `<h1>`. For optional intro text or extra context below the navbar, use `$lib/components/SectionIntro.svelte` (description + children, no title).
* **Toasts**: Trigger alerts via `$lib/services/toasts.svelte.ts` and display them with `$lib/components/ToastContainer.svelte`. The service keeps two independent queues so a burst of one category can never evict the other: **status** toasts (action feedback — `add`/`error`) and **push** toasts (inbound SSE notifications — `push`). `ToastContainer` renders them in separate regions — push at the top (like OS notifications), status bottom-centered against the viewport at every width, raised above the mobile bottom nav.
* **Notification bodies**: A notification `body` arrives as a pre-sanitized, safe HTML subset (the backend's `HtmlSanitizer` is the single source of truth — see [backend.md](backend.md)). Render it with `{@html notification.body}` (in `ToastContainer.svelte` and `NotificationListItem.svelte`), keeping `whitespace-pre-line` so the stored `\n` line breaks show. The notification `title` is plain text — render it with normal `{title}` interpolation. Do **not** add a client-side sanitizer or `{@html}` any other API field.
* **Page Containers**: Match the spacing/layout patterns established in `frontend/src/routes/(app)/+layout.svelte`.
* **Captcha**: `$lib/components/CaptchaWidget.svelte` wraps the Yandex SmartCaptcha widget in invisible mode (loaded via `$lib/utils/smartcaptcha.ts`). It renders nothing unless `PUBLIC_SMARTCAPTCHA_CLIENT_KEY` is set, so callers must gate their submit logic on the exported `captchaEnabled` flag and pass the bound `token` to the API. Invisible mode mints a token only after `execute()`, so callers bind `execute` and call it when submitting; the bound `reset` fetches a fresh single-use token for the next request. Used on the login-code request and resend. Yandex (rather than Cloudflare Turnstile) because Cloudflare is often throttled in Russia — see [docs/adr/](adr/README.md).

---

## 9. Accessibility

Project a11y bindings — keep wired, don't regress:

* **Skip link**: `$lib/components/SkipLink.svelte` is wired in `(app)/+layout.svelte` and targets `#main-content`. Keep both the link and the target id.
* **Focus on route**: the main scroll region carries the `#main-content` id and is focusable (`tabindex="-1"` + `focus-visible` ring) — keyboard/screen-reader users land in content after navigation.
* **Toast a11y contract**: `ToastContainer` sets `role="alert"`/`aria-live="assertive"` for errors and `role="status"`/`aria-live="polite"` otherwise, with `aria-atomic`. Match this on any new toast markup; toasts must not steal focus.
* **Reduced motion**: a global `@media (prefers-reduced-motion: reduce)` rule in `app.css` near-instantly finishes all CSS animations/transitions and disables `scroll-smooth`. CSS-only motion is covered automatically. JS-driven Svelte transitions are **not** affected by that rule — gate them on `prefersReducedMotion.current` from `svelte/motion` instead (see `ToastContainer` toast `fly` + swipe-dismiss and `HeroCard` countdown).

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
