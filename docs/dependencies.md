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
| `uv` | `mise.toml`, `backend/pyproject.toml` (`[tool.uv]` and the `uv_build` floor in `[build-system]`), `backend/Dockerfile`, `.claude/setup.sh`, CI (`setup-uv` input) |
| `hadolint` | `mise.toml`, `.pre-commit-config.yaml` (`rev`), the image behind the `.claude/setup.sh` shim |
| `pnpm` | `mise.toml`, `frontend/package.json` (`packageManager`), `frontend/Dockerfile` (`PNPM_VERSION`), `.claude/setup.sh`, CI (`pnpm/action-setup` input) |
| `node` | `mise.toml`, `frontend/Dockerfile`, `.claude/setup.sh`, CI (`setup-node`) |
| `python` | `mise.toml`, `backend/.python-version`, `backend/pyproject.toml` (`requires-python` floor) |

Prefer an exact pin over a floating tag so every consumer resolves identically.

`just` is pinned too (`mise.toml`), but it is deliberately **not** in the table
above: `mise.toml` is its only exact-pin site, so there is nothing to keep in
lockstep and it needs no Renovate group — the built-in `mise` manager bumps it
directly as a normal review PR. The cloud setup (`.claude/setup.sh`) installs it
with `apt-get install just`, which cannot pin a version: that is the one
cloud-install exception left untracked, unlike the uv, pnpm and node pins in the
same script, which are exact and Renovate-tracked.

## How Renovate enforces it

[`renovate.json`](../renovate.json) automates the bump-together part:

* **Grouped `packageRules`** (`uv`, `postgres`, `node`, `pnpm`, `hadolint`,
  `python`) consolidate each shared pin into a single PR, so no site is left
  behind. A shared pin whose sites are read by different managers — and so by
  different datasources — needs its group most: `python` is seen three times
  (mise, pyenv, pep621) and would otherwise arrive as three PRs that can settle
  on different versions.
* **`customManagers`** (regex) cover the pins the built-in managers cannot see:
  the Postgres image literals in `backend/scripts/generate_migration.py` and
  `backend/tests/fixtures/db_provider.py`; the hadolint image behind the
  `.claude/setup.sh` shim; the uv, pnpm and node pins in `.claude/setup.sh`
  (the `npm install -g pnpm@…` and `NODE_VERSION=…` lines the session actually
  runs — distinct from the postgres/valkey prepull literals in that file, which
  are cache hints, not functional pins, so they are left untracked); the uv pin
  in `backend/pyproject.toml`.
* **A pin inside a Dockerfile that isn't a `FROM` line gets an inline
  annotation, not a regex manager.** The `dockerfile` manager reads `FROM` lines
  only, so `ENV PNPM_VERSION` in `frontend/Dockerfile` was invisible to it and
  drifted a patch behind the other pnpm sites. It now carries a
  `# renovate: datasource=npm depName=pnpm versioning=npm` comment, read by the
  first-party `customManagers:dockerfileVersions` preset. Renovate's own
  [regex-manager docs](https://docs.renovatebot.com/modules/manager/regex/)
  prefer this to a bespoke rule — one manager covers every annotated line
  instead of one rule per pin, and the annotation documents the constraint in
  the file a reader is already looking at. The comment must sit on the line
  **directly above** the `ENV`/`ARG`; a blank line between them breaks the
  match.
* **Version inputs to setup actions need no custom manager.** The
  `github-actions` manager reads supported `uses … with` inputs itself, so the
  `setup-uv`, `pnpm/action-setup` and `setup-node` version inputs in `ci.yml`
  are extracted natively — as `astral-sh/uv`, `pnpm` and `node`, which is why
  the `uv` group matches `astral-sh/uv` as well as `uv`. Adding a regex manager
  for one of those lines gives the same string two owners with two datasources,
  and then two disagreeing answers about the latest version. The pnpm input
  still has to *exist* in the workflow, though: action-setup v6 cannot read
  `packageManager` from the subdirectory `frontend/package.json`
  ([pnpm/action-setup#227](https://github.com/pnpm/action-setup/issues/227)).
* Third-party GitHub Actions are pinned to commit SHAs
  (`helpers:pinGitHubActionDigests`) with a `# vX` tag comment.

**Adding a new pin site for an already-tracked dependency means extending the
matching group or custom manager in the same change** — otherwise Renovate bumps
the other sites and silently reintroduces the drift this rule exists to prevent.

### The backstop: CI builds the images

Grouping is best-effort, not a guarantee. A group only carries the sites that
had an update *when Renovate cut the branch*, and its members come from
different datasources (PyPI, GitHub releases, the GHCR tag list) that learn
about a release at different moments — so a member can be left at the old
version in an otherwise correct-looking PR. [PR #360](https://github.com/Arutemu64/fanapp/pull/360)
did exactly that: it moved four of the five `uv` sites to `0.11.30` and left the
`ghcr.io/astral-sh/uv` builder tag in `backend/Dockerfile` at `0.11.29`, which
`[tool.uv] required-version` then rejected inside the image build.

So `ci.yml` has an `images` job that builds both images (without pushing) on any
change to `backend/**`, `frontend/**` or a `Dockerfile`. Before it existed the
only real build ran in `docker-publish.yml` *after* merge, which meant a broken
build was discovered as a red `main` that could no longer publish. **Review a
shared-pin PR against the table above rather than trusting the diff to be
complete** — the `images` job catches a drifted pin only when the drift actually
breaks a build.

### One PR per dependency

Bumps are **not** batched into weekly grouped PRs. This repo is public and every
CI job runs on a standard GitHub-hosted runner, which GitHub does not meter, so
batching saves nothing and costs atomicity: a grouped branch passes or fails as a
whole, Renovate cannot split it afterwards, and one bad bump then holds back
every other update in the batch. One PR per dependency means one revertable
commit per dependency instead.

The six shared-pin groups are the exception, and they are not an economy
measure — they exist so that every site of one pin moves in lockstep.

### What automerges, and what only looks like tooling

Dev tooling automerges on minor/patch because it fails loudly in CI. That
argument does not extend to everything in `frontend/package.json`
`devDependencies`: SvelteKit convention puts `svelte`, `@sveltejs/*`, `vite`,
`tailwindcss` and `flowbite*` there, but their output ships in the bundle, and a
CSS or component-library minor can move the layout with every gate green. Those
are carved back out into review PRs; `eslint`, `prettier`, `typescript`,
`svelte-check`, `vitest` and `openapi-typescript` keep automerging.

### Rule order matters

`packageRules` are applied in order and a later rule overrides an earlier one.
Two consequences to keep in mind when editing:

* The shipped-bundle carve-out must stay **below** the `devDependencies`
  automerge rule it is carving out of, or it silently does nothing.
* The shared-pin groups stay **last**, so nothing above them can claim a pinned
  dependency for a different `groupName`.

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

#### Which number moves

SemVer's own rules are defined against a public API — the spec requires that
"Software using Semantic Versioning MUST declare a public API", and grades
MAJOR/MINOR/PATCH by backward compatibility with it. This repo has no such API:
nobody installs `fanfan`, and the only client is regenerated in-repo and
deployed in the same step as the backend. So the number is a changelog marker,
not a compatibility promise, and it is keyed to the one boundary that does
exist — **the deploy**, meaning an image against the server's `.env` and
database.

| Bump | When |
| --- | --- |
| PATCH | `just deploy` and nothing else: fixes, dependency bumps, refactors, copy. |
| MINOR | Same, but attendees see something new — a feature, a page, a notification type. |
| MAJOR | `just deploy` alone is **not** enough: a new required env var, a migration that cannot be rolled back, changed deployment topology. |

MAJOR is the one that earns its keep: it is the only version signal that changes
what a human has to *do*, and the failure it guards against — deploying blind
into a broken app on the morning of the convention — is a real one here.

(`2.0.0` is an exception to that rule and says so: the 1.x line was the original
Telegram-bot project, so the major marks lineage, not an operational break.)

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
