---
paths:
  - "frontend/**"
---

# Frontend triggers

Loaded only when working with `frontend/**` files.

- Load the `svelte-code-writer` and `svelte-core-bestpractices` skills for any `.svelte`/`.svelte.ts`/`.svelte.js` change; add `ui-ux-pro-max` for styling/layout work, and `kill-ai-slop`, `accessibility` and `core-web-vitals` before shipping UI.
- Writing or changing Russian copy? Voice, register («ты») and the glossary (Программа / Выступление / Голосование) live in [.agents/redpolitika.md](../../.agents/redpolitika.md), read automatically by the `ux-copy` / `redaktura` skills — load `ux-copy` for interface strings. Load `fanfan-russian-copy` for the repo mechanics (plural three-forms, two-file emails, the copy-tells scanner).
- Touching `service-worker.ts`, `manifest.json`, the IndexedDB offline cache or Web Push? Read [docs/frontend.md](../../docs/frontend.md) §2 "PWA & Offline Support" — and note the SW's fetch handler is inert in dev, so verify with `just run-prod`, not `just frontend-dev`.
- Read [docs/frontend.md](../../docs/frontend.md) for project bindings (typography/radius/z-index scales, modal conventions, offline cache, component placement).
- Prefer the vendored shadcn-svelte components in `$lib/components/ui/` over hand-rolled elements; load the `shadcn-svelte` skill and add missing ones with the CLI (`pnpm dlx shadcn-svelte@latest add <name>`). Style with built-in variants and semantic tokens (`variant="outline"`, `bg-muted`, `text-muted-foreground`) — use `class` for layout, not to override component colors. Change an app-wide default by editing the component source in `ui/` or the CSS variables in `src/app.css`, never by repeating an override per instance — see [docs/frontend.md](../../docs/frontend.md) §3.
- All user-facing copy in Russian; code comments in English.
- Favour the obvious construction over the compact one — no nested ternaries in markup, no dense one-liners. Prefer a named `$derived` over an inline expression a reader has to unpick.
- Comment only to carry the *why* (browser quirk, ordering constraint, why an effect is needed) — never a restatement of the markup or a `$derived`. Update a comment in the same edit as the code under it; don't drop an existing one while refactoring unless its code is gone.
- Never store user/session state in module-level singletons (client-rendered SPA).
- Research the current best practice (web / current docs) before any non-trivial work — a refactor, a new feature, a library or framework API. Never decide from training memory alone; cite what you find.
- Mobile-first; bottom padding for the floating nav bar.
- After changes: run `just frontend-lint` and `just frontend-check`; fix all errors. Touched pure logic in `src/lib/`? Run `just frontend-test` too, and consider a colocated `*.test.ts` — see [docs/testing.md](../../docs/testing.md) "Frontend".
