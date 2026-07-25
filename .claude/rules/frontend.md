---
paths:
  - "frontend/**"
---

# Frontend triggers

Loaded only when working with `frontend/**` files.

- Load the `svelte-code-writer` and `svelte-core-bestpractices` skills for any `.svelte`/`.svelte.ts`/`.svelte.js` change; add `tailwind-css-patterns` and `ui-ux-pro-max` for styling/layout work.
- Read [docs/frontend.md](../../docs/frontend.md) for project bindings (typography/radius/z-index scales, modal conventions, offline cache, component placement).
- All user-facing copy in Russian; code comments in English.
- Favour the obvious construction over the compact one — no nested ternaries in markup, no dense one-liners. Prefer a named `$derived` over an inline expression a reader has to unpick.
- Comment only to carry the *why* (browser quirk, ordering constraint, why an effect is needed) — never a restatement of the markup or a `$derived`. Update a comment in the same edit as the code under it; don't drop an existing one while refactoring unless its code is gone.
- Never store user/session state in module-level singletons (client-rendered SPA).
- Mobile-first; bottom padding for the floating nav bar.
- After changes: run `just frontend-lint` and `just frontend-check`; fix all errors.
