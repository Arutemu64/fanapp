# ADR-0030: Lint Tailwind classes against the design system

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Project maintainers

## Context

The design system's rules about classes (type roles, semantic colour tokens, the
z-index ladder; DESIGN.md, docs/frontend.md) lived only in prose. Prose drifts,
and most of this codebase is written by agents, which follow what they see in
nearby code. A typography review found phones on smaller type than desktop through
dozens of `text-sm sm:text-base` steps copied from screen to screen. Nothing
failed when a new one appeared.

Tailwind classes are strings, so no type checker or stock ESLint rule sees them.
Options considered:

- **eslint-plugin-tailwindcss** (francoismassart): mature, and Tailwind v4 support
  arrived in 4.x, but it has no rule to ban classes by pattern, which is the rule
  the design system needs.
- **ESLint's `no-restricted-syntax`** with AST selectors: no dependency, but Svelte
  class values arrive as strings, arrays, `cn()` calls and template literals, and
  a selector per shape is brittle.
- **eslint-plugin-better-tailwindcss** (schoero): `no-restricted-classes` takes
  regexes with a message and an optional autofix, reads classes from all of those
  shapes, supports Svelte and Tailwind v4 via the CSS entry point. About 1.4M
  weekly npm downloads in October 2026, near the older plugin's 1.7M; releases
  every few weeks. One maintainer.

## Decision

We use eslint-plugin-better-tailwindcss, pinned to an exact version, configured in
`frontend/eslint.tailwind.js`:

- the `recommended-error` preset, minus `enforce-consistent-class-order` and
  `enforce-consistent-line-wrapping`, which `prettier-plugin-tailwindcss` and
  Prettier already own;
- `enforce-canonical-classes` ignoring the type roles and `leading-*`, because the
  roles share sizes with stock steps and canonicalisation would rewrite
  `text-body` back to `text-base`;
- `no-restricted-classes` in three groups: **type** (no width-stepped sizes, no
  raw heading sizes, no arbitrary sizes), **palette** (no raw hues, no arbitrary
  colours) and **zIndex** (nothing above `z-30` except the ladder tokens). A file
  is exempted from a group only in `restrictedClassExemptions`, with its reason.

Vendored `ui/` components are linted for correctness only, so they stay diffable
against upstream shadcn-svelte.

The same module feeds `frontend/eslint.tailwind.config.js`, a type-info-free
config the `PostToolUse` edit hook runs on the edited file in about a second, so
an agent sees the message while it is still working on that file.

## Consequences

- A drift that used to need a design review now fails `just frontend-lint`, and
  the messages name the fix (which role, which token, which doc).
- Exemptions are visible in one list, not scattered `eslint-disable` comments.
- One maintainer is a bus-factor risk. If the plugin stalls, the
  restrictions are plain regexes and port to `no-restricted-syntax` or a script.
- `enforce-canonical-classes` follows Tailwind's internal canonicalisation, which
  can change between Tailwind releases and add autofixes on upgrade.
- pnpm's 7-day `minimumReleaseAge` applies: the newest plugin release may be
  unavailable for a week; Renovate handles the bump.
