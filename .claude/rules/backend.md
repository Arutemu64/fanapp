---
paths:
  - "backend/**"
---

# Backend triggers

Loaded only when working with `backend/**` files.

- Load the `fastapi` and `clean-ddd-hexagonal` skills; read [docs/backend.md](../../docs/backend.md) (start at "Rules at a glance"). Add `security-and-hardening` when touching auth, untrusted input, webhooks or external integrations, and `python-testing-patterns` when writing pytest tests.
- Changing an ORM model or writing a migration? Load `fanfan-migrations`, `sqlalchemy-alembic-expert-best-practices-code-review` and `supabase-postgres-best-practices` (also for query/index work). Adding a member to a DB-backed enum autogenerates an *empty* migration — it needs a hand-written CHECK constraint swap.
- Favour the obvious construction over the compact one — no nested ternaries, no dense one-liners, no logic buried in a comprehension. Incidental complexity only: ports, interactors and value objects stay even with a single caller ([ADR-0005](../../docs/adr/0005-ports-as-protocol-with-explicit-adapter-subclassing.md)).
- Comments are in English, one or two short lines, and appear only where the code needs clarification (a constraint, a rejected alternative, an ADR ref). Never narrate or restate the code. Update a comment in the same edit as the code under it.
- The `PostToolUse` hook already ran `ruff check` on the file you just edited and reported any findings — a silent hook means only that ruff passed. Still run `just backend-lint` and `just backend-typecheck` before calling the work done; `ty` and import-linter are whole-project and the hook never runs them. Prefer CI for the integration suite (`just backend-test-integration`) — it's slow and CI runs it anyway, so don't gate work on it; run it locally only when it helps (debugging). Cloud web sessions have a Docker daemon for `just backend-generate-auto` and the suite alike.
- Changed an env var, endpoint, or error code? Update `.env.example` and the docs in the same change (AGENTS.md "Never" / "Staying in sync"), and run `just frontend-generate-api` for API changes — a unit test fails if the committed spec drifts from the routers. A breaking change to a response the frontend saves offline (`/me`, `/config`, the schedule, subscriptions, notifications, the quest) or to a queued write's body (awards, subscriptions, feedback) also bumps `QUERY_CACHE_BUSTER` (`frontend/src/lib/api/offlineQueries.ts`; [docs/offline.md](../../docs/offline.md) "Cache buster").
- Verify a Jinja template by rendering it with the real context before calling the task done.
