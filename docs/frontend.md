# Frontend & SvelteKit Guidelines

This document outlines the codebase-specific constraints, SvelteKit SSR rules, styling standards, layout designs, and custom component inventory.

> [!IMPORTANT]
> **Required Svelte Skills**: Svelte 5 reactivity syntax, runes usage, event handling conventions, and snippet patterns are fully documented in workspace skills. Whenever editing Svelte components (`.svelte`) or Svelte modules (`.svelte.ts`/`.svelte.js`), you **MUST** load and apply these skills:
> 1. `svelte-code-writer`
> 2. `svelte-core-bestpractices`
>
> Refer to those skills for core syntax and best practices; do not duplicate them here.

> [!NOTE]
> **Scope of this doc**: only FAN FAN–specific decisions and bindings live here — chosen scales, tokens, component wiring, conventions. Generic best-practice (accessibility, UX, responsive + dark-mode mechanics) lives in the `ui-ux-pro-max`, `tailwind-css-patterns`, and `svelte-core-bestpractices` skills — load those. **Rule of thumb**: if a skill that has never seen this repo could state a rule, it belongs in the skill, not here.

---

## 1. Client Rendering (SPA) & State Isolation

The app is a **client-rendered SPA**: `export const ssr = false` lives in the root `src/routes/+layout.ts`, so pages render only in the browser — there is no server render. The app is built with `@sveltejs/adapter-static` (SPA mode, `fallback: '200.html'`) into a static bundle, served in production by a small **NGINX** container (`frontend/nginx.conf`) that falls back to `200.html` for every unknown route so the client router can take over. There is no Node server.

* **Build-time `PUBLIC_*` env**: Because nothing runs at runtime, the app reads its public env via `$env/static/public` (not `$env/dynamic/public`), so `PUBLIC_API_URL`, `PUBLIC_VAPID_KEY`, `PUBLIC_SENTRY_DSN` and `PUBLIC_TURNSTILE_SITE_KEY` are **baked into the bundle at build time**. Changing one means rebuilding the image — the server's `.env` cannot inject them into a prebuilt image. In CI they come from GitHub repository variables (see `.github/workflows/docker-publish.yml`); for local `just run-dev`/`run-prod` they come from the root `.env` build args. Every referenced `PUBLIC_*` var must exist (even if empty) at build time, or the build fails.
* **Relative API base (`PUBLIC_API_URL=/api`)**: The default is a **relative** path, not an absolute URL. The SPA and API are served same-origin (Caddy routes `/api*` to the backend), so a relative base resolves against whatever origin serves the app — keeping the bundle (and the prebuilt GHCR image) domain-agnostic, so the same build runs on any domain with no rebuild. Browser consumers (`openapi-fetch`, the reachability probe, the SSE `EventSource`, the Telegram OAuth `href`s) resolve it against `location.origin`; the service worker resolves it against its own origin (`new URL(PUBLIC_API_URL, self.location.origin)`) since `new URL` throws on a bare path. In dev the frontend and backend are different origins, so `frontend/vite.config.ts` proxies `/api` to the backend (`VITE_API_PROXY_TARGET`, default `http://localhost:8000`; `http://api:8000` in the Docker dev overlay) and strips the `/api` prefix to mirror Caddy. Set an absolute URL only for the opt-in split-origin deployment (then also set `WEB__CORS_ALLOW_ORIGINS`).

* **No SSR**: Browser globals (`window`, `document`, `localStorage`) are safe in component and module code, since nothing runs on the server. (Still guard with `browser` from `$app/environment` only if a module also runs under non-browser tooling, e.g. tests.)
* **Strict State Isolation**: Do not store user/session state in global/module-level variables, legacy stores, or reactive singletons. In a SPA a module singleton persists across client-side navigations and across login/logout — scoping avoids stale data bleeding between sessions.
* **Context API for Shared State**: For state shared across Svelte 5 components, keep logic in classes with `$state` fields instanced per component. Use Svelte 5's type-safe `createContext` utility (rather than global stores or raw module variables) to scope state to the component tree.
* **Effect avoidance**: Prefer (in order) event handlers, `{@attach ...}` for external libs, `<svelte:window>`/`<svelte:document>` for global listeners, and `createSubscriber` for external sources; reach for `$effect` only as a last resort. See `svelte-core-bestpractices`.

---

## 2. Data Loading & SvelteKit Integration

* **Data Fetching boundaries**: Move first-render data requirements into SvelteKit layout or page `load` functions. All loads are **universal** (`+page.ts`/`+layout.ts`) — there are no `.server.ts` loads in a SPA.
* **Pass the load `fetch`**: Always pass the SvelteKit-provided `fetch` (from load functions) inside the request options block of your client calls (e.g., `client.GET('/route', { fetch })`). It gives request deduplication, relative-URL resolution, and integration with `invalidate()`. The session cookie is carried automatically by the browser (the API client uses `credentials: 'include'`).
* **Typed `data`**: Always type page/layout props with the generated `PageProps`/`LayoutProps` (or `PageData`/`LayoutData`) from `./$types`. Never leave `$props()` untyped — typed `data` is what catches load/page mismatches at check time.

### Access Control (don't duplicate guards)

Guards run client-side in **universal `load`** functions (these are UX redirects only — the backend enforces real auth on every endpoint):

* The root `+layout.ts` fetches the current user from `/me/` and returns `user`, so it flows down to **every** page. Do not re-return `user` from a nested layout — it is already inherited.
* Route-group layouts gate by membership: `(app)/(protected)/+layout.ts` requires a logged-in user (else → `/login`); `(auth)/+layout.ts` is guests-only (else → `/`). Putting a route inside the group is the guard — do **not** re-check `user` in that route's `load`.
* A nested `+layout.ts` should only add checks the group can't express — e.g. a finer-grained `error(403, …)`. The whole `org/` section is already gated by `org/+layout.ts` via the `canManageSettings`/`canImportSchedule`/`canSendNotifications` permission helpers; never re-check organizer access inside individual org pages.

### PWA & Offline Support

The app is an installable PWA: `static/manifest.json` (icons, standalone display) + a service worker (`src/service-worker.ts`, the SvelteKit `$service-worker` template) that SvelteKit auto-registers in production. The SW precaches the app shell (`build` + everything in `static/`; the venue maps live in `$lib/assets/map` and ride `build` as content-hashed assets, so they work offline too), handles web-push, and **never caches API requests** — the backend is served under a path on the *same* origin (e.g. `/api`, derived from `PUBLIC_API_URL`), so the SW excludes it by path (`isApiRequest`), not by origin; its user-specific data is cached by the app layer, never the SW. `UpdatePrompt.svelte` (mounted in the root layout) surfaces a "new version" banner when a fresh build is waiting and reloads on `controllerchange`; the SW activates the waiting worker only when it receives a `'skipWaiting'` message.

* **Read-only offline data**: For pages worth viewing offline (schedule, notifications, profile), wrap the load in `fetchWithCache` (`$lib/utils/offlineCache.ts`, IndexedDB via `idb-keyval`). It encapsulates the whole flow — skip the request when `isReachable()` is false, bound the fetch with `FIRST_PAINT_TIMEOUT_MS`, update reachability, persist the fresh copy, and fall back to the cache on error/timeout. Pass a `key` and a `fetcher({ signal })` that returns the value to cache, or `undefined` to fall back; it returns `{ data, stale, cachedAt }`. Render `StaleDataNotice` when `stale` and pass `cachedAt` (epoch millis of when the shown copy was persisted) so the notice shows a "synced at" time via `formatSyncedAt`. Entries are stored as a `{ value, cachedAt }` envelope; entries written before this migration are read as bare values with no timestamp and upgraded on the next online write. Key the cache per user (`schedule:${user.id}`) so one device's account never serves another's data. The low-level `readCache`/`writeCache`/`clearCache` helpers remain for non-`load` callers. Mutations (votes, settings) stay online-only.
* **Complete-miss handling (offline vs. failure)**: When `data` is `undefined` (nothing cached), branch on `isReachable()`: if offline, return a soft empty state with an `offlineMiss: true` flag so the page renders a calm inline "недоступно офлайн" message and keeps the app shell/bottom nav usable; only a *reachable* failure throws `error(503, …)`. The page suppresses `StaleDataNotice` when `offlineMiss` (there is no saved copy to caveat) and swaps the empty-state copy. This is more reliable than `ErrorState`'s render-time offline reframing, which can lag a beat behind the load's reachability verdict.
* **Identity caching contract (`me:user` in `+layout.ts`)**: the `/me` fetcher distinguishes three outcomes so a transient error can't silently log a user out and orphan their per-user caches: `200` → cache the user; explicit **`401`/`403`** → authoritative logout: cache `null` **and** `clearCache()` (mirrors `AppNavbar.handleLogout`, so no per-user entries linger for the next account); any **other** error (`5xx`, parse, empty) → return `undefined` so the last-good cached user is kept. Offline, `/me` throws and the cached user is served unchanged. Because identity only drops on a real logout/expiry (both of which clear the cache), per-user keys never go stale against the live session.
* **Warming a cache before first visit**: `warmCache` (`$lib/utils/offlineCache.ts`) proactively seeds a `fetchWithCache` entry for a page the user hasn't opened, so it works offline from the first run. The root `+layout.ts` warms the schedule on the first online boot. It is fire-and-forget (never `await`ed in a `load`, so it can't block first paint), a no-op when offline or already cached, and never refetches once warmed — the page's own `load` + the `schedule_updated` SSE event keep it fresh after that.
* **Connectivity vs. stream health**: `OfflineService` (`$lib/services/offline.svelte.ts`) tracks `navigator.onLine` via `createSubscriber`; `ConnectionBanner` shows the offline strip from it, distinct from the SSE `EventsClient` reconnect state.

---

## 3. Styling & Custom UI Rules

* **Tailwind CSS v4**: Theme styling is configured directly in `frontend/src/app.css`. Avoid adding Tailwind v3 style configurations or tailwind.config files.
* **Component Preference**: Always prioritize official Flowbite-Svelte components instead of writing custom elements.
* **Icons**: Use `flowbite-svelte-icons` for iconography. Add icons only when they improve navigation or scanning.

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

Contrast targets and dark-mode mechanics → `tailwind-css-patterns` / `ui-ux-pro-max`.

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

Russian copy is mandatory for all user-facing text — buttons, placeholders, errors, toasts, empty states (AGENTS.md #1). Keep sentences brief, direct, and actionable; never surface raw backend exceptions or stack traces.

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
* **Toasts**: Trigger alerts via `$lib/services/toasts.svelte.ts` and display them with `$lib/components/ToastContainer.svelte`.
* **Notification bodies**: A notification `body` arrives as a pre-sanitized, safe HTML subset (the backend's `HtmlSanitizer` is the single source of truth — see [backend.md](backend.md)). Render it with `{@html notification.body}` (in `ToastContainer.svelte` and `NotificationListItem.svelte`), keeping `whitespace-pre-line` so the stored `\n` line breaks show. The notification `title` is plain text — render it with normal `{title}` interpolation. Do **not** add a client-side sanitizer or `{@html}` any other API field.
* **Page Containers**: Match the spacing/layout patterns established in `frontend/src/routes/(app)/+layout.svelte`.
* **Captcha**: `$lib/components/CaptchaWidget.svelte` wraps the Cloudflare Turnstile widget. It renders nothing unless `PUBLIC_TURNSTILE_SITE_KEY` is set, so callers must gate their submit logic on the exported `captchaEnabled` flag and pass the bound `token` to the API. Used on the login-code request and resend.

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
