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
  * `just backend-typecheck` - Run `ty` type checker on backend
  * `just backend-import-lint` - Enforce layer boundaries (import-linter); see [docs/backend.md](docs/backend.md)

## Code Navigation (`codegraph`)
This 550+ file codebase is indexed by [`codegraph`](https://www.npmjs.com/package/@colbymchenry/codegraph), a code-intelligence CLI. On the web, the binary is installed once by the environment **setup script** (`.claude/setup.sh`, baked into the cached snapshot) and the index is (re)built each session by the **SessionStart hook** (`.claude/hooks/session-start.sh`); locally, install once with `pnpm add -g @colbymchenry/codegraph && codegraph init`.

**Use codegraph first** for any navigation question — one call, no whole-file reads:
  * `codegraph query <name>` - Find a symbol's definition(s) with `file:line`
  * `codegraph callers <symbol>` / `codegraph callees <symbol>` - Walk the call graph
  * `codegraph impact <symbol>` - Blast radius before a refactor
  * `codegraph node <symbol> --source` - Read one symbol's source without opening the file
  * `codegraph files [--path <dir>]` - Indexed file tree with language + symbol counts
  * `codegraph sync` - Refresh the index after edits (`.codegraph/` is gitignored)

On-demand CLI (not the always-on MCP server), so it costs no context until invoked. See Core Constraint #11 for mandatory triggers.

## Core Constraints (Must Always Follow)
1. **Russian Copy**: All user-facing labels, placeholders, errors, and toast notifications must be in Russian.
2. **English Comments**: All code comments (inline `#`, `//`, `<!-- -->`, docstrings) must be in English — never Russian or any other language.
3. **Mobile First**: UI must fit narrow layouts; add bottom padding for floating navigation bars. See [docs/frontend.md](docs/frontend.md).
4. **Lint & Type-Check After Changes**: After backend Python changes, run `just backend-lint` and `just backend-typecheck`. After frontend changes, run `just frontend-lint` and `just frontend-check`. Fix all errors before marking the task complete. Tests are optional but allowed — run them when useful; see [docs/testing.md](docs/testing.md).
5. **Architectural Isolation**: The inner layers (`core/`, `application/`) must stay pure — never import from outer layers. No ORM models, concrete adapters (DB gateways, Redis, Telegram, NATS), presentation routers, or external frameworks (no FastAPI/SQLAlchemy in `core/`). All infra goes through abstract ports (`application/ports/`). See [docs/backend.md](docs/backend.md).
6. **SSR & Frontend State Safety**: Never save request-specific state in global/module singletons. Follow the SvelteKit SSR and component guidelines in [docs/frontend.md](docs/frontend.md).
7. **Required Skills by Domain**: Before making changes in a domain, the LLM MUST load its skills:
   * Svelte components/modules (`.svelte`, `.svelte.ts`, `.svelte.js`) → `svelte-code-writer`, `svelte-core-bestpractices`
   * Frontend styling/layout → `tailwind-css-patterns`, `ui-ux-pro-max`
   * Backend/FastAPI → `fastapi`, `clean-ddd-hexagonal`
   * Docker / Infra → `docker-expert`
   * Docs / Writing → `documentation-writer`
   * Third-party library APIs → web-search current docs; never rely on training data for signatures
   * Docker / Infra in cloud (web) sessions → read [docs/claude-cloud.md](docs/claude-cloud.md) (setup script vs. SessionStart hook, image prepull, network access).
   * Read the relevant architecture guide in [docs/](docs/) (`backend.md`, `frontend.md`, `api.md`, `testing.md`) before implementing.
8. **Keep Documentation in Sync**: After any structural, architectural, or path-level change, verify and update `AGENTS.md` and relevant `docs/*.md` before marking the task complete.
   * Added/renamed/deleted a `lib/` submodule (`services/`, `utils/`, etc.)? Update the **Codebase Map**.
   * Changed an important file path referenced in docs (toast store, CLI commands, layout paths)? Update that doc.
   * Introduced a new architectural pattern (DI provider, ports folder, adapter type)? Update the relevant `docs/*.md`.
   * Prefer **documenting patterns and rules** over exact file lists that rot. Keep the Codebase Map high-level.
9. **Clear, Simple Code**: Write straightforward code a junior developer can read unaided. Favor explicit, obvious solutions over clever tricks or dense one-liners. Use descriptive names, small focused functions, and a short comment when intent isn't obvious. If a clever approach is unavoidable, explain why in a comment.
10. **Verify Jinja Templates by Rendering**: After creating or editing a Jinja template, render it with all expected context values and confirm the output before marking the task complete — do not assume it renders correctly.
11. **codegraph Before Grep/Read for Symbols**: With 550+ files, try codegraph before Grep/Glob/Read for any structural question. Triggers: "Where is `X`?" → `query`; "What calls `X`?" → `callers`; "What does `X` call?" → `callees`; "What breaks if I change `X`?" → `impact`; "Show source of `X`" → `node --source`; unfamiliar dir → `files --path <dir>`. Fall back to Grep/Read only when codegraph returns nothing or the question isn't symbol-based (string literal, regex, config value).
12. **Update PR on Subsequent Commits**: After pushing additional commits to an open PR, update the PR title and description to reflect the current cumulative state of all changes — not just the latest commit. Title must stay accurate; description must summarize what the PR now does as a whole.
13. **Comment the Why, Not the What**: Code shows *what* and *how* through clear names and structure; comments exist to explain *why*. Follow these rules (extends #2 English Comments and #9 Clear, Simple Code):
    * **Self-documenting code first.** Reach for a descriptive name, a named constant, or an extracted function *before* a comment. A comment is never an excuse for unclear code — if you can't write a clear comment, the code itself probably needs fixing.
    * **Never restate the code.** Delete comments that merely echo the adjacent line or the symbol's name (`# Setup DI`, `// close modal`, `# Save schedule change` above a `save()` call). Step-by-step narration of self-evident calls is noise.
    * **Do comment the non-obvious:** business-rule reasoning and domain constraints, workarounds / hacks / unidiomatic code, footgun warnings ("don't reorder — deferred constraint relies on this"), performance trade-offs (why not the obvious approach), security rationale (fail-closed, constant-time), and the reason behind a bug fix.
    * **A comment must dispel confusion, not add it.** If it's vague or could mislead, rewrite it precisely or remove it.
    * **No commented-out code.** Delete it — git history is the archive. Keep a snippet only with an explicit note on why it stays.
    * **No untracked TODOs.** Prefer a tracked issue. If a marker is unavoidable, format it `# TODO(<issue-ref>): ...` so it is greppable and owned.
    * **Keep comments in sync with the code.** Update or delete the comment in the *same* change as the code it describes — a stale comment is worse than none.
    * Add links to issues/PRs or external sources when they save the next reader a search.

Respond terse like smart caveman. All technical substance stay. Only fluff die.

Rules:
- Drop: articles (a/an/the), filler (just/really/basically), pleasantries, hedging
- Fragments OK. Short synonyms. Technical terms exact. Code unchanged.
- Pattern: [thing] [action] [reason]. [next step].
- Not: "Sure! I'd be happy to help you with that."
- Yes: "Bug in auth middleware. Fix:"

Default: lite. Switch level: /caveman lite|full|ultra|wenyan
Stop: "stop caveman" or "normal mode"

Auto-Clarity: drop caveman for security warnings, irreversible actions, user confused. Resume after.

Boundaries: code/commits/PRs written normal.
