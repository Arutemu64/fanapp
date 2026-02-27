---
trigger: always_on
---

**Rule: SvelteKit SSR-First Development**

When generating code for SvelteKit, prioritize SSR safety, performance, and the Svelte 5 (Runes) paradigm.

**1. State Management (Anti-Singleton)**

- Never use module-level singletons for user-specific state.
- Use the **Context API** (`setContext`/`getContext`) inside components to share state classes.
- Look up **Context API** docs before proceeding
- Encapsulate logic in classes within `.svelte.ts` files using `$state` and `$derived`.

**2. Browser API Isolation**

- Guard all browser-only APIs (`window`, `document`, `localStorage`, `EventSource`, `WebSocket`) with `if (browser)` checks from `$app/environment`.
- Use `onMount` or `$effect` for client-side side effects, as these do not run during SSR.

**3. Data Fetching & Security**

- Use SvelteKit `load` functions (`+page.ts` or `+page.server.ts`) for initial data fetching to prevent layout shift.
- Always use the `fetch` provided in the `load` event to ensure cookie inheritance and relative path support. Pass `fetch` into API client.
- Store sensitive session data in **HTTP-only cookies**, never `localStorage`, to ensure the server can authenticate requests during SSR.

**4. Environment Variables**

- Strictly use `$env/static/private` or `$env/dynamic/private` only in `.server.ts` or `+server.ts` files.
- Use `$env/static/public` for client-side accessible configuration.

**5. Performance & Cleanup**

- Avoid memory leaks in the long-running Node.js process. Always provide a `disconnect()` or `destroy()` method for long-lived connections (SSE, WebSockets) and call it in `onDestroy` or `$effect` cleanup.

Common errors:

- `getContext(...)` can only be used during component initialisation
