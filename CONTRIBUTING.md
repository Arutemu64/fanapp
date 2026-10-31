# Contributing

Thanks for helping with the FAN FAN companion app. This is the short version
for humans; the canonical, detailed rules live in [`AGENTS.md`](AGENTS.md) and
the guides under [`docs/`](docs/). **Where this file and `AGENTS.md` disagree,
`AGENTS.md` wins** — it's the source of truth, and this page only points at it.

## Getting started

Install Docker and the tools pinned in [`mise.toml`](mise.toml) (`mise install`
if you use mise). From the repository root:

```bash
just setup       # install dependencies, create .env and generate local secrets
just dev         # full stack in Docker with hot reload; includes migrations and worker
```

Open http://localhost:3000. No external credentials are required: use email login
and read its code in the API logs (`docker compose logs api`). In another
terminal, run `just demo` to populate an empty database with programme and voting
data. Setup preserves existing configuration; demo seeding is safe to repeat.

For host processes with Docker backing services, follow the
[advanced setup](README.md#advanced-run-app-processes-on-the-host).
Optional Git hooks: `just backend-setup-hooks`.

## Finding and maintaining commands

Run `just` to list commands by group, or `just --group checks --list` to show
only checks. Existing names such as `run-dev` and `backend-lint` remain aliases.

Keep recipes in the root `justfile`. Use native [aliases](https://just.systems/man/en/aliases.html)
for alternate names and [dependencies](https://just.systems/man/en/dependencies.html)
for ordered steps, so checks share one invocation. Use `quote()` for text arguments
passed to the shell. Format changes with `just --fmt` and verify with
`just --fmt --check` (using the version pinned in `mise.toml`). CI runs this check
when the task file or tool pins change.

Routine Python commands and hooks use `uv run --locked`: update `uv.lock`
explicitly when changing dependencies. `just dev --build` rebuilds development
images; `just run-prod --no-build` skips rebuilding production images.

## Before you push

Run the check for what you touched. These commands do not fix source files:

- **Backend** — `just backend-check` (format, lint, types and import boundaries)
- **Frontend** — `just frontend-check` (format, lint and types)
- **Dockerfile** — `just dockerfile-lint`
- **Markdown or YAML outside `frontend/`** — `just root-lint`

To fix formatting, use `just backend-format`, `just frontend-format` or
`just root-format`. `just backend-fix` also applies Ruff fixes and sorts dependencies.
For types alone, use `just backend-typecheck` or `just frontend-typecheck`.
`just backend-lint` remains a check-only alias for the full backend gate.

Run the tests relevant to your change (`just backend-test`, `just frontend-test`,
or `just frontend-e2e`). See [`docs/testing.md`](docs/testing.md) for when to add tests.

## Language

User-facing copy is **Russian**; code, comments, docs, and issues/PRs are
**English**. See the language rule in [`AGENTS.md`](AGENTS.md).

## Commits & pull requests

- We **squash-merge**, so the **PR title** _is_ the commit that lands on `main`.
  It's linted as Conventional Commits — `type(scope): subject` with a lowercase
  subject — by CI. Allowed types and scopes are in [`AGENTS.md`](AGENTS.md)
  ("Commit & PR titles").
- Open the PR against `main`, fill in the
  [PR template](.github/pull_request_template.md), and link the issue with
  `Closes #123`.
- Deferring something? Leave a self-explaining `TODO`, or open an issue if it's
  cross-cutting or needs design — the promotion rule is in `AGENTS.md`.

## Reporting bugs & requesting features

Use the [issue forms](.github/ISSUE_TEMPLATE/). Please **don't** file security
problems as public issues — follow [`SECURITY.md`](SECURITY.md) instead.
