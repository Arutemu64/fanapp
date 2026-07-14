---
paths:
  - "backend/**"
---

# Backend triggers

Loaded only when working with `backend/**` files.

- Load the `fastapi` and `clean-ddd-hexagonal` skills; read [docs/backend.md](../../docs/backend.md) (start at "Rules at a glance").
- `core/` and `application/` never import `adapters/` or `presentation/` — infrastructure only through ports in `application/ports/`.
- After changes: run `just backend-lint` and `just backend-typecheck`; fix all errors.
- Changed an env var, endpoint, or error code? Check AGENTS.md constraints 8–9 (`.env.example`, docs sync) and run `just frontend-generate-api` for API changes.
