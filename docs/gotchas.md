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

## A new service process needs its own infra-host env overrides in docker-compose

- **Area**: infra / docker-compose, DI (`StreamProvider`, `EventBroker`)
- **Expected**: Adding the outbox relay (which uses `EventBroker` → `NatsBroker`) to the existing `scheduler` service would just work, since `api`/`faststream` connect to NATS fine.
- **Actual**: The relay's first tick hung forever (`apscheduler` then logged `maximum number of running instances reached (1)` every interval). Cause: `.env` ships `NATS__HOST=127.0.0.1` for local dev, and each compose service overrides the hosts it needs (`DB__HOST: db`, `REDIS__HOST: redis`, `NATS__HOST: nats`). The `scheduler` service only overrode `DB__HOST` because it never used NATS/Redis before — so inside the container the broker dialed `127.0.0.1:4222` (itself) and `broker.connect()` blocked forever. The empty outbox table made it look like the hang was elsewhere; it was actually the first-ever resolution of the NATS-connected `EventBroker`.
- **Fix / Correct approach**: When a service starts using an infra dependency it didn't before, add the matching `*__HOST` env override **and** a `depends_on: { <svc>: { condition: service_healthy } }` in `docker-compose.yml` (base file — prod/dev inherit). Mirror what `api`/`faststream` already set.
- **Date**: 2026-06-10
