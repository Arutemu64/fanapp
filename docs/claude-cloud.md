# Claude Code Cloud Environment

How this repo is provisioned for [Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web).
Cloud sessions run in a fresh Anthropic-managed VM with the repo cloned; the
filesystem is snapshotted and cached between sessions. This page documents the
two provisioning mechanisms and the project-specific choices in each. It is only
relevant to web/remote sessions — local development uses your own toolchain.

## Setup script vs. SessionStart hook

Two mechanisms run at session start; they live in different places and run on
different schedules.

|            | Setup script (`.claude/setup.sh`)                | SessionStart hook (`.claude/hooks/session-start.sh`) |
| ---------- | ------------------------------------------------ | ---------------------------------------------------- |
| Attached to| The cloud environment                            | The repository                                       |
| Configured | Cloud environment UI (**Setup script** field)    | `.claude/settings.json`                              |
| Runs       | **Once**, at environment creation; result cached | **Every** session (startup + resume)                 |
| Use for    | Slow installs that persist on disk               | Work that does not survive the snapshot              |

**Rule of thumb:** if a step writes files (a binary, `.venv`, `node_modules`, a
Docker image layer) it belongs in the setup script; if it starts a process or
sets per-session state it belongs in the hook.

### Caching lifecycle

The setup script runs the first time a session starts in an environment; the
filesystem is then snapshotted and reused, and the setup step is skipped on
later sessions. It re-runs (rebuilding the cache) only when:

* the setup script changes,
* the allowed network hosts change, or
* the cache expires (~7 days).

Resuming an existing session never re-runs it. **A dependency bump on the branch
does not trigger a rebuild** — which is why dependency installs live in the hook
(see below), not the setup script.

> The setup script lives in the cloud environment UI, not the repo. `.claude/setup.sh`
> is tracked here for review and as the source of truth; you must paste/refresh
> it into the environment's **Setup script** field for it to run. Keep the two in
> sync — drift is detected automatically: at environment creation the setup
> script records a hash of the repo's `.claude/setup.sh`
> (`~/.cache/fanfan-setup.hash`), and the SessionStart hook warns at session
> start whenever the branch's copy no longer matches. On that warning, repaste
> the file into the **Setup script** field (which rebuilds the snapshot).

## What runs where

**`.claude/setup.sh`** — tooling the cloud lacks but a laptop has, plus image
prepulls (all persist in the snapshot):

* `just` (apt), an upgraded `uv` (PyPI), Python 3.14 — the base image's `uv` is
  too old for stable 3.14 and can't self-update here (GitHub installer 403s).
* Node 24 via `nvm` (already on the image) — the base image's system Node is
  22; the official Node/nvm installers both 403 here.
* `docker login` + Docker image prepulls (`postgres:18.4-alpine`, `valkey/valkey:9.1-alpine`, see below).
* CodeGraph (`@colbymchenry/codegraph`, the code-navigation graph — see
  [AGENTS.md](../AGENTS.md) "Code Navigation") — installed from the **npm
  registry**, not its recommended `curl|sh` installer, which pulls a runtime
  from GitHub releases this environment blocks (same reason `just`/`uv`/`node`
  above skip their GitHub installers). The tool is fully local (bundled SQLite,
  no runtime network). A baseline index is seeded into `.codegraph/` here so the
  hook only has to `sync` the branch delta; both the binary and the seed persist
  in the snapshot.

**`.claude/hooks/session-start.sh`** — work that must run each session because it
does not survive the snapshot:

* `uv sync` / `pnpm install` — kept here so a dependency bump is picked up
  without an environment rebuild; near-instant when the lockfile is unchanged.
* `codegraph sync` — refreshes the seeded index against the current branch so
  code-navigation queries stay accurate; falls back to a full `codegraph init`
  if the snapshot has no seeded index. Kept here (not in the setup script) for
  the same reason as the dependency syncs: the index is per-branch state that
  must track the code, so a session on a different branch or a newer commit
  re-parses only the delta.
* starting `dockerd` — a process, never cached; restarted every session.
* per-session env vars written to `$CLAUDE_ENV_FILE` (`PATH`, including
  activating the nvm-installed Node 24 over the base image's system Node 22).

## Network access

Package registries (npm, PyPI, …) and Docker Hub — including its blob CDN,
`production.cloudflare.docker.com` — are on the default **Trusted** allowlist
([current list](https://code.claude.com/docs/en/claude-code-on-the-web#default-allowed-domains)).
`ghcr.io` itself is Trusted too, but its blob CDN,
`pkg-containers.githubusercontent.com`, is not — if a `ghcr.io` pull
authenticates and then 403s mid-download, set the environment's network access
to **Custom** (keep the default list checked) and add:

```text
pkg-containers.githubusercontent.com  # GHCR layer blobs
```

Or use **Full** access. Changing the allowlist rebuilds the cache on the next
fresh session. (A 403 here is a network-allowlist problem, distinct from the
Docker Hub rate-limit below.)

## Docker images

The cloud agent flow does two container-bound tasks: autogenerating Alembic
migrations against a throwaway Postgres, and running the `@pytest.mark.integration`
suite against real Postgres + Valkey via testcontainers (see
[testing.md](testing.md)). So the setup script prepulls two images, baked into
the snapshot and on disk at session start:

* `postgres:18.4-alpine` — pinned (not a floating minor tag) to match
  production (`docker-compose.yml`) exactly; used both by
  `just backend-generate-auto` and by the testcontainers integration suite
  (`backend/tests/fixtures/db_provider.py`). One image everywhere avoids
  running tests against a different Postgres build than production — Alpine's
  musl libc has different collation/locale behavior than glibc-based images,
  so a mismatched variant could hide or fabricate sorting bugs.
* `valkey/valkey:9.1-alpine` — the testcontainers image
  `backend/tests/fixtures/db_provider.py` boots for `@pytest.mark.integration`
  tests, matching what CI (`.github/workflows/ci.yml`) uses.

Only the daemon (a process) is restarted per session by the hook; containers
themselves are booted and torn down on demand by `just backend-generate-auto`
or a test run (`just backend-test` / `backend-test-integration`). The hook
also sets `TESTCONTAINERS_RYUK_DISABLED=true`, matching CI — dockerd itself
doesn't survive between sessions and the fixtures stop their own containers in
`finally:` blocks, so the Ryuk cleanup reaper isn't needed and skipping it
avoids pulling/running an extra container per session.

Everything else is deliberately **not** prepulled and left to CI:

* the rest of the compose stack (`nats`, db-backup) — not needed for Alembic
  autogenerate or the test suite.
* Dockerfile bases (`uv`, `debian`, `node`, `nginx`) and the project's own
  `ghcr.io/arutemu64/fanapp-*` images — image builds run in
  `docker-publish.yml`.

Fast local checks (`just backend-lint`, `backend-typecheck`, `frontend-lint`)
need no containers and still run in-session per AGENTS.md.

### Docker Hub authentication

Docker Hub caps **anonymous** pulls (~100 / 6h per egress IP), which a shared
cloud egress hits quickly. Set `DOCKERHUB_USER` and `DOCKERHUB_TOKEN` (a scoped,
read-only access token — not your password) in the environment's variables; the
setup script runs `docker login` (token via stdin) before pulling, which raises
the cap. The resulting `~/.docker/config.json` persists in the snapshot, so
sessions' own lazy pulls are authenticated too.

> A token in an env var is **not** used until something runs `docker login` —
> setting the variable alone does nothing.

The prepull is **best-effort**, so a remaining cap or a bad token degrades a
pull to a lazy pull at first use rather than failing environment creation.

> Cloud environments have no secrets store yet; environment variables are visible
> to anyone who can edit the environment. Use a revocable, least-privilege token.
