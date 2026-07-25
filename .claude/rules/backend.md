---
paths:
  - "backend/**"
---

# Backend triggers

Loaded only when working with `backend/**` files.

- Load the `fastapi` and `clean-ddd-hexagonal` skills; read [docs/backend.md](../../docs/backend.md) (start at "Rules at a glance").
- `core/` and `application/` never import `adapters/` or `presentation/` — infrastructure only through ports in `application/ports/`.
- Comments in English, and only where they carry the *why* (constraint, rejected alternative, ADR ref) — never a restatement of the code. Update a comment in the same edit as the code under it; don't drop an existing one while refactoring unless its code is gone.
- After changes: run `just backend-lint` and `just backend-typecheck`; fix all errors.
- Changed an env var, endpoint, or error code? Update `.env.example` and the docs in the same change (AGENTS.md "Never" / "Staying in sync"), and run `just frontend-generate-api` for API changes.
