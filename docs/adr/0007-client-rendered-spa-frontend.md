# ADR-0007: Client-rendered SvelteKit SPA frontend

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project maintainers

## Context

The frontend is a companion app for an anime convention: an authenticated,
app-like, mobile-first experience (schedule, voting, notifications, PWA/offline)
rather than a content site that needs SEO or fast first-paint for anonymous
visitors. Running a Node SSR server would add a moving part to operate and
deploy for benefits this audience and feature set do not need.

## Decision

We will ship the frontend as a **client-rendered SPA** with SvelteKit.

- `export const ssr = false` in the root `+layout.ts`; built with
  `@sveltejs/adapter-static` (`fallback: '200.html'`). No Node server runs — a
  small NGINX container serves the static bundle and falls back to `200.html`
  for unknown routes so the client router takes over.
- Public config is read via `$env/static/public`, **baked in at build time**;
  the default API base is the **relative** `/api`, so the same prebuilt image is
  domain-agnostic and runs on any origin without a rebuild.
- All loads are **universal** (`+page.ts`/`+layout.ts`); there are no
  `.server.ts` loads. Client-side guards are UX redirects only — the backend
  enforces real auth on every endpoint.

## Consequences

- Deployment is a static bundle behind NGINX — no Node runtime to operate,
  scale, or patch; one image runs on any domain.
- No SSR means no server-render SEO and a client-render first paint; acceptable
  for an authenticated app-style tool, and not to be undone without revisiting
  this ADR.
- Because config is build-time, changing a `PUBLIC_*` value means rebuilding the
  image; the server's runtime `.env` cannot inject it. Contributors must keep
  request/session state out of module singletons, since an SPA module persists
  across navigations and across login/logout.

See [`docs/frontend.md`](../frontend.md) for the working rules.
