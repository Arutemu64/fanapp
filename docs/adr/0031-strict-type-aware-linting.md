# ADR-0031: Strict type-aware linting as a guardrail for generated code

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Project maintainers

## Context

Most of this frontend is written by agents. An agent copies the patterns it sees
nearby and takes the cheapest route to a green gate: an `eslint-disable` with no
reason, a deprecated API from its training data, a truthiness check that treats
`0` as missing, a conditional assertion in a test that silently checks nothing.
Review catches some of this; a lint gate catches all of it, every time.

The config already ran typescript-eslint's `recommendedTypeChecked`. Measured on
this codebase in October 2026, moving to `strictTypeChecked` found 27 uses of
deprecated APIs (renamed Lucide icons, TanStack Query's `fetchQuery` and
`isCancelledError`, SvelteKit's object-body `error()`), a dead `?? fallback` the
SDK's types rule out, and always-true object checks. typescript-eslint marks the
strict preset as not covered by semver: a minor release can add rules or tighten
options ([shared configs](https://typescript-eslint.io/users/configs/)).

Community presets for agent-written code exist (eslint-config-agent,
eslint-for-ai, @coderrob's zero-tolerance plugin), but each is a young,
single-maintainer package that bundles React rules or opinionated bans (optional
chaining, magic numbers). The parts that fit are available from maintained
plugins.

## Decision

We lint with `strictTypeChecked`, plus a small set of rules chosen for the
shortcuts generated code takes, all in `frontend/eslint.config.js`:

- **Suppressions must justify themselves.**
  `@eslint-community/eslint-plugin-eslint-comments` (recommended, plus
  `require-description`: every directive carries `-- reason`).
  `no-restricted-disable` forbids disabling the Tailwind design rules inline,
  since their exemptions live in `eslint.tailwind.js`. `reportUnusedDisableDirectives`
  and `reportUnusedInlineConfigs` are errors, not ESLint's default warning.
- **Type-aware correctness beyond the preset**: `strict-boolean-expressions`
  (nullable strings and booleans allowed; `any`, objects and nullable numbers
  not), `switch-exhaustiveness-check`, `require-array-sort-compare`,
  `prefer-readonly`, `eqeqeq` (smart), `no-implicit-coercion` (`!!` allowed),
  `no-param-reassign`, and `no-console` (warn and error only).
- **Svelte 5 opt-ins** from eslint-plugin-svelte beyond `recommended`:
  `no-top-level-browser-globals`, `no-at-const-tags` (`{@const}` is legacy since
  Svelte 5.56), `no-add-event-listener` in components, `button-has-type`,
  `no-target-blank` and a few others with no findings today.
- **Test plugins**: `eslint-plugin-playwright` (`flat/recommended`) on `e2e/`, and
  `@vitest/eslint-plugin` (`recommended`) on `src/**/*.test.ts`.

Where a strict rule misreads Svelte, it is turned off for `.svelte` files with the
reason beside it, rather than suppressed per line: `no-useless-default-assignment`
(its autofix deletes `$bindable()` and breaks two-way binding) and
`no-confusing-void-expression` (it reports every `{@render}` tag). Vendored
shadcn-svelte `ui/` files get the condition checks relaxed alongside the existing
`no-unsafe-*` carve-out, so they stay diffable against upstream.

## Consequences

- A lint failure now names deprecated APIs before their removal ships.
- A `typescript-eslint` minor bump can add findings. Renovate's dependency PRs run
  the gate, so a new finding lands as a red PR to fix, not a surprise on `main`.
- Three more pinned dev dependencies to keep current.
- `eslint --fix` from the strict preset is not blindly safe in `.svelte` files; the
  carve-outs above record the two cases found. Review autofix diffs on components.

## Alternatives considered

- **Stay on `recommendedTypeChecked` and add `no-deprecated` alone.** Catches the
  deprecations, misses the condition and promise rules that make up most of the
  rest.
- **Adopt an "AI lint" preset wholesale.** Rejected for maintenance risk and
  rules that fight this codebase's conventions (see Context).
- **`noInlineConfig`, banning every directive.** The few remaining suppressions are
  genuine (an SDK error body that is not an `Error`, a control-character regex);
  `require-description` keeps them reviewable without forcing workarounds.
- **`stylisticTypeChecked`, `curly: all`, `explicit-module-boundary-types`.**
  Style, not correctness; hundreds of changes for no bug class caught.
