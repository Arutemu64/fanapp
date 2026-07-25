# FAN FAN helper web app — monorepo guidelines

Helper web app for the "FAN FAN" Russian anime convention. Audience: teen to young adult, non-technical.

## Never

* **Never** import outward from `core/` or `application/` — no ORM models, concrete adapters, presentation routers, no FastAPI/SQLAlchemy in `core/`. Infrastructure reaches the inner layers only through ports in `application/ports/`. Enforced by `just backend-import-lint`.
* **Never** ship user-facing English. Every label, placeholder, error, toast and empty state is **Russian**. Code comments and docstrings are **English** — what to document, and where, is in [docs/backend.md](docs/backend.md#comments--docstrings) and [docs/frontend.md](docs/frontend.md#12-comments--component-docs).
* **Never** keep request- or user-scoped state in a frontend module singleton — modules outlive navigation and login/logout in the SPA.
* **Never** add, rename or remove an env var without updating `.env.example` in the same change. Its header explains the three consumers and the grouping; the backend's `extra="ignore"` means a drifted key fails silently at runtime instead of at boot.
* **Never** call work done with a failing gate: `just backend-lint` + `just backend-typecheck` after Python, `just frontend-lint` + `just frontend-check` after frontend, `just dockerfile-lint` after a `Dockerfile`. Tests are not a gate — run them when useful.

## Load before you edit

Load the listed skills and read the guide **before** implementing, not after.

| Working on | Load | Read |
| --- | --- | --- |
| Backend / FastAPI | `fastapi`, `clean-ddd-hexagonal` | [docs/backend.md](docs/backend.md) (start at "Rules at a glance") |
| `.svelte`, `.svelte.ts`, `.svelte.js` | `svelte-code-writer`, `svelte-core-bestpractices` | [docs/frontend.md](docs/frontend.md) |
| Styling / layout | `tailwind-css-patterns`, `ui-ux-pro-max` | [docs/frontend.md](docs/frontend.md) §3–4 |
| Frontend ↔ API contracts | — | [docs/api.md](docs/api.md) |
| Tests | — | [docs/testing.md](docs/testing.md) |
| Docker / infra | `docker-expert` | [docs/dependencies.md](docs/dependencies.md) |
| Docker / infra in a **web** session | `docker-expert` | [docs/claude-cloud.md](docs/claude-cloud.md) |
| Docs / writing | `documentation-writer` | [docs/adr/README.md](docs/adr/README.md) |

Third-party library APIs: look the signature up in current docs; never rely on training memory.

## Stack & commands

* **Frontend**: SvelteKit (Svelte 5 runes) + Flowbite-Svelte + Tailwind v4 | `pnpm`
* **Backend**: FastAPI + PostgreSQL (SQLAlchemy + Alembic) + Redis + NATS (FastStream) | `uv`
* **Runner**: `just`, from the repo root.

| Command | Does |
| --- | --- |
| `just bootstrap` | Local setup: `.env` + generated secrets + VAPID keys. Idempotent. |
| `just run-dev` / `just run-prod` | Full env via Docker Compose (dev / local prod build) |
| `just deploy` | Server deploy: pull prebuilt GHCR images, restart |
| `just backend-dev` / `just frontend-dev` | Run one side locally |
| `just backend-lint` / `just backend-typecheck` | Format + ruff + `ty` + import-linter / `ty` alone |
| `just frontend-lint` / `just frontend-check` | Prettier + ESLint / `svelte-check` |
| `just dockerfile-lint` | hadolint (config `.hadolint.yaml`) |
| `just backend-test` / `just backend-test-integration` | pytest (integration needs a Docker daemon) |
| `just backend-migrate` | Apply migrations |
| `just backend-generate <name>` | Autogenerate a migration against the running app DB |
| `just backend-generate-auto <name>` | Autogenerate against a throwaway Postgres (no app DB needed; requires Docker) |
| `just frontend-generate-api` | Regenerate `v1.d.ts` from the OpenAPI spec |
| `just ci` | Every CI gate locally, check-only. Cheaper than spending an Actions run. |

Always review a generated migration: autogenerate emits renames as drop+create and does not see enum-member changes.

## Codebase map

```text
├── backend/src/fanfan/
│   ├── core/            # Pure domain: models, value objects, exceptions
│   ├── application/     # Interactors/use cases, DTOs, ports, services
│   ├── presentation/    # HTTP (web/), Telegram (tgbot/), NATS (faststream/), CLI (cli/), APScheduler (scheduler/, incl. the outbox relay)
│   ├── adapters/        # Infrastructure: DB, Redis, NATS, Telegram, external clients
│   ├── main/            # FastAPI setup + Dishka DI container
│   └── common/          # Shared static assets, path helpers
├── frontend/src/
│   ├── routes/          # Pages & layouts
│   └── lib/             # assets/ components/ api/ types/ services/ utils/ constants/
├── shared/openapi/      # Shared OpenAPI spec
├── config/              # Committed, non-secret infra config
└── secrets/             # Gitignored runtime secrets (VAPID PEM); mounted read-only
```

## Code navigation (codegraph)

`.codegraph/` at the repo root means the index is live — web sessions provision it automatically ([docs/claude-cloud.md](docs/claude-cloud.md)); locally it is opt-in. When it exists, reach for the `codegraph_explore` MCP tool (or the `codegraph` CLI) before Grep/Glob/Read for any symbol question, and run `codegraph sync` after editing. When it does not exist, use Grep/Glob/Read and **do not** install codegraph unless asked. Grep is still the right tool for non-symbol lookups — string literals, regexes, config values.

## Staying in sync

Structural change → update the docs **in the same change**. Prefer documenting patterns over file lists that rot; keep the codebase map high-level.

* New/renamed/deleted `lib/` submodule → the codebase map above.
* New architectural pattern (DI provider, ports folder, adapter type) → the matching `docs/*.md`.
* A path or command that a `docs/*.md` or `.claude/rules/*.md` names → that file. The rules files are thin, path-scoped restatements of this one.
* Architecturally significant decision — new external dependency, changed deployment topology, an expensive-to-reverse choice → a new immutable ADR under [docs/adr/](docs/adr/README.md). Guides say *how it works now*; ADRs record *why we chose it*.
* An open PR that gained commits → refresh its title and description to describe the PR as a whole, not the latest commit.
* A version pinned in more than one place → bump every site together and keep `renovate.json` covering them. See [docs/dependencies.md](docs/dependencies.md).

## Project constraints

* **Mobile first.** Narrow layouts are the default; leave bottom padding so the floating nav bar never covers a control.
* **Verify Jinja templates by rendering them** with the real context before calling the task done — do not assume they render.
* **Verify a "best practice" claim before asserting it.** Recommending an HTTP header, config default, caching/security/auth policy or framework convention needs a current docs lookup and a citation — not training memory. Routine edits do not.
* **`TODO`s are tracked or absent.** Prefer an issue; if a marker is unavoidable, write `# TODO(<issue-ref>): ...` so it is greppable and owned.
