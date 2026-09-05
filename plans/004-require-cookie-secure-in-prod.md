# Plan 004: Fail closed when a production deploy forgets WEB__COOKIE_SECURE

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 3063e77e..HEAD -- backend/src/fanfan/adapters/config/models.py backend/src/fanfan/presentation/web/config.py .env.example`
> If any in-scope file changed since this plan was written, compare the "Current
> state" excerpts against the live code before proceeding; on a mismatch, treat
> it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `3063e77e`, 2026-09-05

## Why this matters

`WEB__COOKIE_SECURE` defaults to `False`. It controls the `Secure` flag on the
session cookie and on the OAuth-state `SessionMiddleware` cookie. The app already
**fails closed** on the analogous `DEBUG__ENABLED` misconfiguration in production
(it refuses to start), but there is **no equivalent guard for `cookie_secure`**.
So a production deploy that forgets to set `WEB__COOKIE_SECURE=True` silently
ships session and OAuth-state cookies **without the `Secure` flag**, meaning a
browser will send them over plain HTTP — exposing the session to network
attackers. The asymmetry (debug guarded, cookie flag not) makes this an easy,
silent misconfiguration. This plan adds the missing production guard, mirroring
the existing debug guard.

## Current state

- `backend/src/fanfan/presentation/web/config.py:23-24` — the default:

  ```python
      # Set to True in production (HTTPS). Ensures cookies are never sent over plain HTTP.
      cookie_secure: bool = False
  ```

  It flows into the session cookie (`routes/auth/cookies.py:12`) and the OAuth
  `SessionMiddleware` (`web/factory.py:67`).

- `backend/src/fanfan/adapters/config/models.py:100-125` — the existing
  environment-posture validator that already fails closed on debug in prod. This
  is the pattern to mirror and the place to add the cookie check:

  ```python
      @model_validator(mode="after")
      def _apply_environment_posture(self) -> EnvConfig:
          """Derive debug defaults from ENV, then fail closed in production.
          ...
          """
          explicit = self.debug.model_fields_set
          if self.env is Environment.DEV:
              if "enabled" not in explicit:
                  self.debug.enabled = True
              if "logging_level" not in explicit:
                  self.debug.logging_level = logging.DEBUG
              if "json_logs" not in explicit:
                  self.debug.json_logs = False
          elif self.env is Environment.PROD and self.debug.enabled:
              # FastAPI debug mode leaks stack traces in HTTP responses, so it
              # must never reach production — refuse to start rather than leak.
              msg = (
                  "DEBUG__ENABLED must be False when APP_ENV=prod "
                  "(FastAPI debug mode leaks stack traces in HTTP responses)."
              )
              raise ValueError(msg)
          return self
  ```

  `EnvConfig` has `web: WebConfig` (line 47), so `self.web.cookie_secure` is
  reachable in this validator. `Environment` is a `StrEnum` with `DEV`, `STAGING`,
  `PROD` (lines 25–30).

- `.env.example` — documents `WEB__COOKIE_SECURE` in the BACKEND block. AGENTS.md
  requires `.env.example` to stay in sync when config behavior changes; the
  comment there must state the new fail-closed rule.

## Design decision

Guard **PROD only** (not STAGING), matching the existing debug guard and avoiding
surprising a deliberately-HTTP staging box. Add the check inside the existing
`elif self.env is Environment.PROD` branch rather than a new validator, so all
production posture rules live in one place.

## Commands you will need

| Purpose    | Command                                       | Expected on success |
|------------|-----------------------------------------------|---------------------|
| Lint       | `just backend-lint`                           | exit 0              |
| Typecheck  | `just backend-typecheck`                      | exit 0, no errors   |
| Unit tests | `cd backend && uv run pytest -m unit`         | all pass            |

## Scope

**In scope**:
- `backend/src/fanfan/adapters/config/models.py` (add the guard)
- `.env.example` (document the fail-closed behavior on the `WEB__COOKIE_SECURE`
  line)
- A unit test **if** a config-test harness already exists (see Test plan).

**Out of scope** (do NOT touch):
- `backend/src/fanfan/presentation/web/config.py` — leave the `False` default
  (the guard, not the default, is the fix; changing the default could relax dev).
- `routes/auth/cookies.py`, `web/factory.py` — the cookie-setting code is fine.

## Git workflow

- Branch: `advisor/004-cookie-secure-prod-guard` off `main`.
- One commit; imperative title, e.g.
  `Refuse to start in prod when WEB__COOKIE_SECURE is False`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the production guard

Extend the `PROD` branch of `_apply_environment_posture`. Because the branch
currently reads `elif self.env is Environment.PROD and self.debug.enabled:`,
restructure it so both prod checks run (the current condition short-circuits when
debug is off, which would skip a cookie check). Target shape:

```python
        elif self.env is Environment.PROD:
            if self.debug.enabled:
                # FastAPI debug mode leaks stack traces in HTTP responses, so it
                # must never reach production — refuse to start rather than leak.
                msg = (
                    "DEBUG__ENABLED must be False when APP_ENV=prod "
                    "(FastAPI debug mode leaks stack traces in HTTP responses)."
                )
                raise ValueError(msg)
            if not self.web.cookie_secure:
                # Without Secure, the browser sends the session and OAuth-state
                # cookies over plain HTTP — refuse to start rather than ship them
                # unprotected.
                msg = (
                    "WEB__COOKIE_SECURE must be True when APP_ENV=prod "
                    "(cookies without Secure are sent over plain HTTP)."
                )
                raise ValueError(msg)
        return self
```

Preserve the existing docstring and the DEV branch unchanged.

**Verify**: `just backend-typecheck` → exit 0. `just backend-lint` → exit 0.

### Step 2: Update `.env.example`

On the `WEB__COOKIE_SECURE` line's comment, state that it **must** be `True` when
`APP_ENV=prod` and that the app refuses to start otherwise (mirroring how the
`DEBUG__ENABLED` line is documented). Keep it terse and in the file's existing
comment style.

**Verify**: read the diff; the comment reflects the new fail-closed rule.

### Step 3: Add a unit test (only if a config-test harness exists)

Look for existing tests of `EnvConfig` / `_apply_environment_posture` (e.g.
`grep -rn "EnvConfig\|_apply_environment_posture\|DEBUG__ENABLED must be False" backend/tests`).

- **If** a test already covers the debug guard: add a sibling test asserting that
  building an `EnvConfig` with `env=PROD` and `web.cookie_secure=False` raises
  `ValueError`, and that `cookie_secure=True` in prod is accepted. Follow that
  file's construction pattern exactly (it will already solve providing the
  required nested config).
- **If** no such harness exists: do **not** build one from scratch for this
  (constructing `EnvConfig` requires every required nested field). Note in your
  report that the guard is untested for lack of a config-test harness, and that
  `just backend-lint`/`typecheck` plus manual reasoning are the coverage.

**Verify**: `cd backend && uv run pytest -m unit` → all pass.

## Test plan

- Conditional on an existing config-test harness (Step 3): one unit test for the
  prod + `cookie_secure=False` → `ValueError` path and one for the accepted case.
- Otherwise: no new test (documented in the PR), same judgment call
  `docs/testing.md` sanctions for config with no cheap test seam.

## Done criteria

ALL must hold:

- [ ] `just backend-typecheck` exits 0
- [ ] `just backend-lint` exits 0
- [ ] `cd backend && uv run pytest -m unit` exits 0
- [ ] Building the config with `APP_ENV=prod` and `WEB__COOKIE_SECURE` unset/False
      raises a `ValueError` at startup (verified by the new test, or by reading
      the validator if no harness exists)
- [ ] The debug guard still fires in prod (its behavior is preserved by the
      restructure, not dropped)
- [ ] `.env.example` documents the new fail-closed rule on the
      `WEB__COOKIE_SECURE` line
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The "Current state" excerpts don't match the live code (drift) — especially if
  the validator has already gained a cookie check (someone fixed it).
- Restructuring the `PROD` branch would change the DEV-branch behavior in any way
  — the DEV relaxation must stay byte-for-byte equivalent.

## Maintenance notes

- If STAGING ever needs the same guard (staging on HTTPS), extend the check to
  `self.env in (Environment.PROD, Environment.STAGING)` — deliberately left
  PROD-only here to match the debug guard and not break a plain-HTTP staging box.
- A reviewer should confirm the debug guard is still reached when debug is
  enabled in prod (the restructure from `elif ... and self.debug.enabled` to a
  nested `if` is where a mistake would silently drop it).
