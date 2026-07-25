# Dependency Pinning & Renovate

The rule: **one external dependency, one pinned version, everywhere.** When the
same Docker image or tool is pinned in more than one file, every site names the
*same exact* version and they all move together in a single change. A floating
tag or a stray unpinned install (`pip install --upgrade uv`) silently
reintroduces drift, and drift here means a test, a migration or a lint gate runs
against a different build than production.

If two sites genuinely cannot share a version (different platform or major
requirements), say why in a comment **at each site** rather than leaving the
mismatch unexplained.

## The shared pins

| Dependency | Pinned in |
| --- | --- |
| `postgres:18.4-alpine` | `docker-compose.yml`, `backend/scripts/generate_migration.py`, `backend/tests/fixtures/db_provider.py` |
| `uv` | `mise.toml`, `backend/pyproject.toml` (`[tool.uv]`), `backend/Dockerfile`, `.claude/setup.sh`, CI (`setup-uv` input) |
| `hadolint` | `mise.toml`, `.pre-commit-config.yaml` (`rev`), the image behind the `.claude/setup.sh` shim |
| `pnpm` | `mise.toml`, `frontend/package.json` (`packageManager`), CI (`pnpm/action-setup` input) |
| `node` | `mise.toml`, `frontend/Dockerfile`, CI (`setup-node`) |

Prefer an exact pin over a floating tag so every consumer resolves identically.

## How Renovate enforces it

[`renovate.json`](../renovate.json) automates the bump-together part:

* **Grouped `packageRules`** (`uv`, `postgres`, `node`, `pnpm`, `hadolint`)
  consolidate each shared pin into a single PR, so no site is left behind.
* **`customManagers`** (regex) cover the pins the built-in managers cannot see:
  the Postgres image literals in `backend/scripts/generate_migration.py` and
  `backend/tests/fixtures/db_provider.py`; the uv pin in `.claude/setup.sh`,
  `backend/pyproject.toml` and the CI `setup-uv` input; and the pnpm `version`
  input to `pnpm/action-setup` in CI. That last one stays explicit because
  action-setup v6 cannot read `packageManager` from the subdirectory
  `frontend/package.json` ([pnpm/action-setup#227](https://github.com/pnpm/action-setup/issues/227)).
* Third-party GitHub Actions are pinned to commit SHAs
  (`helpers:pinGitHubActionDigests`) with a `# vX` tag comment.

**Adding a new pin site for an already-tracked dependency means extending the
matching group or custom manager in the same change** — otherwise Renovate bumps
the other sites and silently reintroduces the drift this rule exists to prevent.

### Rule order matters

`packageRules` are applied in order and a later rule overrides an earlier one.
The broad CI-minute batching groups (`github actions`, `dev tooling`,
`backend dependencies`) must therefore stay **above** the shared-pin groups —
otherwise a shared pin gets swallowed into a batch PR instead of bumping
together in its own.

## Versioning the app

The same "one version, one place" rule applies to the app's own version. There
are exactly **two** identifiers, and they answer different questions.

### Release version — *which release is this?*

One number for the whole repo, held in `backend/pyproject.toml` (`[project]
version`) and mirrored by a `vX.Y.Z` git tag.

The bump and the tag are two steps, not one. Bump on a branch, merge it, then
tag `main`:

```bash
# on the branch
# edit backend/pyproject.toml -> version = "2.1.0"
just backend-generate-openapi          # spec + uv.lock follow
git commit -am "Release 2.1.0"

# after the PR merges, on main
git tag -a v2.1.0 -m "Release 2.1.0"
git push origin v2.1.0                 # this publishes 2.1.0, 2.1 and 2 to GHCR
```

Tagging the branch commit instead would publish images from unmerged code, and
a squash-merge would leave the tag pointing at a commit `main` never received.

It lives in `backend/pyproject.toml` because that is the only manifest that must
carry a version anyway and can be read back at runtime — `common/version.py`
resolves it from the installed distribution, so `FastAPI(version=…)` and the
committed `shared/openapi/openapi.json` cannot drift off it. `backend/uv.lock`
records it as well, which is why the regeneration step above is not optional:
a lock left behind fails the image build on `uv sync --locked`.

`frontend/package.json` deliberately stays at `0.0.0`. The frontend is
`private`, is never installed by anyone, and is deployed from the same commit as
the backend — a second number there would only be a second thing to forget.
Independent SemVer per package buys nothing when no consumer ever chooses a
version: the API client is regenerated in-repo (`just frontend-generate-api`) and
both images ship together.

Keep tags SemVer-shaped: the publish workflow derives image tags with
`type=semver`, so a `v1.2.3` tag publishes `1.2.3`, `1.2` and `1`, while a
free-form tag publishes none of them.

### Build id — *which build is running?*

The commit SHA. This, not the release version, is what a deploy pins and what a
bug report needs.

| Where | How it gets there |
| --- | --- |
| Image tag (`sha-1a2b3c4`) | `type=sha` in the publish workflow; pinned via `IMAGE_TAG` |
| Backend Sentry release | `APP_BUILD` build arg → image `ENV` → `EnvConfig.build` |
| Frontend Sentry release | `SENTRY_RELEASE` build arg (source-map upload) |
| Profile footer | `PUBLIC_APP_VERSION` build arg, baked into the bundle |

All four come from the same `github.sha`, so one deploy is one release across
both services. Sentry
([naming releases](https://docs.sentry.io/product/releases/naming-releases/))
recommends exactly this for VCS-backed projects.

`APP_BUILD` stays **commented out** in `.env.example`. Compose `env_file` values
are injected into the container and override image `ENV`, so an empty
`APP_BUILD=` line would erase the value the workflow baked in.

Building from source locally leaves both unset — the footer line hides itself
and Sentry gets no release, which is the honest answer for a build that has no
published identity.

### What is deliberately *not* versioned

The HTTP API has no `/v1` URL prefix and does not need one. Path versioning
exists to let an old client keep working against a new server; with a single
first-party client deployed in the same step as the backend, that window never
opens.
