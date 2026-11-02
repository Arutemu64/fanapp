# Dependency Pinning & Renovate

Use one authoritative version per tool. Consumers read that file when their
installer supports it. Keep remaining exact pins equal, including image digests,
and change them in one PR. `just check-toolchain` enforces this offline before
project dependencies are installed.

## Shared pins

| Dependency | Authoritative declaration | Other consumers                                                                           |
| ---------- | ------------------------- | ----------------------------------------------------------------------------------------- |
| Python     | `mise.toml`               | `backend/.python-version`, read by uv in CI and Docker                                    |
| Node       | `mise.toml`               | Frontend Dockerfile; CI uses `node-version-file: mise.toml`                               |
| pnpm       | `mise.toml`               | Frontend `packageManager` and Dockerfile `PNPM_VERSION`; CI reads `frontend/package.json` |
| uv         | `mise.toml`               | Backend `[tool.uv] required-version` and Dockerfile; CI reads `backend/pyproject.toml`    |
| Postgres   | `docker-compose.yml`      | Migration generator and integration fixture, including the digest                         |
| hadolint   | `mise.toml`               | Pre-commit hook; CI downloads the mise version with checksum verification                 |
| gitleaks   | `.pre-commit-config.yaml` | CI `GITLEAKS_VERSION`                                                                     |

`just` also has one pin in `mise.toml`, read by CI. Renovate's validator and its
Node runtime live together in `.github/renovate/mise.toml`. Renovate 44 declares
Node `^24.11.0` support, so this tool uses Node 24 independently of the Node 26
application. Both the CI validator step and `just renovate-check` read that
isolated toolchain. Keep its runtime rule in Renovate aligned with upstream's
[engines](https://github.com/renovatebot/renovate/blob/main/package.json) when
upgrading the validator.

`requires-python` is a compatibility floor, so it stays at `>=3.14` while runtime
patch pins move. `uv_build` is a bounded build requirement, not an exact runtime
pin. Its floor travels with uv updates because Astral releases them together;
the checker does not confuse either requirement with an equality pin.

## Check and update pins

Run these from the repository root:

```sh
just check-toolchain
just test-dependencies
just renovate-check
```

`check-toolchain` and its regression tests use only Python 3.11+ and the standard
library. They run before installation in the required `Dependency configuration`
CI job. `CI success` waits for that job. The same check runs as a local prek hook
on every commit. It checks every occurrence of each registered version declaration
and fails when a file or expected pin disappears. Each error names the file and
expected value. Workflow syntax is checked by actionlint; the consistency checker
focuses on the version declarations listed above.

The validator is based on the explicit site registry in
[Airflow's toolchain check](https://github.com/apache/airflow/blob/main/scripts/ci/prek/check_go_version_in_sync.py).
[Squareone](https://github.com/lsst-sqre/squareone/blob/main/packages/repo-scripts/src/validate-docker-versions.js)
also compares package-manager pins with Dockerfiles. Here exact patch equality
and missing-site failures follow this application's reproducibility policy.

When adding a pin site, extend `scripts/check_toolchain.py` and Renovate's manager
coverage together. Add a regression test that changes or removes the new site.
Compatibility ranges and action versions have their own version streams; do not
add them to an unrelated equality group.

## Renovate policy

Renovate opens one PR per dependency. Shared-pin groups are the exception: they
keep the copies of one tool together. Groups are best-effort: different managers
can see releases at different times. The required consistency check rejects an
incomplete update. Docker builds separately check that the images still build.

- Native managers handle mise, package manifests, workflows, hooks and images.
- `customManagers:dockerfileVersions` reads annotated `ARG`/`ENV` pins. Keep the
  annotation immediately above `PNPM_VERSION`.
- Custom regex managers cover Postgres literals, CI's gitleaks version and uv's
  `required-version`. Postgres extraction captures the tag and digest separately.
- The native Docker manager owns the uv image's tag **and** digest. A release-only
  regex could update its tag while retaining the old image digest.
- [`renovate-config-validator --strict`](https://docs.renovatebot.com/config-validation/)
  runs on pull requests and main pushes when its config, isolated toolchain,
  validation scripts or CI workflow change. Manual CI runs also validate it.
  Unrelated automatic builds and release tags skip the validator installation.
  Extraction tests ensure each custom manager still recognizes its declarations.
  Change detection uses [paths-filter's push support](https://github.com/dorny/paths-filter/blob/v4.0.3/README.md#supported-workflows).

All external base/service images are pinned to multi-platform OCI digests.
Renovate tracks both their readable tags and digests via `docker:pinDigests`, as
recommended by its [upgrade guidance](https://docs.renovatebot.com/upgrade-best-practices/).
The Postgres fixtures use the same digest as Compose. Application deployment
images remain selected by the release or build identifier; see the versioning
section below.

### Review and release age

Frontend tooling automerges on minor/patch updates after 14 days. Stable frontend
runtime dependencies automerge on patch updates after the same delay. Frameworks,
CSS, component libraries, icons, translations, Markdown processing, date handling
and Workbox require review because their output ships to users. 0.x frontend
runtime dependencies also require review.

Backend dev tools automerge on minor/patch updates. Stable backend runtime
dependencies automerge on patch updates; runtime minor/major and 0.x updates
require review.

All lock-file refreshes require review. Most Python requirements use open-ended
`>=` floors, so `uv lock --upgrade` can select major or breaking 0.x releases
without changing those floors. A lock-file-maintenance PR cannot inherit
per-package patch-only review guarantees.

Reviewed updates normally wait seven days. pnpm's `minimumReleaseAge` and uv's
`exclude-newer` apply that delay during resolution. Backend updates, including
automerges, retain their existing seven-day exception so Renovate and uv use the
same window. Making only Renovate wait 14 days lets uv lock a newer release inside
that window and can strand the PR on `renovate/artifacts`.

GitHub Actions and pre-commit hooks automerge minor/patch updates after 14 days.
Shared hadolint and gitleaks groups use 14 days at every pin site. Major runtime,
framework and image updates require review.

**uv is the timestamp exception.** GHCR supplies no release timestamp, so the
whole uv group has `minimumReleaseAge: null` and `automerge: false`. A uniform
policy allows native tag/digest updates without holding its other pins at a
different target. Review the release before merging; the consistency gate rejects
incomplete groups. This replaces the old GitHub-release regex workaround.

Lock maintenance also sets Renovate's age to `null`: the package manager resolves
that refresh, so only its own cooldown can enforce release age. Refreshes remain
review-only. See [Renovate's release-age limitations](https://docs.renovatebot.com/key-concepts/minimum-release-age/).

### Schedule

The update window is Monday 00:00–05:59 Moscow time, with
`updateNotScheduled: false`. Outside it Renovate neither opens nor re-pushes
ordinary update branches. Security updates retain Renovate's schedule bypass.
Actions use commit SHAs with full `# vX.Y.Z` comments so release aging follows
specific releases.

Later package rules override earlier ones. Keep the shipped-output exclusions
below generic automerge rules, and shared-pin policy below manager defaults.

## Versioning the app

The same "one version, one place" rule applies to the app's own version. There
are exactly **two** identifiers, and they answer different questions.

### Release version — _which release is this?_

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

| Bump  | When                                                                                                                                |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------- |
| PATCH | `just deploy` and nothing else: fixes, dependency bumps, refactors, copy.                                                           |
| MINOR | Same, but attendees see something new — a feature, a page, a notification type.                                                     |
| MAJOR | `just deploy` alone is **not** enough: a new required env var, a migration that cannot be rolled back, changed deployment topology. |

MAJOR is the one that earns its keep: it is the only version signal that changes
what a human has to _do_, and the failure it guards against — deploying blind
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

#### Why the bump stays manual

The bump is a deliberate human step, not automation keyed off commit messages.
Every automated bumper (semantic-release, release-please, Changesets) infers the
number from Conventional-Commits `type:` prefixes. We lint the PR title's shape
(`.github/workflows/pr-title.yml` — the PR title is what squash-merge lands, so
that, not individual commits, is what gets linted; see AGENTS.md "Commit & PR
titles"), but nothing consumes the prefixes. The bump that matters most, MAJOR,
is exactly the one no tool can infer — it marks _"`just deploy` alone is not
enough"_, a judgment about deploy steps, not a diff. So the number stays a human
call.

If the release chore ever grates enough to automate, the title lint is already
in place; add **release-please**, which opens a release PR carrying the bump and
changelog and keeps the human gate we rely on — you still choose when to merge
and tag. semantic-release (fully hands-off, wrong for images that sometimes need
manual MAJOR steps) and Changesets (monorepo/library-shaped) do not fit a single
deployed app.

### Build id — _which build is running?_

The commit SHA. This, not the release version, is what a deploy pins and what
ties an error to an exact bundle: every build between two releases carries the
same release number.

| Where                     | How it gets there                                                       |
| ------------------------- | ----------------------------------------------------------------------- |
| Image tag (`sha-1a2b3c4`) | `type=sha` in the publish workflow; pinned via `IMAGE_TAG`              |
| Backend Sentry release    | `APP_BUILD` build arg → `/app/BUILD_ID` file → `common/version.py`      |
| Frontend Sentry release   | `APP_BUILD` build arg → source-map upload release (`vite.config.ts`)    |
| Profile footer            | `APP_BUILD` build arg → `__APP_BUILD__` constant, baked into the bundle |

All four come from the same `github.sha`, so one deploy is one release across
both services. Sentry
([naming releases](https://docs.sentry.io/product/releases/naming-releases/))
recommends exactly this for VCS-backed projects.

### Both, baked in at build time

The two identifiers describe the build artifact, so they are fixed when it is
built and never read from the environment of a running container — 12-Factor's
build stage turns a specific commit into the artifact, and a release "cannot be
mutated once it is created" ([build, release, run](https://12factor.net/build-release-run)).
They enter as Docker build args because neither image's build context can see
their source: `./frontend` has no `pyproject.toml`, and neither context has a
`.git`.

- **Frontend** — the publish workflow reads the release number from
  `pyproject.toml` and passes `APP_VERSION` and `APP_BUILD`; `vite.config.ts`
  inlines them as `__APP_VERSION__` / `__APP_BUILD__` with Vite's
  [`define`](https://vite.dev/config/shared-options#define). The profile
  footer shows `Версия 2.1.0 · 1a2b3c4`: the number an attendee can read out in
  a bug report, plus the short SHA.
- **Backend** — `APP_BUILD` is written to a file, not set as image `ENV`.
  Compose `env_file` values override image `ENV`, so a stray `APP_BUILD=` line in
  a server's `.env` would silently erase the baked-in id; a file is out of its
  reach. The Dockerfile uses a plain `ARG`, which Docker does not persist into
  the image ([Dockerfile reference](https://docs.docker.com/reference/dockerfile/#arg)).

`just run-prod` passes `APP_VERSION` only, so a local image shows the release
number without a SHA. Building from a working tree leaves `APP_BUILD` unset — the
footer drops the SHA and Sentry gets no release, which is the honest answer for
a build that has no published identity. A host build outside Docker
(`just frontend-dev`) has neither, and the footer line hides itself.

### What is deliberately _not_ versioned

The HTTP API has no `/v1` URL prefix and does not need one. Path versioning
exists to let an old client keep working against a new server; with a single
first-party client deployed in the same step as the backend, that window never
opens.
