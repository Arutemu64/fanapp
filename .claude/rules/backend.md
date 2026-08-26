---
paths:
  - "backend/**"
---

# Backend triggers

Loaded only when working with `backend/**` files.

- Load the `fastapi` and `clean-ddd-hexagonal` skills; read [docs/backend.md](../../docs/backend.md) (start at "Rules at a glance").
- Changing an ORM model or writing a migration? Load `fanfan-migrations` and `sqlalchemy-alembic-expert-best-practices-code-review`. Adding a member to a DB-backed enum autogenerates an *empty* migration — it needs a hand-written CHECK constraint swap.
- `core/` and `application/` never import `adapters/` or `presentation/` — infrastructure only through ports in `application/ports/`.
- Favour the obvious construction over the compact one — no nested ternaries, no dense one-liners, no logic buried in a comprehension. Incidental complexity only: ports, interactors and value objects stay even with a single caller ([ADR-0005](../../docs/adr/0005-ports-as-protocol-with-explicit-adapter-subclassing.md)).
- Comments in English, and only where they carry the *why* (constraint, rejected alternative, ADR ref) — never a restatement of the code. Update a comment in the same edit as the code under it; don't drop an existing one while refactoring unless its code is gone.
- After changes: run `just backend-lint` and `just backend-typecheck`; fix all errors. Prefer CI for the integration suite (`just backend-test-integration`) — it's slow and CI runs it anyway, so don't gate work on it; run it locally only when it helps (debugging). Cloud web sessions have a Docker daemon for `just backend-generate-auto` and the suite alike.
- Research the current best practice (web / current docs) before any non-trivial work — a refactor, a new feature, a library call, a config default. Never decide from training memory alone; cite what you find.
- Changed an env var, endpoint, or error code? Update `.env.example` and the docs in the same change (AGENTS.md "Never" / "Staying in sync"), and run `just frontend-generate-api` for API changes — a unit test fails if the committed spec drifts from the routers.
