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
> sync.

## What runs where

**`.claude/setup.sh`** — tooling the cloud lacks but a laptop has, plus image
prepulls (all persist in the snapshot):

* `just` (apt), an upgraded `uv` (PyPI), Python 3.14 — the base image's `uv` is
  too old for stable 3.14 and can't self-update here (GitHub installer 403s).
* Node 24 via `nvm` (already on the image) — the base image's system Node is
  22; the official Node/nvm installers both 403 here.
* `docker login` + a single Docker image prepull (`postgres:18-alpine`, see below).

**`.claude/hooks/session-start.sh`** — work that must run each session because it
does not survive the snapshot:

* `uv sync` / `pnpm install` — kept here so a dependency bump is picked up
  without an environment rebuild; near-instant when the lockfile is unchanged.
* starting `dockerd` — a process, never cached; restarted every session.
* per-session env vars written to `$CLAUDE_ENV_FILE` (`PATH`, including
  activating the nvm-installed Node 24 over the base image's system Node 22).

## Network access

Package registries (npm, PyPI, …) are on the default **Trusted** allowlist.
Docker image **layers** are served from registry blob CDNs that may not be — if
a pull authenticates and then 403s mid-download, set the environment's network
access to **Custom** (keep the default list checked) and add:

```text
production.cloudfront.docker.com      # Docker Hub layer blobs
pkg-containers.githubusercontent.com  # GHCR layer blobs
```

Or use **Full** access. Changing the allowlist rebuilds the cache on the next
fresh session. (A 403 here is a network-allowlist problem, distinct from the
Docker Hub rate-limit below.)

## Docker images

The cloud agent flow does one container-bound task: autogenerating Alembic
migrations against a throwaway Postgres. So the setup script prepulls a **single**
image — `postgres:18-alpine`, matching production (`docker-compose.yml`) and the
CI drift gate — baked into the snapshot and on disk at session start. Only the
daemon (a process) is restarted per session by the hook; the container itself is
booted and torn down on demand by `just backend-generate-auto` (see
[backend.md](backend.md)).

Everything else is deliberately **not** prepulled and left to CI:

* integration-test images (`postgres:18.4`, `redis:…` via testcontainers) — the
  full `pytest` suite runs in `.github/workflows/ci.yml`, not in cloud sessions.
* the rest of the compose stack (`nats`, `valkey`, db-backup) — not needed to
  generate a schema diff.
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

The prepull is **best-effort**, so a remaining cap or a bad token degrades the
single `postgres:18-alpine` pull to a lazy pull at first use rather than
failing environment creation.

> Cloud environments have no secrets store yet; environment variables are visible
> to anyone who can edit the environment. Use a revocable, least-privilege token.
