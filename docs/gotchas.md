<!--
  Purpose: A running log of mistakes and surprising behaviors discovered while
  working in THIS codebase, so that future contributors — human or AI — never
  repeat them.

  When to add an entry (see Core Constraint #10 in AGENTS.md):
    Whenever something behaves differently than you expected — a wrong
    assumption about a library/API, a confusing pattern, or a non-obvious
    gotcha specific to this project.

  What NOT to add:
    Issues that are purely about the environment you happen to run inside
    (e.g. bash vs PowerShell differences, container quirks, local tooling
    setup). Only log issues about this codebase and the libraries it uses.

  Entry format — copy the template below and fill it in:

    ## <short, searchable title>
    - **Area**: <e.g. backend/application, frontend/svelte, Jinja templates, Alembic>
    - **Expected**: What you thought would happen.
    - **Actual**: What actually happened.
    - **Fix / Correct approach**: How to do it right next time.
    - **Date**: YYYY-MM-DD

  Keep entries short and specific. Newest entries go at the top.
-->

# Gotchas & Lessons Learned

## TicketsCloud reuses ticket ids — do not revoke tickets by id alone

- **Area**: backend / TicketsCloud integration (`application/services/ticketscloud.py`, `TCloudService.proceed_order`)
- **Expected**: A ticket id (`ticketscloud_ticket_id`) uniquely and permanently identifies one ticket, so revoking a cancelled/refunded order could just delete the ticket row with that id.
- **Actual**: TicketsCloud **reuses ticket ids** — after a ticket is revoked, the same id can be resold to a different buyer. Deleting purely by `ticketscloud_ticket_id` would therefore drop a ticket that is now legitimately valid again, or churn rows on every sync.
- **Fix / Correct approach**: Revocation is intentionally **not implemented**. `proceed_order` is add-only (it creates tickets for `DONE` orders, never deletes). If/when revocation is added, key the decision off more than the id alone (e.g. also `barcode`/`serial`, and the order's current status) so a resold id is not mistaken for the revoked one. See the TODO in `proceed_order`.
- **Date**: 2026-06-11

## SvelteKit simulates CORS during SSR — adapter-node must know the real origin

- **Area**: frontend / SvelteKit (adapter-node, `hooks.server.ts` `handleFetch`), infra / Caddy
- **Expected**: Server-side `fetch` has no origin, so CORS can't apply during SSR. A page that loads fine in the browser should render fine on the server too.
- **Actual**: A `load` fetch to the API failed **only during SSR** with `CORS error: No 'Access-Control-Allow-Origin' header is present`, even though the underlying request to `http://api:8000` returned 200. Recent SvelteKit *simulates* the browser CORS check during SSR, based on the **original** request URL (`PUBLIC_API_URL`) versus the page origin `event.url.origin` — not the internal URL that `handleFetch` rewrites to. Behind Caddy (which terminates TLS and forwards plain HTTP), `adapter-node` defaulted the SSR origin to `http://<host>`, so a same-origin `https://<host>/api` call looked cross-origin (scheme mismatch) and the simulation rejected the response. The browser, loaded over real HTTPS, saw it as same-origin and worked — hence "SSR only".
- **Fix / Correct approach**: Two things must hold. (1) `adapter-node` must derive the true public origin: set `PROTOCOL_HEADER=x-forwarded-proto` and `HOST_HEADER=x-forwarded-host` on the frontend service (done in `docker-compose.yml`) so it reads Caddy's forwarded scheme/host. (2) `PUBLIC_API_URL` must be the **same origin** as the site with the `/api` path (e.g. `https://example.com/api`), matching `Caddyfile.example`. Then API calls are same-origin in both the browser and SSR and no CORS is involved. Only set `WEB__CORS_ALLOW_ORIGINS` when the API genuinely lives on a different origin; if you do, it must list the public app origin exactly (scheme + host, no trailing slash, no path).
- **Date**: 2026-06-11

## A new service process needs its own infra-host env overrides in docker-compose

- **Area**: infra / docker-compose, DI (`StreamProvider`, `EventBroker`)
- **Expected**: Adding the outbox relay (which uses `EventBroker` → `NatsBroker`) to the existing `scheduler` service would just work, since `api`/`faststream` connect to NATS fine.
- **Actual**: The relay's first tick hung forever (`apscheduler` then logged `maximum number of running instances reached (1)` every interval). Cause: `.env` ships `NATS__HOST=127.0.0.1` for local dev, and each compose service overrides the hosts it needs (`DB__HOST: db`, `REDIS__HOST: redis`, `NATS__HOST: nats`). The `scheduler` service only overrode `DB__HOST` because it never used NATS/Redis before — so inside the container the broker dialed `127.0.0.1:4222` (itself) and `broker.connect()` blocked forever. The empty outbox table made it look like the hang was elsewhere; it was actually the first-ever resolution of the NATS-connected `EventBroker`.
- **Fix / Correct approach**: When a service starts using an infra dependency it didn't before, add the matching `*__HOST` env override **and** a `depends_on: { <svc>: { condition: service_healthy } }` in `docker-compose.yml` (base file — prod/dev inherit). Mirror what `api`/`faststream` already set.
- **Date**: 2026-06-10
