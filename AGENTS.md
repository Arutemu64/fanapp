# Monorepo Guidelines (FAN FAN helper web app)

Helper web app for the "FAN FAN" Russian anime convention (audience: teen to young adults, non-tech).

## Codebase Map
```text
├── backend/                  # FastAPI Application
│   └── src/fanfan/
│       ├── core/             # Pure Domain Models, Value Objects, Exceptions
│       ├── application/      # Interactors, Use Cases, DTOs, Ports, Services
│       ├── presentation/     # Interfaces: HTTP (web/), Telegram (tgbot/), NATS (faststream/), CLI (cli/), Scheduler (scheduler/, APScheduler cron jobs)
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
  * `just backend-typecheck` - Run `ty` type checker on backend

## Code Navigation (`codegraph`)
This 550+ file codebase is indexed by [`codegraph`](https://www.npmjs.com/package/@colbymchenry/codegraph), a code-intelligence CLI. In Claude Code web sessions it is auto-installed and indexed by the SessionStart hook (`.claude/hooks/session-start.sh`); locally, install it once with `pnpm add -g @colbymchenry/codegraph && codegraph init`. **Prefer it over reading whole files to trace symbols** — it answers structural questions in one call and saves tokens:
  * `codegraph query <name>` - Find a symbol's definition(s) with `file:line`
  * `codegraph callers <symbol>` / `codegraph callees <symbol>` - Walk the call graph
  * `codegraph impact <symbol>` - Blast radius before a refactor (what breaks if you change it)
  * `codegraph node <symbol> --source` - One symbol's source without opening the file
  * `codegraph files [--path <dir>]` - Indexed file tree with language + symbol counts
  * `codegraph sync` - Refresh the index after edits (the index in `.codegraph/` is gitignored)
We use the CLI on demand rather than the always-on MCP server so it costs no context until invoked.

## Core Constraints (Must Always Follow)
1. **Russian Copy**: All user-facing labels, placeholders, errors, and toast notifications must be in Russian.
2. **Mobile First**: UI must fit narrow layouts; add bottom padding for floating navigation bars. See [docs/frontend.md](docs/frontend.md).
3. **No Automated Tests**: Do not run unit/integration tests unless explicitly requested. When you do write or run tests, follow [docs/testing.md](docs/testing.md).
4. **Lint & Type-Check After Backend Changes**: After modifying any backend Python code, run `just backend-lint` and `just backend-typecheck`. Fix all errors before marking the task complete. For frontend changes, run `just frontend-lint` and `just frontend-check`.
5. **Architectural Isolation**: The inner layers (`core/`, `application/`) must remain pure. They must never import from outer layers—this means absolutely no ORM models, concrete adapters (DB gateways, Redis, Telegram, NATS), presentation routers, or external frameworks (no FastAPI, SQLAlchemy in `core/`). All infra operations must go through abstract ports (`application/ports/`). See [docs/backend.md](docs/backend.md).
6. **SSR & Frontend State Safety**: Never save request-specific state in global/module singletons. Always follow SvelteKit SSR and component guidelines in [docs/frontend.md](docs/frontend.md).
7. **Required Skills by Domain**: When working in any of the following domains, the LLM MUST load the listed skills BEFORE making changes:
   * Svelte components/modules (`.svelte`, `.svelte.ts`, `.svelte.js`) → `svelte-code-writer`, `svelte-core-bestpractices`
   * Frontend styling/layout → `tailwind-css-patterns`, `ui-ux-pro-max`
   * Backend/FastAPI work → `fastapi`, `clean-ddd-hexagonal`
   * Docker / Infra → `docker-expert`
   * Docs / Writing → `documentation-writer`
   * Third-party library API questions → `find-docs` (query current docs; never rely on training data for API signatures)
   * Read the architecture guides in [docs/](docs/) (`backend.md`, `frontend.md`, `api.md`, `testing.md`) before implementing in those areas.
8. **Keep Documentation in Sync**: After any structural, architectural, or path-level change, verify and update `AGENTS.md` and relevant `docs/*.md` files before marking the task complete.
   * Did you add, rename, or delete a `lib/` submodule (`services/`, `utils/`, etc.)? Update the **Codebase Map**.
   * Did you change an important file path referenced in docs (e.g., toast store location, CLI commands, layout paths)? Update the doc that mentions it.
   * Did you introduce a new architectural pattern (new DI provider, new ports folder, new adapter type)? Update the relevant `docs/*.md` file.
   * Prefer **documenting patterns and rules** over exact file lists that rot quickly. The Codebase Map should stay high-level; do not list every individual file.
9. **Clear, Simple Code**: Write straightforward code that a junior developer can read and understand without help. Favor explicit, obvious solutions over clever tricks, dense one-liners, or implicit magic. Use descriptive names, small focused functions, and add a short comment when intent isn't obvious. If a clever approach is unavoidable, explain why in a comment.
