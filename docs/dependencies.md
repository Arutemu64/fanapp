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
