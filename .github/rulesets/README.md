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
- **Required status checks** — just two: `CI success` and `Validate PR title`. `CI success`
  is an aggregate gate job in `ci.yml` that `needs` every gating job and fails if any of
  them failed or was cancelled (`skipped` and `success` both pass). It exists because the
  individual jobs can't be required directly: `ci.yml` fans backend/frontend/images out into
  conditional and matrix jobs, and a *skipped* matrix job reports a single check under the
  un-interpolated name (`Frontend (${{ matrix.task.name }})`), not the expanded `Frontend
  (lint)` … contexts — so requiring the expanded names would deadlock any PR outside that
  area. The gate also closes the change-detection bypass: if the `changes` job fails, its
  dependents skip, and without the gate those skipped-but-required checks would let a PR
  merge unvalidated; the gate fails instead. Non-strict (no "up to date before merge") to
  avoid re-run churn; revisit with a merge queue if PR volume grows. This is the documented
  pattern for conditional/matrix jobs — see
  <https://devopsdirective.com/posts/2025/08/github-actions-required-checks-for-conditional-jobs/>.
- `Frontend (e2e)` is deliberately **not** gated — `ci.yml` wants a browser tier to prove
  stable under CI timing first, so it is excluded from the gate's `needs`.

Requiring only the gate means the sole thing to keep in sync is the gate's `needs` list in
`ci.yml`: a new required job missing from it is silently ungated. The two `context` names
here must still match the check names GitHub shows on a real PR exactly — rename the gate
job or the PR-title job and the matching `context` must change too.
