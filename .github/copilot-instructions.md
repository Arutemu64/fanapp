# FAN FAN — Copilot Instructions

FAN FAN is a helper web app for a Russian anime convention. The audience is
teens and young adults, non-technical, mostly on phones.

## Tech stack

- **Backend** (`backend/`): FastAPI + PostgreSQL (SQLAlchemy + Alembic) + Redis + NATS (FastStream); dependencies managed with `uv`.
- **Frontend** (`frontend/`): SvelteKit with Svelte 5 runes + Flowbite-Svelte + Tailwind CSS v4; dependencies managed with `pnpm`.
- Commands run from the repo root via `just` (see `justfile`).

## Commands

- `just backend-lint` and `just backend-typecheck` — run after every backend change; fix all errors.
- `just frontend-lint` and `just frontend-check` — run after every frontend change; fix all errors.
- `just frontend-generate-api` — regenerate frontend API types after backend endpoint/schema changes.
- `just backend-generate-auto <name>` — autogenerate an Alembic migration; always review the output.

## Rules

- All user-facing text (labels, placeholders, errors, toasts) is in Russian. All code comments and docstrings are in English.
- The backend is hexagonal: `core/` and `application/` must never import `adapters/` or `presentation/`. Infrastructure is reached only through ports in `application/ports/`. See `docs/backend.md`.
- The frontend is a client-rendered SPA. Never store user/session state in module-level singletons; it leaks across navigations and logins. See `docs/frontend.md`.
- Mobile-first UI: design for narrow screens and add bottom padding so the floating nav bar never covers controls.
- Comments explain *why*, not *what*. No commented-out code; no untracked TODOs.
- Full guidelines: `AGENTS.md` and `docs/*.md` (`backend.md`, `frontend.md`, `api.md`, `testing.md`).
