# FAN FAN companion web app

Companion web app for the "FAN FAN" Russian anime convention. Users are teens and young adults, mostly non-technical. The app is in production with real user data.

## Never

- Never import outward from `core/` or `application/`. Infrastructure reaches them only through ports in `application/ports/` (`just backend-import-lint`).
- Never ship user-facing English. All copy is Russian and lives in `frontend/messages/ru.json` ([docs/frontend.md](docs/frontend.md) §6). Code comments and docstrings are English.
- Never keep user-scoped state in a frontend module singleton unless `Session` resets it on every identity change. Modules outlive login and logout, so the next person on a shared phone would see the last account's data.
- Never change an env var without updating `.env.example` in the same change. The backend ignores unknown keys, so drift fails silently.
- Never write a migration that assumes an empty table. Add a column nullable, backfill it, then tighten. The `fanfan-migrations` skill has the procedure.
- Never edit `backend/pyproject.toml` `version` unless asked by name. Suggest a bump instead ([docs/dependencies.md](docs/dependencies.md) "Versioning the app").

## Task guides

Read the relevant guide and load the listed skills for the work at hand. Fanapp's rules take precedence.

- For **backend work**, use `fastapi` and `clean-ddd-hexagonal`. [Backend rules](docs/backend.md)
- For **database work**, use `fanfan-migrations` for schema and database enum changes, `sqlalchemy-alembic-expert-best-practices-code-review` for ORM work, and `supabase-postgres-best-practices` for SQL. [Backend persistence](docs/backend.md)
- For **Svelte files**, load `svelte-code-writer` and `svelte-core-bestpractices` for `.svelte` and `.svelte.ts`. Run `svelte-autofixer` on each edited file. [Frontend guide](docs/frontend.md)
- For **UI work**, use `shadcn-svelte` for components, `ui-ux-pro-max` for design and layout, and `mobile-native` for mobile interactions. Review UI with `antislop`, `antislop-ui`, and `antislop-human`. [Frontend guide](docs/frontend.md) · [Design direction](.agents/context/DESIGN.md)
- For **Russian copy**, use `ux-copy` and `fanfan-russian-copy`. [Editorial policy](.agents/redpolitika.md) · [Product](.agents/context/PRODUCT.md)
- For **API contracts and DTOs**, use `api-and-interface-design`. [Fanapp API conventions](docs/api.md)
- For **Svelte Query, cache persistence, service workers, and push**, follow the project guides. [Query and mutation patterns](docs/api.md) · [Offline guide](docs/offline.md)
- For **tests**, use `python-testing-patterns` for Python, `vitest` for frontend unit tests, and `playwright-best-practices` for E2E. Locate UI elements by role and Russian name. [Testing guide](docs/testing.md)
- For **auth, user input, and webhooks**, use `security-and-hardening`. [Backend guide](docs/backend.md)
- For **Docker and deployment**, use `docker-expert`. [Dependencies](docs/dependencies.md) · [Deployment](docs/deployment.md)
- For **docs and ADRs**, use `documentation-writer`. [ADR index](docs/adr/README.md)
- For **agent tooling**, use `writing-for-agents`. [Agent tooling guide](.agents/context/agent-tooling.md)

## Agent skills

Matt Pocock's skills are configured. Use the paths below whenever a skill refers to `docs/agents/`.

### Issue tracker

Track issues and specs in GitHub Issues. [Issue tracker workflow](.agents/context/issue-tracker.md)

### Triage labels

Use the five default triage labels. [Triage labels](.agents/context/triage-labels.md)

### Domain docs

Fanapp uses one root glossary and one ADR directory. [Domain docs](.agents/context/domain.md)

## Commands and checks

Run `just` at the repository root to list recipes. [Development setup](CONTRIBUTING.md#getting-started) · [Command maintenance](CONTRIBUTING.md#finding-and-maintaining-commands)

Resolve failures in the relevant gate before calling work done.

- Backend Python runs `just backend-check`.
- Frontend work runs `just frontend-check`.
- Dockerfile changes run `just dockerfile-lint`.
- Markdown and YAML outside `frontend/` run `just root-lint`.

Start bug fixes and changes with clear inputs and outputs with a failing test. Run the backend integration suite locally when it helps diagnose a problem. CI already runs it. [Testing guide](docs/testing.md)

## Code navigation

Backend layers live in `backend/src/fanfan/`. The domain is in `core/`, use cases and ports in `application/`, infrastructure in `adapters/`, transports in `presentation/`, and entrypoints and DI in `main/`. SvelteKit routes and libraries are in `frontend/src/`. Agent guidance lives in `.agents/`.

Use `codegraph_explore` first in indexed checkouts with CodeGraph available. Run `codegraph sync` after edits there. [Agent tooling guide](.agents/context/agent-tooling.md#codegraph)

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
