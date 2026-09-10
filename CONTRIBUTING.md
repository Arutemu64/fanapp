# Contributing

Thanks for helping with the FAN FAN companion app. This is the short version
for humans; the canonical, detailed rules live in [`AGENTS.md`](AGENTS.md) and
the guides under [`docs/`](docs/). **Where this file and `AGENTS.md` disagree,
`AGENTS.md` wins** — it's the source of truth, and this page only points at it.

## Getting started

You'll need [`just`](https://github.com/casey/just), Docker, `uv` (backend) and
`pnpm` (frontend). Then:

```bash
just bootstrap    # .env + generated secrets + VAPID keys (idempotent)
just run-dev      # full stack via Docker Compose
```

To run one side on the host, start the backing services with `just run-infra`
and use `just backend-dev` / `just frontend-dev`. The full command list is in
[`AGENTS.md`](AGENTS.md) ("Stack & commands").

## Before you push

Run the gate for what you touched (CI runs these regardless):

- **Backend** — `just backend-lint` and `just backend-typecheck`
- **Frontend** — `just frontend-lint` and `just frontend-check`
- **Dockerfile** — `just dockerfile-lint`

Whether a change needs a *new* test is a judgement call — see
[`docs/testing.md`](docs/testing.md).

## Language

User-facing copy is **Russian**; code, comments, docs, and issues/PRs are
**English**. See the language rule in [`AGENTS.md`](AGENTS.md).

## Commits & pull requests

- We **squash-merge**, so the **PR title** *is* the commit that lands on `main`.
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
