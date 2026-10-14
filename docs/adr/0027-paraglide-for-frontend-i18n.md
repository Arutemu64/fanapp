# ADR-0027: Paraglide JS for frontend i18n, with client-side locale and reload on switch

- **Status:** Accepted
- **Date:** 2026-10-14
- **Deciders:** project maintainers

## Context

The frontend shipped Russian-only, with every string written inline in
components and `.ts` modules. English-speaking guests and the organizers' foreign
guests need the same screens in English, and a second language makes inline text
unmaintainable: no way to see what is untranslated, plurals hand-rolled per call
site (`pluralize()`), no type safety on keys.

The app is a client-rendered SPA (`ssr = false`, `adapter-static`, one `200.html`
shell served by NGINX for every route; ADR-0001's topology). There is no server to
read a cookie or `Accept-Language`, and URL-prefixed locales (`/en/schedule`)
would fork every route, the service worker's precache list and every
`resolve()`-built link.

## Decision

We will use [Paraglide JS](https://paraglidejs.com) 2.x (`@inlang/paraglide-js`).

- Messages live in `frontend/messages/{ru,en}.json`, Russian as the base locale,
  compiled by the Vite plugin into `src/lib/paraglide/` (gitignored). Components
  call `m.key()`; each key is a tree-shaken function with typed parameters.
- Locale strategy is `['localStorage', 'baseLocale']`: an explicit choice made in
  the profile hub, Russian otherwise. We deliberately do **not** add
  `preferredLanguage`: the audience is a Russian convention, and a Russian reader
  whose browser is set to English should not be switched without asking.
- `setLocale()` keeps its default of reloading the page. Messages stay plain
  function calls (no reactive state), and module-level `Intl` formatters and
  lookup tables stay correct because the locale cannot change within a page load.
- The inlang message-format plugin is installed from npm
  (`@inlang/plugin-message-format`) and referenced by a local path in
  `project.inlang/settings.json`, so builds fetch no code from a CDN and the
  version is pinned by the lockfile and its release-age cooldown.
- Plurals are `plural`-selector variant messages (CLDR via `Intl.PluralRules`),
  replacing the `pluralize()` helper.

## Consequences

- Every new string is a key in both catalogs; a missing key or a mismatched
  placeholder is a review finding, and an unreferenced key shows up in a diff of
  the catalogs. Typed `m.*` references make a deleted key a compile error.
- The generated directory must exist before `svelte-check` and ESLint: `check`,
  `lint:eslint` and `prepare` compile it first (`pnpm paraglide`).
- Switching language costs a reload — acceptable for a setting changed once —
  and makes `setLocale(…, { reload: false })` off-limits without revisiting the
  module-level constants.
- Out of scope, by design: text the backend produces (emails, notification
  bodies, schedule titles from the organizers' spreadsheet), the service worker's
  push fallback (no `localStorage` in a worker), `manifest.json` and the static
  Open Graph tags in `app.html` (read by crawlers and the OS, not the app). A
  later decision to localize backend text needs a locale on the user record and
  would be its own ADR.

## Alternatives considered

- **`svelte-i18n` / `typesafe-i18n` / `i18next`:** runtime message parsing or
  stores, a larger bundle, and no per-message tree-shaking. Paraglide's compiled
  functions ship only the messages a page imports.
- **URL-prefixed locales** (Paraglide's default `url` strategy): the right choice
  for SEO on a content site; here it multiplies routes, SW precache entries and
  links for no gain, because the app is behind a login and indexed nowhere.
- **Cookie strategy:** nothing server-side reads it.
- **Reactive locale switching without reload:** possible with
  `setLocale(…, { reload: false })` plus reactive wrappers, but every static
  table and formatter would need re-deriving; not worth it for a rarely changed
  setting.
