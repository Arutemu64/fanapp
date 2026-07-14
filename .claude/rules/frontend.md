---
paths:
  - "frontend/**"
---

# Frontend triggers

Loaded only when working with `frontend/**` files.

- Load the `svelte-code-writer` and `svelte-core-bestpractices` skills for any `.svelte`/`.svelte.ts`/`.svelte.js` change; add `tailwind-css-patterns` and `ui-ux-pro-max` for styling/layout work.
- Read [docs/frontend.md](../../docs/frontend.md) for project bindings (typography/radius/z-index scales, modal conventions, offline cache, component placement).
- All user-facing copy in Russian; code comments in English.
- Never store user/session state in module-level singletons (client-rendered SPA).
- Mobile-first; bottom padding for the floating nav bar.
- After changes: run `just frontend-lint` and `just frontend-check`; fix all errors.
