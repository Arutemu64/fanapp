# FAN FAN companion web app

Companion web app for the "FAN FAN" Russian anime convention. Users are teens and young adults, mostly non-technical. The app is in production with real user data.

## Never

- Never import outward from `core/` or `application/`. Infrastructure reaches them only through ports in `application/ports/` (`just backend-import-lint`).
- Never ship user-facing English. All copy is Russian and lives in `frontend/messages/ru.json` ([docs/frontend.md](docs/frontend.md) §6). Code comments and docstrings are English.
- Never keep user-scoped state in a frontend module singleton unless `Session` resets it on every identity change. Modules outlive login and logout, so the next person on a shared phone would see the last account's data.
- Never change an env var without updating `.env.example` in the same change. The backend ignores unknown keys, so drift fails silently.
- Never call work done with a failing gate: `just backend-lint` + `just backend-typecheck` after Python, `just frontend-lint` + `just frontend-check` after frontend, `just dockerfile-lint` after a `Dockerfile`, `just root-lint` after Markdown or YAML outside `frontend/`. A bug fix, or a change with clear inputs and outputs, starts with a failing test ([Anthropic](https://www.anthropic.com/engineering/claude-code-best-practices)); otherwise [docs/testing.md](docs/testing.md) decides whether a change needs a test.
- Never block on the integration suite (`just backend-test-integration`). It is slow and CI runs it. Run it locally only when it helps, for example when debugging.
- Never write a migration that assumes an empty table. Add a column nullable, backfill it, then tighten. The `fanfan-migrations` skill has the procedure.
- Never edit `backend/pyproject.toml` `version` unless asked by name. Suggest a bump instead ([docs/dependencies.md](docs/dependencies.md) "Versioning the app").

## Load before you edit

Load the skills and read the guide before implementing. This file wins over a skill: skills are generic, and where one conflicts with a repo rule, follow the rule.

| Working on                               | Load                                                                                                                                          | Read                                                                                   |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Any code                                 | `solid` (the lint limits below replace its hard numbers)                                                                                      | "Code" below                                                                           |
| Backend / FastAPI                        | `fastapi`, `clean-ddd-hexagonal`                                                                                                              | [docs/backend.md](docs/backend.md) "Rules at a glance"                                 |
| ORM models, migrations, SQL              | `fanfan-migrations`, `sqlalchemy-alembic-expert-best-practices-code-review`, `supabase-postgres-best-practices`                               | [docs/backend.md](docs/backend.md) "Persistence & Transaction Management"              |
| `.svelte`, `.svelte.ts`                  | `svelte-code-writer`, `svelte-core-bestpractices`; run `svelte-autofixer` on each file                                                        | [docs/frontend.md](docs/frontend.md)                                                   |
| UI components                            | `shadcn-svelte`, `web-component-design` (ignore its React and CSS-in-JS examples)                                                             | [docs/frontend.md](docs/frontend.md) §3, §7–8                                          |
| Styling, layout                          | `ui-ux-pro-max`, `mobile-native`                                                                                                              | [docs/frontend.md](docs/frontend.md) §3–4, [DESIGN.md](.agents/context/DESIGN.md)      |
| Design review before shipping UI         | `antislop`, `antislop-ui`, `antislop-human`, `accessibility`, `core-web-vitals`                                                               | [DESIGN.md](.agents/context/DESIGN.md)                                                 |
| Russian copy                             | `ux-copy`, `fanfan-russian-copy`                                                                                                              | [redpolitika.md](.agents/redpolitika.md), [PRODUCT.md](.agents/context/PRODUCT.md)     |
| Offline, service worker, push            | —                                                                                                                                             | [docs/offline.md](docs/offline.md)                                                     |
| API contracts, endpoints, DTOs           | `api-and-interface-design` (we use snake_case, lowercase enums, RFC 9457, keyset cursors)                                                     | [docs/api.md](docs/api.md)                                                             |
| TanStack Query                           | `tanstack-query-best-practices` (React-based; ADR-0021 and ADR-0022 win)                                                                      | [docs/frontend.md](docs/frontend.md) §2, [docs/offline.md](docs/offline.md)            |
| Tests                                    | `python-testing-patterns`, `vitest`, `playwright-best-practices`, `e2e-testing-patterns` (locate by role and Russian name, not `data-testid`) | [docs/testing.md](docs/testing.md)                                                     |
| Auth, user input, webhooks               | `security-and-hardening`                                                                                                                      | [docs/backend.md](docs/backend.md)                                                     |
| Docker, deployment                       | `docker-expert`                                                                                                                               | [docs/dependencies.md](docs/dependencies.md), [docs/deployment.md](docs/deployment.md) |
| Docs, ADRs                               | `documentation-writer`                                                                                                                        | [docs/adr/README.md](docs/adr/README.md)                                               |
| Agent tooling (hooks, subagents, skills) | `writing-for-agents`                                                                                                                          | [agent-tooling.md](.agents/context/agent-tooling.md)                                   |

## Stack & commands

SvelteKit (Svelte 5) + shadcn-svelte + Tailwind v4 with `pnpm`. FastAPI + PostgreSQL (SQLAlchemy, Alembic) + NATS (FastStream) with `uv`. Run `just` from the repo root.

| Command                                                                             | Does                                                                     |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `just bootstrap`                                                                    | Local setup: `.env`, secrets, VAPID keys                                 |
| `just run-dev` / `just run-prod`                                                    | Full stack in Docker Compose                                             |
| `just run-infra` + `just backend-dev` / `just frontend-dev` / `just backend-worker` | Services in Docker, app on the host                                      |
| `just backend-seed-demo`                                                            | Demo programme and voting for an empty environment                       |
| `just backend-lint` / `just backend-typecheck`                                      | Format, ruff, `ty`, import-linter / `ty` alone                           |
| `just frontend-lint` / `just frontend-check`                                        | Prettier and ESLint / `svelte-check`                                     |
| `just backend-test` / `just backend-test-integration`                               | pytest unit / integration (needs Docker)                                 |
| `just frontend-test` / `just frontend-e2e`                                          | Vitest / Playwright against a production build, backend mocked           |
| `just backend-generate-auto <name>`                                                 | Autogenerate a migration against a throwaway Postgres; review the result |
| `just backend-check-migrations`                                                     | Fail on model/migration drift or a broken `downgrade()`                  |
| `just frontend-generate-api`                                                        | Regenerate the OpenAPI spec and the hey-api client                       |
| `just readme-gallery`                                                               | Re-capture the README screenshots                                        |

The justfile lists the rest. Autogenerate emits renames as drop + create and misses enum-member changes.

## Code navigation

Backend layers live in `backend/src/fanfan/`: `core/` (domain), `application/` (use cases, ports), `adapters/` (infrastructure), `presentation/` (HTTP, NATS, CLI), `main/` (entrypoints, DI). Frontend code lives in `frontend/src/` (`routes/`, `lib/`) and its copy in `frontend/messages/ru.json`. Agent material lives in `.agents/`. With `.codegraph/` present, use `codegraph_explore` first and run `codegraph sync` after editing. Locally CodeGraph is opt-in; don't install it unless asked.

## Code

- **Research, then cite.** Before non-trivial work (a refactor, a feature, a library, a config default, a security policy), check current docs or the web and decide from what you find. Training memory goes stale. Cite the source in the PR, comment or reply. Typos, renames and copy tweaks are exempt.
- **Design by SOLID, KISS, YAGNI and DRY.** Pick the simplest design for today's requirement. Build nothing for a guessed future need ([Fowler](https://martinfowler.com/bliki/Yagni.html)). Give each module one reason to change, and depend on ports, not adapters (ADR-0005). When principles conflict, the simpler code wins.
- **Optimize what you measured.** Write the plain version first. Add a cache, throttle, batch or index only for a bottleneck a profile or benchmark shows, and cite the number in the comment or PR ([Knuth](https://dl.acm.org/doi/10.1145/356635.356640)).
- **Offer options when the choice is real.** When approaches differ in cost, risk or reach, give two or three with their trade-offs, simplest first, and recommend one.
- **Lint limits.** Python: complexity 8, nesting 3, `@override` on port implementations, no method that ignores `self`. TypeScript: complexity 10, nesting 3, 4 parameters, 60 lines per function, no nested ternaries. Over a limit means split the function, not suppress the rule.
- **Write for the next reader.** Prefer the obvious construction: no dense one-liners, no logic buried in a comprehension. Ports, interactors and value objects stay even with one adapter.
- **A helper or constant earns its name.** Extract a single-caller helper only for a better name, a home for a _why_, a callback slot or a test seam. Name a tuning knob, an unclear magic number or a value two sites share. Use the stdlib's names (`HTTPStatus.NOT_FOUND`). Extract duplication on the third copy, or the second when the copies must stay in sync.
- **Comments.** Comment only where the code needs clarification: a constraint, a rejected alternative, an upstream bug, an ADR. One or two short lines; link to `docs/` for more. Describe the code as it stands, not its history. Change a comment with its code.
- **`TODO`s explain themselves:** `# TODO: <what> — <why deferred>`. File an issue only for cross-cutting work that needs discussion.
- **Write short sentences** in comments, docs, rules, commits and PRs. Use plain imperatives, not ALL-CAPS keywords or IMPORTANT markers; current models over-apply emphasis ([Claude Code best practices](https://code.claude.com/docs/en/best-practices)). A rule that must never bend becomes a lint rule, hook or CI check.

## Staying in sync

Update docs in the same change as the code.

- A new pattern goes in the matching `docs/*.md`. A path or command those docs name gets updated there.
- An expensive-to-reverse decision (new dependency, deployment change) gets a new ADR in [docs/adr/](docs/adr/README.md).
- A version pinned in several places is bumped everywhere, and `renovate.jsonc` covers it ([docs/dependencies.md](docs/dependencies.md)).
- Tool config goes in `backend/pyproject.toml` unless the tool can't read it, the config reads better alone (`backend/ruff.toml`), or it must be readable outside the package (`.editorconfig`, `mise.toml`). Config sits at the layer it governs.
- **Commit & PR titles.** We squash-merge, so the PR title becomes the commit on `main`. Use Conventional Commits; [`pr-title.yml`](.github/workflows/pr-title.yml) holds the allowed types and scopes. Write a lowercase imperative subject of about 70 characters that names the change and its effect ("feat(voting): make voting honestly offline-only"). The body holds only facts the diff can't show. Fill [`.github/pull_request_template.md`](.github/pull_request_template.md) by hand when you open a PR from the CLI. Refresh the title and description when a PR gains commits.
