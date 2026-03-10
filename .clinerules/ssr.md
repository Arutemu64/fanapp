# SSR-First SvelteKit Rules

## Goal

Make the first render correct on the server, keep user data isolated per request, and avoid browser-only failures.

## Default Approach

- Assume every route and component may render on the server first.
- Move first-render data requirements into SvelteKit load functions when possible.
- Prefer server-friendly architecture over client-only workarounds.

## State Management

- Do not store user-specific state in module-level singletons.
- Share state through props, context, or route data.
- For reusable stateful logic tied to Svelte 5 runes, keep it in `.svelte.ts` modules when that improves clarity.
- Keep ownership of state obvious so it is clear which request or component tree it belongs to.

## Browser-Only APIs

- Treat `window`, `document`, `localStorage`, media queries, observers, sockets, and similar APIs as browser-only.
- Guard browser-only behavior with the SvelteKit environment check.
- Start browser-only side effects inside lifecycle or effect boundaries that do not run during SSR.

## Data Loading

- Use page or layout load functions for initial data needed at render time.
- Use the provided `fetch` inside load so auth, cookies, and relative URLs stay correct.
- Keep server-loaded data serializable and intentional.

## Security and Session Handling

- Keep sensitive session data in secure cookies or server-side storage.
- Do not place tokens or sensitive auth state in client-only persistent storage.
- Use server-only files for privileged logic and secrets.

## Environment Variables

- Read private environment values only in server-only modules.
- Expose only intentionally public configuration to client code.
- Do not import server-only environment modules into browser-reachable files.

## Long-Lived Resources

- Clean up subscriptions, timers, sockets, and streaming connections.
- Any connection opened on the client must have a clear cleanup path.
- Avoid leaks that can accumulate during navigation or long sessions.

## Common Failure Modes

- Accessing browser globals during SSR
- Reading private environment values from client code
- Using shared singleton state across users
- Initializing context outside component setup
- Fetching critical first-render data only after hydration

## Review Checklist

- The route can render without browser globals.
- Initial data is loaded in an SSR-friendly place.
- User-specific state is request-safe.
- Secrets remain server-only.
- Long-lived resources are cleaned up.
