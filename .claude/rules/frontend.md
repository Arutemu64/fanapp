---
paths:
  - "frontend/**"
---

# Frontend triggers

Loaded only when working with `frontend/**` files.

- Load the `svelte-code-writer` and `svelte-core-bestpractices` skills for any `.svelte`/`.svelte.ts`/`.svelte.js` change; add `ui-ux-pro-max` for styling/layout work, and `kill-ai-slop`, `accessibility` and `core-web-vitals` before shipping UI. Load `vitest` when writing unit tests for `src/lib/`. Load `tanstack-query-best-practices` before adding or changing a query, mutation or cache setting (it is written for React; ADR-0021 and ADR-0022 win where they differ).
- Writing or changing Russian copy? Voice, register («ты») and the glossary (Программа / Выступление / Голосование) live in [.agents/redpolitika.md](../../.agents/redpolitika.md), read automatically by the `ux-copy` / `redaktura` skills — load `ux-copy` for interface strings. Load `fanfan-russian-copy` for the repo mechanics (plural three-forms, two-file emails, the copy-tells scanner).
- Touching `src/service-worker/`, `manifest.json`, the IndexedDB offline cache or Web Push? Read [docs/frontend.md](../../docs/frontend.md) §2 "PWA & Offline Support" — and note the SW's fetch handler is inert in dev, so verify with `just run-prod`, not `just frontend-dev`.
- Read [docs/frontend.md](../../docs/frontend.md) for project bindings (typography/radius/z-index scales, modal conventions, offline cache, component placement).
- Prefer the vendored shadcn-svelte components in `#lib/components/ui/` over hand-rolled elements; load the `shadcn-svelte` skill and add missing ones with the CLI (`pnpm dlx shadcn-svelte@latest add <name>`). Style with built-in variants and semantic tokens (`variant="outline"`, `bg-muted`, `text-muted-foreground`) — use `class` for layout, not to override component colors. Change an app-wide default by editing the component source in `ui/` or the CSS variables in `src/app.css`, never by repeating an override per instance — see [docs/frontend.md](../../docs/frontend.md) §3.
- All user-facing copy in Russian; code comments in English.
- Favour the obvious construction over the compact one — no nested ternaries in markup, no dense one-liners. Prefer a named `$derived` over an inline expression a reader has to unpick.
- A single-caller helper or a single-use constant needs a reason to exist (AGENTS.md "A helper or constant earns its name"); a template event handler or a hoisted regex/`Intl` formatter already has one.
- Comment only to carry the *why* (browser quirk, ordering constraint, why an effect is needed) — never a restatement of the markup or a `$derived`. Update a comment in the same edit as the code under it; don't drop one that carries a *why* unless its code is gone (a pure restatement may go — see AGENTS.md).
- Never store user/session state in module-level singletons (client-rendered SPA).
- Research the current best practice (web / current docs) before any non-trivial work — a refactor, a new feature, a library or framework API. Never decide from training memory alone; cite what you find.
- Mobile-first; bottom padding for the floating nav bar.
- Adding a write trigger (a button, switch or form submit that runs a mutation) to a page that stays readable offline? Bind `offlineWriteGate` on it: `aria-disabled={gate.blocked}` and `onclick={gate.guard(handler)}` (or `onsubmit`/`onCheckedChange`), so offline it explains itself instead of failing. A modal's confirm button is covered by the gated trigger that opens it. See [docs/frontend.md](../../docs/frontend.md) §2.
- Visible change to the home, schedule, voting, notifications, map or profile screen? Run `just readme-gallery` and commit the refreshed README images in the same change (AGENTS.md "Staying in sync").
- The `PostToolUse` hook already ran `prettier --check` on the file you just edited, and on a `.svelte` file flagged any user-facing English it spotted. It does NOT run eslint (too slow to sit in the edit loop) or `svelte-check` (whole-project), so a silent hook is not a green light. On every `.svelte`/`.svelte.ts` you touch, also run `npx @sveltejs/mcp svelte-autofixer <path>` (no `--svelte-version` flag; the CLI rejects it) and fix what it reports. After changes: run `just frontend-lint` and `just frontend-check`; fix all errors. Touched pure logic in `src/lib/`? Run `just frontend-test` too, and consider a colocated `*.test.ts` — see [docs/testing.md](../../docs/testing.md) "Frontend".
