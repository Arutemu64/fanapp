# ADR-0028: English localization with a browser-language default

- **Status:** Accepted
- **Date:** 2026-10-15
- **Deciders:** FAN FAN maintainers

## Context

[ADR-0027](0027-paraglide-js-for-user-facing-copy.md) moved the copy into
Paraglide with one locale and said a second would be additive. Visitors from
abroad now need the app too, but the audience is still overwhelmingly Russian.

## Decision

Add `en` next to `ru` (`ru` stays the base locale and the source of the copy).
The language is chosen by a custom client strategy (`custom-appLocale`,
`src/lib/i18n/locale.ts`) in this order: the choice saved in `localStorage`,
then the first language in `navigator.languages` that the app has copy for,
then English. A language switch in the profile writes the saved choice and
reloads.

## Consequences

- A browser with no Russian gets English. Paraglide's built-in
  `preferredLanguage` strategy cannot do this: with `ru` as the base locale it
  falls through to Russian for a German or Japanese browser.
- The built-in `localStorage` strategy is not used either: it reads
  `localStorage` unguarded, and in-app webviews (Telegram's Android webview)
  throw on the access. The custom strategy goes through `safeStorage`.
- A reload on switch keeps module-level `Intl` formatters and message maps
  simple; the cost is one reload on a rare action.
- Every key must exist in both catalogues. Backend emails and notifications
  stay Russian, so a push notification's text can differ from the UI language.
  `app.html` and `manifest.json` stay Russian.

## Alternatives considered

- **`baseLocale: en`:** gives the default for free, but makes English the
  source of truth for copy that is written to a Russian editorial policy.
- **URL prefixes or a cookie:** the SPA has no server to read them, and
  prefixes would change every link the backend and notifications emit.
- **Reactive switching without a reload:** would need every module-level
  formatter and message map to become reactive, for a rarely used control.
