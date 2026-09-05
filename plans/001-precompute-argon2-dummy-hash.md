# Plan 001: Compute the login dummy-hash once per process, not per request

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 3063e77e..HEAD -- backend/src/fanfan/application/interactors/auth/authenticate_user.py backend/src/fanfan/main/ioc/interactors.py`
> If either in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `3063e77e`, 2026-09-05
- **PR**: https://github.com/Arutemu64/fanapp/pull/771

## Why this matters

`AuthenticateUser` computes an Argon2 hash of a throwaway string in its
constructor. The interactor is registered in `Scope.REQUEST` (a fresh instance
per request), so **every login request pays a full Argon2 hash it does not
need** — Argon2 is deliberately slow (tens of ms, tuned CPU + memory). The hash
is only used on the user-not-found branch, to keep that branch constant-time
against account enumeration. Computing it once per process preserves that
security property while removing the per-request cost (and a cheap DoS
amplifier on the unauthenticated `/auth` login route).

## Current state

- `backend/src/fanfan/application/interactors/auth/authenticate_user.py` — the
  login interactor. Constructor, lines 31–43:

  ```python
  class AuthenticateUser:
      def __init__(
          self,
          user_gateway: UserGateway,
          password_hasher: PasswordHasher,
          session_store: SessionStore,
          rate_limiter: RateLimiter,
      ):
          self.user_gateway = user_gateway
          self.password_hasher = password_hasher
          self.session_store = session_store
          self.rate_limiter = rate_limiter
          self.dummy_hash = self.password_hasher.hash("dummy_password")  # ← per-request Argon2 hash
  ```

  The only use, in `__call__`, lines 52–57 — the not-found branch:

  ```python
      user = await self.user_gateway.get_by_email(normalized_email)
      if user is None:
          # Hash against a dummy value so a nonexistent user takes the same
          # time as a wrong password, and the response can't be timed to
          # enumerate accounts.
          self.password_hasher.verify(data.password, self.dummy_hash)
  ```

- `backend/src/fanfan/main/ioc/interactors.py` — `InteractorsProvider` has
  `scope = Scope.REQUEST` (line 163) and lists `AuthenticateUser` in its
  `provide_all(...)` roster (line 209). This is what makes the constructor run
  once per request. **Do not change the scope** — request scope is correct for
  an interactor; only the dummy-hash computation should be hoisted.

- `PasswordHasher` is a port (`application/ports/password_hasher.py`) with
  `hash()` / `verify()`. The app layer must depend only on this port — it must
  **not** import the concrete `PwdlibPasswordHasher` adapter. The fix must keep
  that boundary (enforced by `just backend-import-lint`, part of
  `just backend-lint`).

## Commands you will need

| Purpose   | Command                                             | Expected on success |
|-----------|-----------------------------------------------------|---------------------|
| Lint      | `just backend-lint`                                 | exit 0              |
| Typecheck | `just backend-typecheck`                            | exit 0, no errors   |
| Unit tests| `cd backend && uv run pytest -m unit`               | all pass            |

The auth interactor's behavior is covered by the integration suite
(`backend/tests/integration/auth/`), which needs a Docker daemon. **Do not**
gate this plan on running it locally — CI runs it. If Docker is available and
you want extra confidence: `just backend-test-integration` (slow).

## Scope

**In scope** (the only file you should modify):
- `backend/src/fanfan/application/interactors/auth/authenticate_user.py`

**Out of scope** (do NOT touch):
- `backend/src/fanfan/main/ioc/interactors.py` — the request scope is correct;
  changing it to fix this would be the wrong fix and would affect every
  interactor in the provider.
- `backend/src/fanfan/adapters/auth/password_hasher.py` — the adapter is fine.
- The constant-time not-found branch logic in `__call__` — keep it exactly as
  is; it must still call `verify(...)` against a real Argon2 hash.

## Git workflow

- Branch: `advisor/001-argon2-dummy-hash` off `main`.
- One commit; imperative, capitalised, period-less title, e.g.
  `Compute the login dummy-hash once instead of per request`. End the message
  with the `Co-Authored-By: Claude ...` trailer if your environment adds one.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Hoist the dummy hash to a lazily-initialised, process-wide cache

Replace the per-instance `self.dummy_hash = self.password_hasher.hash(...)` with
a class-level cache computed at most once per process, using the injected
hasher (so the port boundary is preserved). Target shape:

```python
from typing import ClassVar


class AuthenticateUser:
    # Argon2 is deliberately slow; the dummy hash used to equalise timing on the
    # user-not-found branch only needs computing once per process, not per
    # request. Cached on the class, filled lazily from the injected hasher so the
    # application layer stays free of the concrete crypto library.
    _dummy_hash: ClassVar[str | None] = None

    def __init__(
        self,
        user_gateway: UserGateway,
        password_hasher: PasswordHasher,
        session_store: SessionStore,
        rate_limiter: RateLimiter,
    ):
        self.user_gateway = user_gateway
        self.password_hasher = password_hasher
        self.session_store = session_store
        self.rate_limiter = rate_limiter
        if AuthenticateUser._dummy_hash is None:
            AuthenticateUser._dummy_hash = self.password_hasher.hash("dummy_password")
        self.dummy_hash = AuthenticateUser._dummy_hash
```

Leave `__call__` unchanged — it keeps reading `self.dummy_hash`.

**Verify**: `just backend-typecheck` → exit 0, no errors. `just backend-lint` →
exit 0 (this also runs import-linter; a green run confirms the port boundary is
intact).

### Step 2: Confirm the not-found branch still uses the cached hash

Read `__call__` and confirm line ~57 still reads
`self.password_hasher.verify(data.password, self.dummy_hash)` and that
`self.dummy_hash` is a real Argon2 hash string (it is — it comes from
`password_hasher.hash(...)`). No code change expected here; this is a
correctness check that the constant-time property is preserved.

**Verify**: `cd backend && uv run pytest -m unit` → all pass.

## Test plan

No new test required: this is a pure performance refactor with **no behavior
change** — the not-found branch still verifies against a real Argon2 hash, so
the existing auth integration tests in `backend/tests/integration/auth/` remain
the coverage. (Per `docs/testing.md`, a refactor an existing test already
covers does not need a new test.) Writing a test that asserts "hash computed
once" would require a call-counting fake hasher and test interactor internals —
skip it.

## Done criteria

ALL must hold:

- [ ] `just backend-typecheck` exits 0
- [ ] `just backend-lint` exits 0 (includes import-linter: no new adapter import
      in the application layer)
- [ ] `cd backend && uv run pytest -m unit` exits 0
- [ ] `grep -n "password_hasher.hash(\"dummy_password\")" backend/src/fanfan/application/interactors/auth/authenticate_user.py`
      shows the call is now guarded by the `if AuthenticateUser._dummy_hash is None:` check (not an unconditional statement in `__init__`)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The "Current state" excerpt of `authenticate_user.py` no longer matches the
  live code (drift since this plan was written).
- `just backend-lint` reports an import-linter violation — that means the
  approach accidentally reached for the concrete hasher; the injected
  `self.password_hasher` must be the only source of the hash.
- You find another interactor already sharing a process-wide dummy hash
  (someone fixed this differently) — reconcile rather than duplicate.

## Maintenance notes

- If a second interactor ever needs the same equal-timing trick, consider
  moving the cached dummy hash behind the `PasswordHasher` port (a
  `dummy_verify(password)` method) so the caching lives with the crypto. Not
  worth it for a single caller today.
- A reviewer should confirm the not-found branch still performs a real Argon2
  `verify` (constant-time enumeration defense) and that request scope on the
  interactor is unchanged.
