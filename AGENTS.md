# Monorepo Guidelines (FAN FAN helper web app)

Helper web app for the "FAN FAN" Russian anime convention (audience: teen to young adults, non-tech).

## Codebase Map
```text
├── backend/                  # FastAPI Application
│   └── src/fanfan/
│       ├── core/             # Pure Domain Models, Value Objects, Exceptions
│       ├── application/      # Interactors, Use Cases, DTOs, Ports
│       ├── presentation/     # Interfaces: HTTP (web/), Telegram (tgbot/), NATS (faststream/)
│       ├── adapters/         # Infrastructure: DB, Redis, NATS, Telegram, external clients
│       ├── main/             # FastAPI setup, dependency injection (DI) container (Dishka)
│       └── common/           # Shared static assets, path helpers
├── frontend/                 # SvelteKit Application (Svelte 5 runes)
│   └── src/
│       ├── routes/           # Pages & layout files
│       └── lib/
│           ├── components/   # Reusable UI (SectionHeader, ToastContainer, etc.)
│           ├── api/          # Shared openapi-fetch client & generated types (v1.d.ts)
│           ├── types/        # Local TS interfaces and schema type overrides
│           ├── services/     # Svelte 5 reactivity services (toasts, events, PWA)
│           ├── utils/        # Shared helpers (formatters, permissions, validation)
│           ├── constants/    # Frontend constants
│           ├── server/       # Server-only modules (cookies, etc.)
│           └── assets/       # Static assets imported by components
├── shared/                   # Shared OpenAPI spec
│   └── openapi/
└── config/                   # Redis and infrastructure configuration files
```

## Stack & Core Commands
* **Frontend**: SvelteKit (Svelte 5 Runes) + Flowbite-Svelte + Tailwind CSS v4 | `pnpm`
* **Backend**: FastAPI + PostgreSQL (SQLAlchemy + Alembic) + Redis + NATS (FastStream) | `uv`
* **Command Runner**: `justfile` (Run from root):
  * `just run-dev` - Start full env via Docker Compose
  * `just backend-dev` / `just frontend-dev` - Start dev locally
  * `just backend-migrate` - Run Alembic migrations
  * `just backend-generate <name>` - Generate migration file
  * `just frontend-generate-api` - Update SvelteKit types from OpenAPI spec
  * `just backend-lint` / `just frontend-lint` - Lint & format code

## Core Constraints (Must Always Follow)
1. **Russian Copy**: All user-facing labels, placeholders, errors, and toast notifications must be in Russian.
2. **Mobile First**: UI must fit narrow layouts; add bottom padding for floating navigation bars. See [docs/frontend.md](file:///c:/Users/artem/fanapp/docs/frontend.md).
3. **No Automated Tests**: Do not run unit/integration tests unless explicitly requested.
4. **Architectural Isolation**: Domain/Interactors must never import ORM models. See [docs/backend.md](file:///c:/Users/artem/fanapp/docs/backend.md).
5. **SSR & Frontend State Safety**: Never save request-specific state in global/module singletons. Always follow SvelteKit SSR and component guidelines in [docs/frontend.md](file:///c:/Users/artem/fanapp/docs/frontend.md).
6. **Required Svelte Skills**: When editing or analyzing Svelte components (`.svelte`) or Svelte modules (`.svelte.ts`/`.svelte.js`), the LLM MUST proactively load and apply the `svelte-code-writer` and `svelte-core-bestpractices` workspace skills before performing any changes.
7. **Skills & Docs**: Proactively load relevant workspace skills. Read guides in [docs/](file:///c:/Users/artem/fanapp/docs/) for feature implementation.
   * Frontend/Svelte work → `svelte-code-writer`, `svelte-core-bestpractices`, `tailwind-css-patterns`, `ui-ux-pro-max`
   * Backend/FastAPI work → `fastapi`, `clean-ddd-hexagonal`
   * Python tests → `python-testing-patterns`
   * Docker / Infra → `docker-expert`
   * Docs / Writing → `documentation-writer`
8. **Keep Documentation in Sync**: After any structural, architectural, or path-level change, verify and update `AGENTS.md` and relevant `docs/*.md` files before marking the task complete.
   * Did you add, rename, or delete a `lib/` submodule (`services/`, `utils/`, etc.)? Update the **Codebase Map**.
   * Did you change an important file path referenced in docs (e.g., toast store location, CLI commands, layout paths)? Update the doc that mentions it.
   * Did you introduce a new architectural pattern (new DI provider, new ports folder, new adapter type)? Update the relevant `docs/*.md` file.
   * Prefer **documenting patterns and rules** over exact file lists that rot quickly. The Codebase Map should stay high-level; do not list every individual file.
