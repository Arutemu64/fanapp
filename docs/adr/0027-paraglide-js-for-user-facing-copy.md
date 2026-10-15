# ADR-0027: Paraglide JS for user-facing copy

- **Status:** Accepted
- **Date:** 2026-10-15
- **Deciders:** project maintainers

## Context

Russian copy was ~980 string literals spread over ~125 components, services and
utilities. Reviewing wording meant grepping the codebase; the same text was
written out several times (`Отмена` eight times, `Голосование` six); three-form
plurals were hand-assembled with a `pluralize()` helper; and nothing checked a
string against the editorial policy ([.agents/redpolitika.md](../../.agents/redpolitika.md))
as a set. The app ships one locale and has no plan for a second.

## Decision

We will keep all frontend copy in `frontend/messages/ru.json` and compile it
with [Paraglide JS](https://paraglidejs.com) 2.x (`@inlang/paraglide-js`).

- Single locale: `baseLocale: "ru"`, `strategy: ["baseLocale"]`. No URL
  prefixes, cookies or server middleware, which the client-rendered SPA
  (`ssr = false`, adapter-static) neither has nor needs.
- Messages are compiled to one tree-shakable module each in the gitignored
  `src/lib/paraglide/`, so a mistyped key or missing parameter is a type error.
- Plurals are variant messages using `Intl.PluralRules` (CLDR), replacing
  `pluralize()`.
- The inlang message-format plugin is installed from npm and referenced by a
  local path in `project.inlang/settings.json`, not loaded from a CDN: builds
  stay offline-capable and the plugin is covered by the lockfile and the
  7-day `minimumReleaseAge` gate.

## Consequences

Copy can be reviewed and linted as one file. Components import `m` instead of
carrying text. A second locale becomes an additive change, though sentences
split around links would need reworking first (see docs/frontend.md §6).

The service worker imports the messages too (push fallback text) and its
bundle grew by about 4 KB for the Paraglide runtime.

`app.html` and `static/manifest.json` stay literal; they cannot import code.

## Alternatives considered

- **svelte-i18n / typesafe-i18n:** runtime stores or heavier runtime, no
  per-message tree-shaking; Paraglide's compiler approach fits a static SPA.
- **Plain `.ts` constants module:** no plural support and no tooling a second
  locale could reuse.
