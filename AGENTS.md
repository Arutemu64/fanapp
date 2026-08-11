# FAN FAN companion web app — monorepo guidelines

Companion web app for the "FAN FAN" Russian anime convention. Audience: teen to young adult, non-technical.

## Never

* **Never** import outward from `core/` or `application/` — no ORM models, concrete adapters, presentation routers, no FastAPI/SQLAlchemy in `core/`. Infrastructure reaches the inner layers only through ports in `application/ports/`. Enforced by `just backend-import-lint`.
* **Never** ship user-facing English. Every label, placeholder, error, toast and empty state is **Russian**. Code comments and docstrings are **English**.
* **Never** delete or weaken an existing comment while refactoring unless the code it describes is gone. A comment that survived review encodes a constraint you cannot see from the diff; if it looks wrong, verify before dropping it.
* **Never** keep request- or user-scoped state in a frontend module singleton — modules outlive navigation and login/logout in the SPA.
* **Never** add, rename or remove an env var without updating `.env.example` in the same change. Its header explains the three consumers and the grouping; the backend's `extra="ignore"` means a drifted key fails silently at runtime instead of at boot.
* **Never** call work done with a failing gate: `just backend-lint` + `just backend-typecheck` after Python, `just frontend-lint` + `just frontend-check` after frontend, `just dockerfile-lint` after a `Dockerfile`. Whether a change needs a *new* test is a judgment call — make it deliberately, per [docs/testing.md](docs/testing.md). The existing suites (pytest, Vitest) run in CI either way.

## Load before you edit

Load the listed skills and read the guide **before** implementing, not after.

| Working on | Load | Read |
| --- | --- | --- |
| Backend / FastAPI | `fastapi`, `clean-ddd-hexagonal` | [docs/backend.md](docs/backend.md) (start at "Rules at a glance") |
| ORM models / migrations | `fanfan-migrations`, `sqlalchemy-alembic-expert-best-practices-code-review` | [docs/backend.md](docs/backend.md) "Persistence & Transaction Management" |
| `.svelte`, `.svelte.ts`, `.svelte.js` | `svelte-code-writer`, `svelte-core-bestpractices` | [docs/frontend.md](docs/frontend.md) |
| Styling / layout | `impeccable`, `ui-ux-pro-max` | [docs/frontend.md](docs/frontend.md) §3–4 |
| Design review before shipping UI | `kill-ai-slop`, `accessibility`, `core-web-vitals` | [docs/frontend.md](docs/frontend.md) |
| Russian user-facing copy | `ux-copy`, `fanfan-russian-copy` | [.agents/redpolitika.md](.agents/redpolitika.md), [.agents/context/PRODUCT.md](.agents/context/PRODUCT.md) |
| Service worker / manifest / offline / push | — | [docs/frontend.md](docs/frontend.md) §2 "PWA & Offline Support" |
| Frontend ↔ API contracts | — | [docs/api.md](docs/api.md) |
| Tests | — | [docs/testing.md](docs/testing.md) |
| Docker / infra | `docker-expert` | [docs/dependencies.md](docs/dependencies.md) |
| Deployment / reverse proxy | `docker-expert` | [docs/deployment.md](docs/deployment.md) |
| Docker / infra in a **web** session | `docker-expert` | [docs/claude-cloud.md](docs/claude-cloud.md) |
| Docs / writing | `documentation-writer` | [docs/adr/README.md](docs/adr/README.md) |

Third-party library APIs: look the signature up in current docs; never rely on training memory.

**This file wins over a skill.** Skills are vendored from upstream and describe a
generic project; three of them contradict this repo on purpose, and the repo is
right: `test-driven-development` mandates a failing test before every change,
where [docs/testing.md](docs/testing.md) asks you to judge whether this change
warrants one;
`using-git-worktrees` and `finishing-a-development-branch` assume you choose a
branch and how to land it, which a Claude Code on the web session does not. All
three are kept because `executing-plans`, `writing-plans` and
`subagent-driven-development` call them as required sub-skills — ignore the
conflicting instruction, not the skill.

Skills are managed with `npx skills` and pinned in `skills-lock.json`; the ones
named `fanfan-*` are project-local and live only here.

## Stack & commands

* **Frontend**: SvelteKit (Svelte 5 runes) + Flowbite-Svelte + Tailwind v4 | `pnpm`
* **Backend**: FastAPI + PostgreSQL (SQLAlchemy + Alembic) + Redis + NATS (FastStream) | `uv`
* **Runner**: `just`, from the repo root.

| Command | Does |
| --- | --- |
| `just bootstrap` | Local setup: `.env` + generated secrets + VAPID keys. Idempotent. |
| `just run-dev` / `just run-prod` | Full env via Docker Compose (dev / local prod build) |
| `just run-infra` / `just stop-infra` | Backing services only (Postgres, Redis, NATS), for running the app on the host |
| `just deploy` | Server deploy: pull prebuilt GHCR images, restart |
| `just backend-dev` / `just frontend-dev` | Run one side on the host (pair with `just run-infra`) |
| `just backend-stream` / `just backend-scheduler` | Run the FastStream consumer / scheduler (outbox relay + syncs) on the host (pair with `just run-infra`) |
| `just backend-seed-demo` | Fill an empty environment with a demo programme and voting (idempotent) |
| `just backend-lint` / `just backend-typecheck` | Format + ruff + `ty` + import-linter / `ty` alone |
| `just frontend-lint` / `just frontend-check` | Prettier + ESLint / `svelte-check` |
| `just dockerfile-lint` | hadolint (config `.hadolint.yaml`) |
| `just backend-test` / `just backend-test-integration` | pytest (integration needs a Docker daemon) |
| `just frontend-test` | Vitest unit tests for pure `src/lib/` logic |
| `just backend-migrate` | Apply migrations |
| `just backend-check-migrations` | Fail if the ORM models have drifted from the migrations |
| `just backend-generate <name>` | Autogenerate a migration against the running app DB |
| `just backend-generate-auto <name>` | Autogenerate against a throwaway Postgres (no app DB needed; requires Docker) |
| `just frontend-generate-api` | Regenerate the OpenAPI spec and `schema.d.ts` from it |
| `just frontend-check-api` | Fail if `schema.d.ts` has drifted from the spec (the spec itself is guarded by a backend test) |
| `just backend-generate-schedule-template` | Rebuild the schedule-import template `.xlsx` offered for download |
| `just ci` | Every CI gate locally, check-only. Cheaper than spending an Actions run. |

Always review a generated migration: autogenerate emits renames as drop+create and does not see enum-member changes.

## Codebase map

```text
├── backend/src/fanfan/
│   ├── core/            # Pure domain: models, value objects, exceptions
│   ├── application/     # Interactors/use cases, DTOs, ports, services
│   ├── presentation/    # HTTP (web/), Telegram (tgbot/), NATS (faststream/), CLI (cli/), APScheduler cron jobs (scheduler/)
│   ├── adapters/        # Infrastructure: DB, Redis, NATS, Telegram, external clients
│   ├── main/            # Entrypoints (web, cli, faststream, scheduler — which registers the outbox relay) + Dishka DI container
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
* A release version bump is a human call — **never** edit `backend/pyproject.toml` `version` unless asked for one by name, however release-worthy the change feels; self-initiated bumps collide in `uv.lock` and the generated spec. **Suggesting** one is welcome: say which bump and why, in the PR description or your final message — you have just seen whether the change needs manual deploy steps, which is what separates MAJOR from the rest (bump table in [docs/dependencies.md](docs/dependencies.md) "Versioning the app"). When asked: edit `pyproject.toml`, run `just backend-generate-openapi` (refreshes `uv.lock` too — commit both, or the image build fails on `uv sync --locked`), and stop. The `vX.Y.Z` tag is a human step on `main` after merge, since pushing it publishes GHCR images. `frontend/package.json` stays at `0.0.0`.

## Project constraints

* **Mobile first.** Narrow layouts are the default; leave bottom padding so the floating nav bar never covers a control.
* **Verify Jinja templates by rendering them** with the real context before calling the task done — do not assume they render.
* **Research the current best practice before you choose — then cite it.** For any non-obvious technical decision — an HTTP header, config default, caching/security/auth policy, framework convention, or a library/approach — search the web or current docs and decide from what you find, not from training memory (it lags releases). This governs the *choice*, not just the claim: verify **before** committing to a direction, and the same standard still blocks asserting any best-practice claim you have not just checked. Carry the citation into the PR, the code comment, or your reply. Routine edits and settled conventions need none of this.
* **`TODO`s explain themselves.** A marker says what is missing and why it was deferred, so it is actionable without hunting for context: `# TODO: <what> — <why deferred>`. An issue reference is welcome, never required.
* **Write for the reader who arrives next.** Favour the obvious construction over the compact one — no nested ternaries, no dense one-liners, no logic buried in a comprehension. Nesting is what compounds: a reader should be able to follow one function without holding the rest of the file in their head. This targets incidental complexity only — the deliberate structure in [docs/backend.md](docs/backend.md) (ports, interactors, value objects) stays, including where a port has exactly one adapter.
* **Comments carry the *why*.** A comment earns its place by recording something the code cannot say: the constraint that forced this shape, the rejected alternative, the upstream bug, the ADR. Never restate what the line already says, and never annotate a function just because it is new — on short, simple code an explanatory comment is usually noise. Prefer a clearer name or type over a comment that compensates for a bad one.
* **A comment describes the code as it stands, not the edit that produced it.** No "was X", "previously", "changed from", "now uses", "renamed" — the reader opening this file never saw the old state, and stacking transitions ("was A, then B, now C") is the clutter that follows; that history goes in the commit message and the PR. Referencing the past is legitimate only when the payload is a *current constraint* — why a removed thing stays removed, why a tempting alternative is wrong here — which is the "rejected alternative" the bullet above already sanctions.
* **A comment changes with its code, in the same edit.** Touching a line whose comment above it no longer holds means rewriting the comment too. Stale comments are worse than no comment: reviewers trust them.
