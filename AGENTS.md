# Monorepo Guidelines (FAN FAN helper web app)

Helper web app for the "FAN FAN" Russian anime convention (audience: teen to young adults, non-tech).

## Codebase Map
```text
├── backend/                  # FastAPI Application
│   └── src/fanfan/
│       ├── core/             # Pure Domain Models, Value Objects, Exceptions
│       ├── application/      # Interactors, Use Cases, DTOs, Ports, Services
│       ├── presentation/     # Interfaces: HTTP (web/), Telegram (tgbot/), NATS (faststream/), CLI (cli/), Scheduler (scheduler/, APScheduler cron + interval jobs incl. the outbox relay)
│       ├── adapters/         # Infrastructure: DB, Redis, NATS, Telegram, external clients
│       ├── main/             # FastAPI setup, dependency injection (DI) container (Dishka)
│       └── common/           # Shared static assets, path helpers
├── frontend/                 # SvelteKit Application (Svelte 5 runes)
│   └── src/
│       ├── routes/           # Pages & layout files
│       └── lib/
│           ├── assets/       # Bundled, Vite-processed assets (content-hashed; e.g. map/ venue maps)
│           ├── components/   # Reusable UI (SectionIntro, ToastContainer, etc.)
│           ├── api/          # Shared openapi-fetch client & generated types (v1.d.ts)
│           ├── types/        # Local TS interfaces and schema type overrides
│           ├── services/     # Svelte 5 reactivity services (toasts, events, PWA)
│           ├── utils/        # Shared helpers (formatters, permissions, validation)
│           └── constants/    # Frontend constants
├── shared/                   # Shared OpenAPI spec
│   └── openapi/
├── config/                   # Committed, non-secret infra config (e.g. redis/)
└── secrets/                  # Gitignored runtime secrets (VAPID PEM keys); mounted read-only into backend
```

## Stack & Core Commands
* **Frontend**: SvelteKit (Svelte 5 Runes) + Flowbite-Svelte + Tailwind CSS v4 | `pnpm`
* **Backend**: FastAPI + PostgreSQL (SQLAlchemy + Alembic) + Redis + NATS (FastStream) | `uv`
* **Command Runner**: `justfile` (run from root):
  * `just bootstrap` - One-command local setup: create `.env`, fill generated secrets (DB/Redis/NATS/`WEB__SECRET_KEY`) + VAPID keys; idempotent
  * `just run-dev` / `just run-prod` - Start full env (dev / local prod build) via Docker Compose
  * `just deploy` - Server deploy: pull prebuilt GHCR images (`docker-compose.prod.yml`) & restart
  * `just backend-dev` / `just frontend-dev` - Start dev locally
  * `just backend-migrate` / `just backend-generate <name>` - Run / generate Alembic migration (prefer autogenerate; always review output)
  * `just backend-generate-auto <name>` - Autogenerate a migration against a throwaway Postgres 18 (needs Docker; for when no app DB is running, e.g. cloud)
  * `just frontend-generate-api` - Update SvelteKit types from OpenAPI spec
  * `just backend-lint` / `just frontend-lint` - Lint & format (`backend-lint` also runs the import-linter boundary check)
  * `just dockerfile-lint` - Lint the Dockerfiles with hadolint (installed via mise; config: `.hadolint.yaml`). Also enforced in CI and as a pre-commit hook.
  * `just backend-typecheck` - Run `ty` type checker on backend
  * `just backend-import-lint` - Enforce layer boundaries (import-linter); see [docs/backend.md](docs/backend.md)

## Code Navigation (codegraph)

Gate on one observable fact: does a `.codegraph/` directory exist at the repo root?

* **No `.codegraph/`** → skip this section entirely; use Grep/Glob/Read. Do not install codegraph unless the user asks (install: `pnpm add -g @colbymchenry/codegraph && codegraph init`; re-run `codegraph sync` after pulling new code).
* **`.codegraph/` exists** → use codegraph BEFORE Grep/Glob/Read for any symbol question:
  * "Where is `X`?" → `codegraph query <name>` — definition(s) with `file:line`
  * "What calls `X`?" / "What does `X` call?" → `codegraph callers <symbol>` / `codegraph callees <symbol>`
  * "What breaks if I change `X`?" → `codegraph impact <symbol>`
  * "Show source of `X`" → `codegraph node <symbol> --source` — one symbol, no whole-file read
  * Unfamiliar directory → `codegraph files --path <dir>`
  * After editing code → `codegraph sync` (`.codegraph/` is gitignored)
* If the `codegraph_explore` / `codegraph_node` MCP tools are available, prefer them over the shell CLI — they answer most code questions in one call.
* Fall back to Grep/Read when codegraph returns nothing or the question is not symbol-based (string literal, regex, config value).

## Core Constraints (Must Always Follow)
1. **Russian Copy**: All user-facing labels, placeholders, errors, and toast notifications must be in Russian.
2. **English Comments**: All code comments (inline `#`, `//`, `<!-- -->`, docstrings) must be in English — never Russian or any other language.
3. **Mobile First**: UI must fit narrow layouts; add bottom padding for floating navigation bars. See [docs/frontend.md](docs/frontend.md).
4. **Lint & Type-Check After Changes**: After backend Python changes, run `just backend-lint` and `just backend-typecheck`. After frontend changes, run `just frontend-lint` and `just frontend-check`. After editing a `Dockerfile`, run `just dockerfile-lint` (hadolint). Fix all errors before marking the task complete. Tests are optional — run them when useful; see [docs/testing.md](docs/testing.md).
5. **Architectural Isolation**: The inner layers (`core/`, `application/`) must stay pure — never import from outer layers. No ORM models, concrete adapters (DB gateways, Redis, Telegram, NATS), presentation routers, or external frameworks (no FastAPI/SQLAlchemy in `core/`). All infra goes through abstract ports (`application/ports/`). Enforced by `just backend-import-lint`. See [docs/backend.md](docs/backend.md).
6. **Frontend State Safety**: Never save request-specific state in global/module singletons. Follow the SvelteKit SPA and component guidelines in [docs/frontend.md](docs/frontend.md).
7. **Required Skills by Domain**: Before making changes in a domain, load its skills:
   * Svelte components/modules (`.svelte`, `.svelte.ts`, `.svelte.js`) → `svelte-code-writer`, `svelte-core-bestpractices`
   * Frontend styling/layout → `tailwind-css-patterns`, `ui-ux-pro-max`
   * Backend/FastAPI → `fastapi`, `clean-ddd-hexagonal`
   * Docker / Infra → `docker-expert`
   * Docs / Writing → `documentation-writer`
   * Third-party library APIs → web-search current docs; never rely on training data for signatures
   * Docker / Infra in cloud (web) sessions → read [docs/claude-cloud.md](docs/claude-cloud.md) (setup script vs. SessionStart hook, image prepull, network access)
   * Read the relevant architecture guide in [docs/](docs/) (`backend.md`, `frontend.md`, `api.md`, `testing.md`) before implementing.
8. **Keep Documentation in Sync**: After any structural, architectural, or path-level change, update `AGENTS.md` and the relevant `docs/*.md` in the same change.
   * Added/renamed/deleted a `lib/` submodule (`services/`, `utils/`, etc.) → update the **Codebase Map**.
   * Changed an important file path referenced in docs (toast store, CLI commands, layout paths) → update that doc.
   * Introduced a new architectural pattern (DI provider, ports folder, adapter type) → update the relevant `docs/*.md`.
   * Made an architecturally significant decision (new external dependency, changed deployment topology, or an expensive-to-reverse choice) → add an immutable Architecture Decision Record under [`docs/adr/`](docs/adr/README.md). `docs/*.md` guides say *how it works now*; ADRs record *why we chose it*.
   * Changed a Core Constraint or command that `.claude/rules/*.md` restates → update those files in the same change (they are thin, path-scoped summaries of this file).
   * Prefer **documenting patterns and rules** over exact file lists that rot. Keep the Codebase Map high-level.
9. **Keep `.env.example` in Sync**: Added/renamed/removed an env variable in ANY consumer → update `.env.example` in the SAME change, mirroring the file's grouping and comments. `.env.example` is the single source of truth for env config. The backend uses `extra="ignore"`, so a drifted/typo'd key does NOT crash at boot — this rule is the only thing keeping the consumers in sync.
   * **Backend** (`adapters/config/models.py`): any add/rename/remove or default/optionality change to a field in `EnvConfig` or a nested `*Config` (`web`, `db`, `redis`, `nats`, `mail`, `bot`, `push`, `debug`, external, `scheduler`, `outbox`, `notification`) → edit the matching `SECTION__FIELD` key in the BACKEND block. Renamed a generated-secret placeholder → also update `GENERATED_SECRETS` in `backend/scripts/bootstrap.py` (its drift guard fails loud otherwise).
   * **Docker Compose** (`docker-compose*.yml`): a new `${VAR}` interpolation → add it to the SHARED / DOCKER COMPOSE block (or the relevant backend key if it's a `SECTION__FIELD` passed through to a container).
   * **Frontend** (`frontend/src`, build args): a new `PUBLIC_*` / `VITE_*` read via `$env/static/public` → add it to the FRONTEND block. These are baked in at build time, not runtime.
10. **Clear, Simple Code**: Write straightforward code a junior developer can read unaided. Favor explicit, obvious solutions over clever tricks or dense one-liners. Use descriptive names, small focused functions, and a short comment when intent isn't obvious. If a clever approach is unavoidable, explain why in a comment.
11. **Verify Jinja Templates by Rendering**: After creating or editing a Jinja template, render it with all expected context values and confirm the output before marking the task complete — do not assume it renders correctly.
12. **Update PR on Subsequent Commits**: After pushing additional commits to an open PR, update the PR title and description to reflect the current cumulative state of all changes — not just the latest commit. Title must stay accurate; description must summarize what the PR now does as a whole.
13. **Comment the Why, Not the What**: Code shows *what* and *how* through clear names and structure; comments exist to explain *why*.
    * **Self-documenting code first.** Reach for a descriptive name, a named constant, or an extracted function *before* a comment. If you can't write a clear comment, the code itself probably needs fixing.
    * **Never restate the code.** Delete comments that merely echo the adjacent line or the symbol's name (`# Setup DI`, `// close modal`).
    * **Do comment the non-obvious**: business-rule reasoning and domain constraints, workarounds / hacks / unidiomatic code, footgun warnings ("don't reorder — deferred constraint relies on this"), performance trade-offs, security rationale (fail-closed, constant-time), and the reason behind a bug fix.
    * **A comment must dispel confusion, not add it.** Vague or misleading → rewrite precisely or remove.
    * **No commented-out code.** Delete it — git history is the archive. Keep a snippet only with an explicit note on why it stays.
    * **No untracked TODOs.** Prefer a tracked issue. If a marker is unavoidable, format it `# TODO(<issue-ref>): ...` so it is greppable and owned.
    * **Keep comments in sync with the code.** Update or delete the comment in the *same* change as the code it describes — a stale comment is worse than none.
    * Add links to issues/PRs or external sources when they save the next reader a search.
14. **Verify Best Practice Before Asserting**: Before recommending an approach, HTTP header, config default, caching/security/auth policy, framework convention, or claiming "X is best practice", confirm it with a current web/docs lookup — never from training memory alone. Cite the sources. Scope: applies to recommendations and "best practice" claims, not routine edits (don't web-search every change). Third-party API signatures always require a docs lookup (constraint 7).
15. **Minimize Version/Image Drift**: When the same external dependency (Docker image, tool version) is pinned in more than one place, use the *same* pinned version everywhere rather than letting each reference float or drift independently — e.g. `postgres:18.4-alpine` is the one Postgres image for `docker-compose.yml`, `backend/scripts/generate_migration.py`, and `backend/tests/fixtures/db_provider.py`; `uv==0.11.29` is the one uv version for `mise.toml`, `backend/pyproject.toml`, `backend/Dockerfile`, `.claude/setup.sh`, and CI. Prefer an exact pin over a floating tag so every consumer resolves identically, and bump all references together in the same change — a stray unpinned install (e.g. `pip install --upgrade uv`) or a leftover different tag silently reintroduces drift. If two references genuinely can't share a version (different platform/major requirements), say why in a comment at each site instead of leaving the mismatch unexplained.
