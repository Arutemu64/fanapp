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
| Env vars   | **Not** injected — the environment's variables read as empty | Injected                                 |
| Use for    | Slow installs that persist on disk               | Work that does not survive the snapshot              |

**Rule of thumb:** if a step writes files (a binary, `.venv`, `node_modules`, a
Docker image layer) it belongs in the setup script; if it starts a process, sets
per-session state, or needs an environment variable it belongs in the hook.

> **Anything needing a credential must go in the hook.** The environment's
> **Environment variables** and **Setup script** fields sit in the same dialog,
> but the variables are injected only into the session — in the setup-script
> phase they are empty, with no error
> ([anthropics/claude-code#63541](https://github.com/anthropics/claude-code/issues/63541)).
> A `docker login`, an authenticated `git clone` or a token-gated download in the
> setup script fails silently; see
> [Docker Hub authentication](#docker-hub-authentication) for how this repo
> handles it.

### Caching lifecycle

The setup script runs the first time a session starts in an environment; the
filesystem is then snapshotted and reused, and the setup step is skipped on
later sessions. It re-runs (rebuilding the cache) only when:

* the **Setup script** field changes,
* the allowed network hosts change, or
* the cache expires (~7 days).

Resuming an existing session never re-runs it. **A dependency bump on the branch
does not trigger a rebuild** — which is why dependency installs live in the hook
(see below), not the setup script.

> The setup script lives in the cloud environment UI, not the repo.
> `.claude/setup.sh` is tracked here for review and as the source of truth; you
> must paste it into the environment's **Setup script** field for it to run, and
> repaste it after every change — which is also what rebuilds the snapshot.
> Nothing detects a stale paste automatically, so treat "edit `setup.sh`" and
> "repaste the field" as one step.

## What runs where

**`.claude/setup.sh`** — tooling the cloud lacks but a laptop has, plus image
prepulls (all persist in the snapshot). Every install is best-effort: a
non-zero exit from the setup script means *no session starts* in this
environment until the field or the cache changes, so a transient apt/PyPI/npm
failure must not propagate. The script ends by checking
`just uv node pnpm hadolint` and naming anything missing in the setup log,
rather than failing the build.

* `just` (apt), an upgraded `uv` (PyPI), Python 3.14 — the base image's `uv` is
  too old for stable 3.14 and can't self-update here (GitHub installer 403s).
* Node 24 via `nvm` (already on the image) — the base image's system Node is
  22; the official Node/nvm installers both 403 here.
* Docker image prepulls (`postgres:18.4-alpine`, `valkey/valkey:9.1-alpine`, `hadolint/hadolint`, see below). Anonymous — the `docker login` lives in the hook, see [Docker Hub authentication](#docker-hub-authentication).
* a `hadolint` shim in `/usr/local/bin` — hadolint ships only as a GitHub
  release binary (403 here) and is not in apt, so the shim runs the prepulled
  image instead. It bind-mounts the caller's working directory read-only at the
  same path and matches the caller's uid/gid, which is what lets hadolint
  resolve relative Dockerfile arguments and discover `.hadolint.yaml` exactly as
  the native binary does. `just dockerfile-lint` and the pre-commit
  `hadolint` hook therefore both work unchanged, calling a plain `hadolint` the
  same way they do on a laptop where `mise` supplies the real binary.
* CodeGraph (`@colbymchenry/codegraph`, the code-navigation graph — see
  [AGENTS.md](../AGENTS.md) "Code navigation") — installed from the **npm
  registry**, not its recommended `curl|sh` installer, which pulls a runtime
  from GitHub releases this environment blocks (same reason `just`/`uv`/`node`
  above skip their GitHub installers). The tool is fully local (bundled SQLite,
  no runtime network). Only the binary is installed and persisted in the
  snapshot here — the index itself is built by the hook instead (see below),
  since a snapshot is reused across sessions on different branches/commits and
  an index baked in at environment-creation time could reflect the wrong ref.
  The binary is also symlinked into `/usr/local/bin` so the project's
  `.mcp.json` server (bare `command: codegraph`) starts even when Claude Code
  spawns MCP servers with a PATH that predates the hook's nvm/Node-24
  additions — the npm global bin otherwise lives off the base PATH.

**`.claude/hooks/session-start.sh`** — work that must run each session because it
does not survive the snapshot:

* `uv sync` / `pnpm install` — kept here so a dependency bump is picked up
  without an environment rebuild; near-instant when the lockfile is unchanged.
* building/refreshing the CodeGraph index — `codegraph sync` updates an
  existing index incrementally so code-navigation queries stay accurate;
  falls back to a full `codegraph init` when no index exists yet, which is
  every fresh session (the setup script only installs the binary, not an
  index) until this hook builds one. Kept here (not in the setup script) for
  the same reason as the dependency syncs: the index is per-branch state that
  must track the code a session actually has, not whatever ref happened to be
  checked out when the snapshot was built.
* starting `dockerd` — a process, never cached; restarted every session.
* `docker login` to Docker Hub — the environment's variables reach the session
  but not the setup script, so this is the only place it can run; see
  [Docker Hub authentication](#docker-hub-authentication).
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

The cloud daemon's in-session job is autogenerating Alembic migrations against a
throwaway Postgres (`just backend-generate-auto`). The `@pytest.mark.integration`
suite runs against real Postgres + Valkey via testcontainers (see
[testing.md](testing.md)), but per AGENTS.md it is **left to CI** even here —
it's slow, and a green run in CI is the gate that matters — so a session does not
run it. The setup script still prepulls the images it *would* need, so the option
exists and CI-parity images are cached; each is baked into the snapshot and on
disk at session start:

* `postgres:18.4-alpine` — pinned (not a floating minor tag) to match
  production (`docker-compose.yml`) exactly; used by
  `just backend-generate-auto`, and shared with the testcontainers integration
  suite (`backend/tests/fixtures/db_provider.py`). One image everywhere avoids
  running against a different Postgres build than production — Alpine's
  musl libc has different collation/locale behavior than glibc-based images,
  so a mismatched variant could hide or fabricate sorting bugs.
* `valkey/valkey:9.1-alpine` — the testcontainers image
  `backend/tests/fixtures/db_provider.py` boots for `@pytest.mark.integration`
  tests, matching what CI (`.github/workflows/ci.yml`) uses; prepulled for
  parity though the suite itself runs in CI, not in-session.
* `hadolint/hadolint` — backs the `hadolint` shim above, so the Dockerfile gate
  (`just dockerfile-lint`) runs in-session instead of only in CI. Pinned to the same version
  as `mise.toml` and the `.pre-commit-config.yaml` rev (docs/dependencies.md);
  the `renovate.json` `hadolint` group bumps all three together.

Only the daemon (a process) is restarted per session by the hook; containers
themselves are booted and torn down on demand by `just backend-generate-auto`
(or by a test run, should one be invoked). The hook
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
need no containers and still run in-session per AGENTS.md. `just dockerfile-lint`
does need the daemon, since the `hadolint` shim is container-backed.

### Docker Hub authentication

Docker Hub caps **anonymous** pulls (~100 / 6h per egress IP), which a shared
cloud egress hits quickly. Set `DOCKERHUB_USER` and `DOCKERHUB_TOKEN` (a scoped,
read-only access token — not your password) in the environment's variables. The
**SessionStart hook** runs `docker login` (token via stdin) right after it starts
`dockerd`, so every pull a session makes — testcontainers, the `hadolint` shim,
`just backend-generate-auto` — is authenticated.

> The login cannot live in the setup script, and its `~/.docker/config.json` is
> **not** part of the snapshot: the environment's variables are injected into the
> session only, so in the setup-script phase they read as empty and the login
> silently does nothing
> ([anthropics/claude-code#63541](https://github.com/anthropics/claude-code/issues/63541)).
> That is why the three prepulls are anonymous and why the login is redone each
> session.

> A token in an env var is **not** used until something runs `docker login` —
> setting the variable alone does nothing.

Both are **best-effort**: a remaining cap, a missing token or a bad one degrades
a pull to a lazy, anonymous pull at first use rather than failing environment
creation or session start.

> Cloud environments have no secrets store yet; environment variables are visible
> to anyone who can edit the environment. Use a revocable, least-privilege token.
