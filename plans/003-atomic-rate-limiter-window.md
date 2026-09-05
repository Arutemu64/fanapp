# Plan 003: Make the Redis rate-limiter increment+expire atomic so a counter can never lose its TTL

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 3063e77e..HEAD -- backend/src/fanfan/adapters/redis/rate_limiter.py`
> If the file changed since this plan was written, compare the "Current state"
> excerpt against the live code before proceeding; on a mismatch, treat it as a
> STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: correctness (availability)
- **Planned at**: commit `3063e77e`, 2026-09-05

## Why this matters

The fixed-window rate limiter does `INCR`, then — only when the counter is `1` —
a **separate** `EXPIRE` call. The two commands are not atomic. If the process
crashes or the Redis connection drops between them on the first hit, the counter
key lives **forever with no TTL**. Once it climbs past the limit it never resets,
so the affected email or IP is **permanently locked out of login** (and OTP
consume) until someone manually clears Redis. This is on the auth critical path,
and the whole point of the window ("so the counter eventually expires instead of
living forever") is defeated by the gap.

The fix collapses increment + expire into a single atomic Redis operation and,
as a bonus, self-heals any key that somehow already lost its TTL.

## Current state

- `backend/src/fanfan/adapters/redis/rate_limiter.py` — the whole file:

  ```python
  from collections.abc import Awaitable
  from typing import cast

  from redis.asyncio import Redis

  from fanfan.application.ports.rate_limiter import RateLimiter
  from fanfan.core.exceptions.rate_limit import TooManyAttempts


  class RedisRateLimiter(RateLimiter):
      """Fixed-window attempt counter backed by Redis INCR/EXPIRE."""

      def __init__(self, redis: Redis):
          self.redis = redis

      @staticmethod
      def _counter_key(key: str) -> str:
          return f"rate_limit:counter:{key}"

      async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
          counter_key = self._counter_key(key)
          # redis-py's async stubs mistype incr() as a plain int, so cast the
          # call to its real awaitable return type before awaiting it.
          attempts = await cast("Awaitable[int]", self.redis.incr(counter_key))
          # Start the window on the first hit so the counter eventually expires
          # instead of living forever once the key goes quiet.
          if attempts == 1:
              await self.redis.expire(counter_key, max(1, window_seconds))
          if attempts > limit:
              retry_after = await self.redis.ttl(counter_key)
              raise TooManyAttempts(retry_after=max(1, retry_after))

      async def reset(self, key: str) -> None:
          await self.redis.delete(self._counter_key(key))
  ```

- Callers that depend on this staying reliable:
  - `application/interactors/auth/authenticate_user.py:97-115` — per-email and
    per-IP login throttle (`login:email:{...}`, `login:ip:{...}`).
  - `adapters/redis/auth_token_registry.py` — OTP attempt limiting.
- `RateLimiter` is a port (`application/ports/rate_limiter.py`); the adapter must
  keep implementing it unchanged in signature.
- Per `docs/testing.md`, the rate limiter is exercised **for real** against Redis
  in integration tests (not faked), so behavior is testable end-to-end.

## Fix approach

Replace the two-step `INCR` + conditional `EXPIRE` with a single Lua script
evaluated server-side (atomic; no client round-trip gap). The script sets the
window on the first hit **and repairs any key missing a TTL**, which also
self-heals counters that were orphaned before this fix ships:

```lua
local current = redis.call('INCR', KEYS[1])
if redis.call('TTL', KEYS[1]) < 0 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
```

(`TTL` returns `-1` for a key with no expiry and `-2` for a missing key; `< 0`
covers "needs a window set".)

Research the current redis-py async API for running a script (`self.redis.eval`
vs. `register_script`) against the version pinned in `backend/pyproject.toml` /
`uv.lock` before writing it, per AGENTS.md — don't rely on memory for the exact
call shape and return typing.

## Commands you will need

| Purpose            | Command                                                    | Expected on success |
|--------------------|-----------------------------------------------------------|---------------------|
| Lint               | `just backend-lint`                                       | exit 0              |
| Typecheck          | `just backend-typecheck`                                  | exit 0, no errors   |
| Integration tests  | `cd backend && uv run pytest -m integration -k rate_limit`| all pass (needs Docker) |

Integration tests need a Docker daemon (testcontainers Redis). If Docker is not
available, write the tests anyway and rely on CI; say so in your report.

## Scope

**In scope**:
- `backend/src/fanfan/adapters/redis/rate_limiter.py`
- A new integration test file (see Test plan).

**Out of scope** (do NOT touch):
- `application/ports/rate_limiter.py` — the port signature stays identical.
- The callers (`authenticate_user.py`, `auth_token_registry.py`) — behavior is
  unchanged from their perspective.
- `reset()` — it is already a single atomic `DELETE`; leave it.

## Git workflow

- Branch: `advisor/003-atomic-rate-limiter` off `main`.
- One commit; imperative title, e.g.
  `Make the rate-limiter window atomic so a counter never loses its TTL`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Replace the increment+expire with an atomic script

Rewrite `hit()` so the increment and window-set happen in one server-side
operation using the Lua script above. Keep the `TooManyAttempts` behavior and
the `retry_after` read (the `TTL` read for `retry_after` when over the limit can
stay a separate read-only call). Preserve an English comment explaining *why* the
script exists (the crash-between-commands race that orphans the TTL) — do not
delete the existing "start the window on the first hit" rationale; fold it into
the new comment.

**Verify**: `just backend-typecheck` → exit 0. `just backend-lint` → exit 0.

### Step 2: Add an integration test proving the window is always set

Create `backend/tests/integration/adapters/test_rate_limiter.py` (create the
`adapters/` integration dir + `__init__.py` if absent), modelled structurally on
the reference `backend/tests/integration/schedule_mgmt/test_set_current_event.py`
(resolve from `dishka_request`, `@pytest.mark.integration`). Resolve the limiter
with `await dishka_request.get(RateLimiter)`. Cover:

1. **TTL set on first hit**: after one `hit(key, limit=..., window_seconds=...)`,
   the counter key's TTL is a positive value ≤ `window_seconds`.
2. **Limit enforced**: hitting `limit + 1` times raises `TooManyAttempts`.
3. **Self-heal**: manually create the counter key with `INCR` and **no** expire
   (simulating an orphaned counter), then call `hit(...)` once and assert the key
   now has a positive TTL. This is the regression this plan fixes.

Reach into Redis through the same client the limiter uses (resolve the `Redis`
client from `dishka_request`, or use `RedisRateLimiter._counter_key(key)` to
compute the key name for assertions).

**Verify**: `cd backend && uv run pytest -m integration -k rate_limit` → all
pass (needs Docker).

## Test plan

- New file: `backend/tests/integration/adapters/test_rate_limiter.py` with the
  three cases in Step 2 — TTL-on-first-hit (happy path), limit-enforced, and the
  orphaned-counter self-heal (the specific regression).
- Structural pattern: `backend/tests/integration/schedule_mgmt/test_set_current_event.py`.
- Verification: `cd backend && uv run pytest -m integration -k rate_limit` → all
  pass, including the 3 new tests. Prefer CI when Docker is unavailable.

## Done criteria

ALL must hold:

- [ ] `just backend-typecheck` exits 0
- [ ] `just backend-lint` exits 0
- [ ] `hit()` performs the increment and window-set in a single atomic Redis
      operation (no client-side gap where a crash leaves the key without a TTL)
- [ ] New integration test file exists with the 3 cases and passes
      (`cd backend && uv run pytest -m integration -k rate_limit`), or, if Docker
      is unavailable, the tests are written and CI is relied on (stated in report)
- [ ] `RateLimiter` port signature and the two callers are unchanged
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The "Current state" excerpt no longer matches the live file (drift).
- The pinned redis-py version's scripting API can't be confirmed against current
  docs, or `eval`/`register_script` isn't available on the async client in use.
- The integration harness can't resolve `RateLimiter` or the `Redis` client from
  `dishka_request` (report the resolution error).

## Maintenance notes

- If the limiter ever needs sliding-window or token-bucket semantics, this Lua
  script is the natural place to evolve; keep it atomic.
- A reviewer should confirm the script's key/argument passing matches redis-py's
  `eval` contract (numkeys, KEYS vs ARGV) and that `retry_after` still returns a
  sane positive integer when over the limit.
