# Repository rulesets

Rulesets live in GitHub's server-side config, **not** in the repo tree — committing a
JSON file here does nothing on its own. These files are version-controlled copies of what
is (or should be) configured under **Settings → Rules → Rulesets**, so the intended
protection is reviewable in a PR and reproducible on another repo.

## Applying a ruleset

**Settings → Rules → Rulesets → New ruleset → Import a ruleset**, pick the JSON, review,
then **Create**. To automate instead, `POST` the JSON to the
[rulesets REST API](https://docs.github.com/en/rest/repos/rules) (`/repos/{owner}/{repo}/rulesets`).

Editing an imported ruleset in the UI does not write back here — update the JSON in the
same PR that changes the intended protection, the same way we keep `.env.example` in sync.

## `main-branch-protection.json`

Protects `main` (enforcement: `active`). Repository admins can bypass (`actor_id: 5`) as
an emergency and solo-merge escape hatch.

- **Pull request required**, 0 approvals — enforces PR-before-merge and conversation
  resolution without blocking a solo maintainer; raise the approval count once the team
  grows.
- **Squash only** + **linear history** — matches the squash-merge policy in `AGENTS.md`
  ("the PR title *is* the commit that lands on `main`").
- **Force pushes blocked** and **deletion restricted**.
- **Required status checks** — the CI jobs that always report a status. `ci.yml` gates
  jobs with a job-level `if:` (not a workflow-level `paths:` filter), so an unrelated PR
  reports these as *skipped*, which counts as passing — no PR ever deadlocks waiting on a
  check that never runs. Non-strict (no "up to date before merge") to avoid re-run churn;
  revisit with a merge queue if PR volume grows.
- `Frontend (e2e)` is deliberately **not** required — `ci.yml` wants a browser tier to
  prove stable under CI timing before it gates merges.

The required-check names must match the check names GitHub shows on a real PR exactly. If a
CI job is renamed, update the matching `context` here or that check silently stops gating.
