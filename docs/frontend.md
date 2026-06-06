# Frontend & SvelteKit Guidelines

This document outlines the codebase-specific constraints, SvelteKit SSR rules, styling standards, layout designs, and custom component inventory.

> [!IMPORTANT]
> **Required Svelte Skills**: Svelte 5 reactivity syntax, runes usage, event handling conventions, and snippet patterns are fully documented in workspace skills. Whenever editing Svelte components (`.svelte`) or Svelte modules (`.svelte.ts`/`.svelte.js`), you **MUST** load and apply these skills:
> 1. `svelte-code-writer`
> 2. `svelte-core-bestpractices`
>
> Refer to those skills for core syntax and best practices; do not duplicate them here.

---

## 1. SSR Safety & Request Isolation

* **Server Evaluation**: Assume every route and component may render on the server first. Do not access browser-only globals (`window`, `document`, `localStorage`, etc.) during module evaluation.
* **Strict State Isolation**: Never store user-specific or request-specific state in global/module-level variables, legacy stores, or reactive singletons.
* **Context API for Shared State**: For state shared across Svelte 5 components, keep logic in classes with `$state` fields instanced per component/request. Use Svelte 5's type-safe `createContext` utility (rather than global stores or raw module variables) to scope state to the request-specific component tree, eliminating SSR data leakage.
* **Browser Guards**: Guard browser-only execution paths with `browser` from `$app/environment` during rendering, or isolate them inside component lifecycles (`onMount` or `$effect`).

---

## 2. Data Loading & SvelteKit Integration

* **Data Fetching boundaries**: Move first-render data requirements into SvelteKit layout or page `load` functions.
* **SSR fetch forwarding**: Always pass the SvelteKit-provided `fetch` (from load functions or server events) inside the request options block of your client calls (e.g., `client.GET('/route', { fetch })`) to preserve session headers, cookies, and correct relative routes.
* **Server-Only Modules**: Server-only modules (e.g., `+page.server.ts`, `.server.ts` files) must be used when handling secure cookies, administrative privileges, or private environment variables. Do not import server-only environment modules in browser-reachable files.

---

## 3. Styling & Custom UI Rules

* **Tailwind CSS v4**: Theme styling is configured directly in `frontend/src/app.css`. Avoid adding Tailwind v3 style configurations or tailwind.config files.
* **Component Preference**: Always prioritize official Flowbite-Svelte components instead of writing custom elements.
* **Icons**: Use `flowbite-svelte-icons` for iconography. Add icons only when they improve navigation or scanning.

### Typography Scale

Two fonts are defined in `app.css`: `font-sans` (Inter, body text) and `font-display` (Unbounded, hero headings and countdown numerics only). Apply sizes by role:

| Role | Classes | Notes |
|---|---|---|
| Hero heading | `font-display text-2xl sm:text-3xl lg:text-4xl font-bold leading-tight` | `font-display` here only |
| Page heading | `text-xl sm:text-2xl font-bold leading-tight` | Used in `SectionHeader` |
| Card/section heading | `text-base sm:text-lg font-semibold leading-snug` | h2/h3 inside cards |
| Body paragraph | `text-sm sm:text-base leading-relaxed` | Default for descriptive text |
| Secondary/helper | `text-xs sm:text-sm leading-relaxed` | Short helper lines next to controls |
| Label/metadata | `text-xs leading-none font-medium` | Single-line only — timestamps, badges, tags |

**Rules:**
* `text-sm` (14px) is the minimum for any multi-line paragraph.
* `text-xs` is for labels, timestamps, and single-line chips — never for multi-sentence body text.
* Never use arbitrary sizes (`text-[10px]`, `text-[0.6rem]`).
* Always add `sm:` responsive upgrade on headings.
* Body text: `leading-relaxed`. Headings: `leading-tight`.

### Border-Radius Scale

Three tiers — pick by element role:

| Tier | Class | Use for |
|---|---|---|
| Outer | `rounded-2xl` | Page-level cards, modals, sheet containers (`ProfileCardShell`, `HeroCard`, `EventCard` wrappers, etc.) |
| Inner | `rounded-xl` | Icon containers, social/chip buttons, dropdown popovers, pill-shaped elements |
| Sub-group | `rounded-lg` | Sections/rows inside a card, toasts, small interactive elements (icon buttons) |
| Circular | `rounded-full` | Avatars, dot indicators, step-number badges |

**Rules:**
* Never use `rounded-sm`, `rounded-md`, or bare `rounded` — they have no role in this scale.
* `rounded-2xl` on the outermost container, `rounded-lg` on inner borders/rows inside it.

---

## 4. Mobile Layout & Forms

* **Mobile-First**: Design for narrow mobile screens first. Keep content inside standard layout containers.
* **Bottom Spacing**: Add bottom padding/spacing to pages to prevent fixed mobile bottom navigation tabs from covering active controls.
* **Form Submissions**: Disable submit buttons and display inline spinners/loading messages when submissions are in-flight.
* **Feedback Scopes**: Place validation errors inline (directly near the related input field). Reserve toasts for transient action results.

---

## 5. Cleanups & Memory Management

* **Resource Cleanups**: Any connection opened on the client (e.g., event listeners, timers, sockets, streams) must have a clear cleanup path (e.g., returning a cleanup function in `$effect` or using Svelte's `onDestroy`). Prevent memory leaks that accumulate during long sessions or client navigation.

---

## 6. Language & Copy

* **Russian Copy Only**: All user-facing text (buttons, placeholders, errors, toasts, empty states) must be in Russian.
* Keep sentences brief, direct, and actionable. Avoid showing raw backend exceptions or stack traces.

---

## 7. Modal Conventions

All modals use Flowbite-Svelte `<Modal bind:open size="sm">`. Follow these structural rules:

### Required: `{#snippet header()}`

Every modal **must** use the `header` snippet — never put a raw `<h3>` inside the modal body. Always pair the title with a contextual icon:

```svelte
<Modal bind:open size="sm">
  {#snippet header()}
    <div class="flex items-center gap-2">
      <SomeIcon class="h-5 w-5 text-gray-500 dark:text-gray-400" />
      <h3 class="text-lg font-bold text-gray-900 dark:text-white">Заголовок</h3>
    </div>
  {/snippet}

  <!-- body -->
</Modal>
```

### Footer snippet: action-only modals

Use `{#snippet footer()}` for modals whose primary content is not a form — confirmation dialogs, single-action prompts. Flowbite renders a top-border separator automatically:

```svelte
{#snippet footer()}
  <Button type="button" color="alternative" onclick={() => (open = false)}>Отмена</Button>
  <Button type="button" color="red" onclick={handleDelete}>Удалить</Button>
{/snippet}
```

### Form modals: submit button stays in body

When the modal contains a real `<form onsubmit={...}>`, put the submit button **inside the form** in the body — not in the footer snippet. This keeps the button as part of the form flow, and the visual separation is intentional (no footer divider).

### Destructive actions

Destructive confirm buttons use `color="red"`. Always pair with a neutral cancel (`color="alternative"` or `color="light"`).

### No `autoclose`

Do not use the deprecated `autoclose` prop. Wire close explicitly: `onclick={() => (open = false)}`.

### Curly-quote hazard

Never copy-paste class attribute values from rich-text sources. Unicode curly quotes `"` `"` (U+201C/U+201D) look identical to straight quotes but break Svelte's attribute parser, causing cryptic "Object literal" TypeScript errors. Always verify with `cat -A` if type-check fails on a class attribute.

---

## 8. Reusable Component Inventory

Before writing any new component, check existing items in `frontend/src/lib/components/`:
* **Section Headers**: Use `$lib/components/SectionHeader.svelte` for screen titles and subtitles.
* **Toasts**: Trigger alerts via `$lib/services/toasts.svelte.ts` and display them with `$lib/components/ToastContainer.svelte`.
* **Page Containers**: Match the spacing/layout patterns established in `frontend/src/routes/(app)/+layout.svelte`.
