---
paths:
  - "frontend/**"
---

# Frontend triggers

Loaded only when working with `frontend/**` files.

- Load the `svelte-code-writer` and `svelte-core-bestpractices` skills for any `.svelte`/`.svelte.ts`/`.svelte.js` change; add `impeccable` and `ui-ux-pro-max` for styling/layout work, and `kill-ai-slop`, `accessibility` and `core-web-vitals` before shipping UI.
- Writing or changing Russian copy? Load `fanfan-russian-copy` — it pins the register («ты») and the glossary (Программа / Выступление / Голосование).
- Touching `service-worker.ts`, `manifest.json`, the IndexedDB offline cache or Web Push? Read [docs/frontend.md](../../docs/frontend.md) §2 "PWA & Offline Support" — and note the SW's fetch handler is inert in dev, so verify with `just run-prod`, not `just frontend-dev`.
- Read [docs/frontend.md](../../docs/frontend.md) for project bindings (typography/radius/z-index scales, modal conventions, offline cache, component placement).
- Prefer official Flowbite-Svelte components over hand-rolled elements. Repeating the same class on 3+ instances of a Flowbite component? Move it into the root `<ThemeProvider>` `flowbiteTheme`, not per-instance — see [docs/frontend.md](../../docs/frontend.md) §3 "Centralized component theme". Overriding a Flowbite default is fine; just centralize the override, don't preserve the default for its own sake.
- All user-facing copy in Russian; code comments in English.
- Favour the obvious construction over the compact one — no nested ternaries in markup, no dense one-liners. Prefer a named `$derived` over an inline expression a reader has to unpick.
- Comment only to carry the *why* (browser quirk, ordering constraint, why an effect is needed) — never a restatement of the markup or a `$derived`. Update a comment in the same edit as the code under it; don't drop an existing one while refactoring unless its code is gone.
- Never store user/session state in module-level singletons (client-rendered SPA).
- Mobile-first; bottom padding for the floating nav bar.
- After changes: run `just frontend-lint` and `just frontend-check`; fix all errors. Touched pure logic in `src/lib/`? Run `just frontend-test` too, and consider a colocated `*.test.ts` — see [docs/testing.md](../../docs/testing.md) "Frontend".
