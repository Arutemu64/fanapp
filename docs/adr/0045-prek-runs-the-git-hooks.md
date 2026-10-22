# ADR-0045: prek runs the git hooks

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Project maintainers

## Context

The git hooks ran under [pre-commit](https://pre-commit.com), installed as a
backend dev dependency. Renovate's `abandonments:recommended` preset flags any
package with no release in a year ([preset](https://docs.renovatebot.com/presets-abandonments/)),
and `pre-commit/pre-commit-hooks` had not released since v6.0.0 (August 2025),
so it sat on the Dependency Dashboard as abandoned, even though its `main`
branch is still being maintained.

[prek](https://github.com/j178/prek) is a Rust reimplementation of pre-commit
that reads `.pre-commit-config.yaml` unchanged and ships as one binary with no
Python runtime. apache/airflow, python/cpython and fastapi/fastapi use it. It
also ships Rust-native ports of the common `pre-commit-hooks` hooks, selected
with `repo: builtin` ([built-in hooks](https://prek.j178.dev/reference/built-in-hooks/)).

## Decision

We will run the hooks with prek, pinned as a backend dev dependency
(`backend/uv.lock`) and installed by `just backend-setup-hooks`
(`prek install --force`). The config stays `.pre-commit-config.yaml`, and the
`pre-commit-hooks` entry becomes `repo: builtin`.

- **YAML, not `prek.toml`.** Renovate's pre-commit manager matches only
  `.pre-commit-config.yaml` and parses it as YAML. It is what keeps the
  gitleaks and hadolint `rev`s current, and those revs are shared pins.
- **`repo: builtin` has no `rev`,** so Renovate's manager skips it and there
  is no dependency left to flag as abandoned.
- **check-yaml is strict by flag.** The builtin hook accepts unknown YAML tags
  by default, unlike upstream. So every file except the Compose files runs
  with `--disallow-unknown-tags`. The Compose files run without it, since they
  rely on `!reset` / `!override`; they still load fully instead of falling back
  to upstream's syntax-only `--unsafe`.

## Consequences

- The `pre-commit-hooks` hooks run without building a Python environment.
  Hook runs and installs are faster.
- Builtin hook behaviour follows prek's ports, not upstream's code. Differences
  are documented per hook. check-yaml's tag handling is the one we rely on.
- A clone that ran `pre-commit install` keeps working shims only after
  `just backend-setup-hooks` is re-run.
- The config no longer runs under upstream pre-commit, which does not know
  `repo: builtin`.

## Alternatives considered

- **Keep pre-commit and silence the abandonment flag** with a Renovate
  `abandonmentThreshold` override. Cheapest, but keeps the slower runner and a
  Python environment per remote hook repo.
- **prek with the remote `pre-commit-hooks` repo.** prek's automatic fast path
  would still run the native ports, but the `rev` would stay a tracked,
  flagged dependency that no longer changes anything.
