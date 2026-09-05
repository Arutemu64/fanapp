# Plan 002: Authorize and size-cap the schedule import before parsing the upload

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 3063e77e..HEAD -- backend/src/fanfan/presentation/web/routes/schedule/importing.py backend/src/fanfan/adapters/parsers/schedule.py etc/caddy/Caddyfile Caddyfile.example`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `3063e77e`, 2026-09-05

## Why this matters

The schedule-import endpoint reads the **entire** uploaded file into memory and
runs a synchronous polars/calamine parse **before any authentication or
authorization happens**. The router's `session_security` dependency is
documentation-only (it never rejects a request — see the excerpt below), and the
real permission check (`SCHEDULE_IMPORT`) lives inside the interactor, which runs
only *after* the parse. There is also no size or content-type cap at any layer
(neither the app nor the deployed Caddy config). Net effect: an unauthenticated
caller can POST a large or malformed body to `/api/schedule/import` and force the
server to buffer it and run a CPU-heavy parse — memory/CPU exhaustion — with the
authorization rejection arriving too late to shed the load.

This plan makes the endpoint (1) check identity + `SCHEDULE_IMPORT` **before**
parsing, (2) reject oversized or wrong-type uploads early, and (3) add a
request-body cap at the reverse proxy as defense-in-depth.

## Current state

- `backend/src/fanfan/presentation/web/routes/schedule/importing.py` — the whole
  file today:

  ```python
  from typing import Annotated

  from dishka import FromDishka
  from dishka.integrations.fastapi import inject
  from fastapi import APIRouter, File, UploadFile
  from starlette.concurrency import run_in_threadpool

  from fanfan.adapters.parsers.schedule import parse_schedule_from_excel
  from fanfan.application.interactors.schedule_mgmt.import_schedule import (
      ImportSchedule,
      ImportScheduleInput,
  )
  from fanfan.presentation.web.responses import AUTH_RESPONSES
  from fanfan.presentation.web.schemas.error import ErrorMessage
  from fanfan.presentation.web.security import session_security

  importing_router = APIRouter(
      dependencies=[session_security],
      responses=AUTH_RESPONSES,
  )


  @importing_router.post(
      "/import",
      status_code=201,
      responses={
          400: {
              "model": ErrorMessage,
              "description": "The spreadsheet could not be read as a schedule.",
          },
      },
  )
  @inject
  async def import_schedule(
      file: Annotated[UploadFile, File(description="Excel file with schedule data.")],
      interactor: FromDishka[ImportSchedule],
  ) -> None:
      # Parse in a worker thread because polars/fastexcel are synchronous libraries.
      # This keeps the async FastAPI event loop responsive during file imports.
      schedule = await run_in_threadpool(parse_schedule_from_excel, file.file)
      await interactor(ImportScheduleInput(schedule=schedule))
  ```

- `backend/src/fanfan/presentation/web/security.py` — proves `session_security`
  does not gate anything:

  ```python
  # ... auto_error=False means it never raises at runtime; real enforcement
  # stays in the application layer (CurrentUserProvider.require_user). ...
  session_security = Security(_session_cookie_scheme)
  # Attach via route/router `dependencies=[session_security]`. This does NOT gate
  # the route (despite the FastAPI Security() convention) — its only effect is to
  # register the SessionCookie scheme ... in OpenAPI.
  ```

- The permission the interactor requires
  (`application/interactors/schedule_mgmt/import_schedule.py`, lines 79–83):

  ```python
  async def __call__(self, data: ImportScheduleInput) -> None:
      current_user = await self.current_user_provider.require_user()
      await self.perm_service.ensure(
          user=current_user, permission=Permission.SCHEDULE_IMPORT
      )
  ```

- The application services you will resolve in the route:
  - `application/services/current_user.py` — `CurrentUserProvider.require_user()`
    returns the `User` or raises `UserNotAuthenticated` / `UserNotFound`.
  - `application/services/permissions.py` — `PermissionService.ensure(user=..., permission=...)`
    raises `AccessDenied` when the grant (or wildcard) is missing.
  - `Permission.SCHEDULE_IMPORT` from `fanfan.core.vo.permission`.
  These raise the same domain exceptions the interactor already raises, so the
  central exception handlers (`presentation/web/exceptions.py`) already map them
  to the right HTTP responses (`AUTH_RESPONSES` is already on the router).

- The parser reads the whole file into memory:
  `adapters/parsers/schedule.py:98` — `return pl.read_excel(file.read())`.

- Deployed reverse proxy `etc/caddy/Caddyfile` — currently has **no**
  `request_body` cap:

  ```
  :80 {
  	@compressible {
  		not path /api/events*
  	}
  	encode @compressible zstd
  	handle_path /api* {
  		reverse_proxy http://127.0.0.1:8000 {
  			header_up X-Forwarded-Proto {header.X-Forwarded-Proto}
  		}
  	}
  	handle {
  		reverse_proxy http://127.0.0.1:3000
  	}
  }
  ```

- `Caddyfile.example` is the documented template (has a `servers { trusted_proxies ... }`
  global block and a richer `:80 { ... }` block). Keep the two files consistent.

## Repo conventions to follow

- Routes use `@inject` + `FromDishka[...]` params; resolving application services
  (not just interactors) in a route is fine — see how interactors are resolved in
  `presentation/web/routes/voting.py`.
- User-facing strings are **Russian**; error *messages* returned to clients come
  from the domain exceptions and their handlers — you are not adding new
  user-facing copy here except the 413/415 detail (Russian, see Step 2).
- Comments are English and carry the *why*, not the *what*.

## Commands you will need

| Purpose            | Command                                              | Expected on success |
|--------------------|-----------------------------------------------------|---------------------|
| Lint               | `just backend-lint`                                 | exit 0              |
| Typecheck          | `just backend-typecheck`                            | exit 0, no errors   |
| Regenerate API spec| `just frontend-generate-api`                        | updates `shared/openapi/openapi.json` + `frontend/src/lib/api/schema.d.ts` |
| Dockerfile lint    | `just dockerfile-lint`                              | exit 0 (only if you touch a Dockerfile — you should not) |

The import endpoint's behavior is covered by the integration suite (needs
Docker). Prefer CI; run `just backend-test-integration` locally only if Docker
is handy and you want extra confidence.

> **Why regenerate the API spec?** Adding a `413`/`415` response and any change
> to the operation's responses alters the OpenAPI contract, and a unit test
> (`tests/unit/presentation/test_openapi_spec.py`) fails if the committed spec
> drifts. Run `just frontend-generate-api` and commit both regenerated files.

## Scope

**In scope**:
- `backend/src/fanfan/presentation/web/routes/schedule/importing.py`
- `etc/caddy/Caddyfile` (add a request-body cap on `/api/schedule/import` or on
  `/api*`)
- `Caddyfile.example` (mirror the cap so the template stays authoritative)
- `shared/openapi/openapi.json` and `frontend/src/lib/api/schema.d.ts` — only as
  regenerated by `just frontend-generate-api`, never hand-edited.

**Out of scope** (do NOT touch):
- `application/interactors/schedule_mgmt/import_schedule.py` — its own auth check
  stays as the authoritative enforcement; the route check is an early gate, not a
  replacement. Leave the interactor unchanged.
- `adapters/parsers/schedule.py` — the parser is fine; do not try to stream it.
- `presentation/web/security.py` — leave `session_security` documentation-only.
- Do NOT introduce a new reusable `require_permission` FastAPI dependency in this
  plan (bigger refactor); resolve the services inline in this one route.

## Git workflow

- Branch: `advisor/002-schedule-import-guard` off `main`.
- One commit; imperative title, e.g.
  `Authorize and size-cap the schedule import before parsing`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Check identity + permission before parsing

Add `CurrentUserProvider` and `PermissionService` as injected params and run the
permission check before `run_in_threadpool(...)`. Target shape:

```python
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission

@inject
async def import_schedule(
    file: Annotated[UploadFile, File(description="Excel file with schedule data.")],
    interactor: FromDishka[ImportSchedule],
    current_user_provider: FromDishka[CurrentUserProvider],
    perm_service: FromDishka[PermissionService],
) -> None:
    # Authorize before reading/parsing the upload: the parse buffers the whole
    # file and runs a CPU-heavy synchronous read, so an unauthorized caller must
    # be rejected before it, not by the interactor afterwards.
    current_user = await current_user_provider.require_user()
    await perm_service.ensure(
        user=current_user, permission=Permission.SCHEDULE_IMPORT
    )
    _ensure_within_size_limit(file)  # from Step 2
    schedule = await run_in_threadpool(parse_schedule_from_excel, file.file)
    await interactor(ImportScheduleInput(schedule=schedule))
```

**Verify**: `just backend-typecheck` → exit 0. `just backend-lint` → exit 0.

### Step 2: Reject oversized / wrong-type uploads early

Add a small guard that rejects the upload before the parse when it is too large
or not an `.xlsx`. Starlette's `UploadFile` exposes `.size` (bytes, from the
multipart part) and `.content_type` / `.filename`. Target shape (module-level in
`importing.py`):

```python
from fastapi import HTTPException, status

# A real convention schedule is a few hundred rows — well under a megabyte. Cap
# generously so a legitimate import never trips it, while a hostile multi-hundred-
# MB body is rejected before the in-memory polars parse.
_MAX_IMPORT_BYTES = 5 * 1024 * 1024
_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",  # some browsers send this for .xlsx
    }
)


def _ensure_within_size_limit(file: UploadFile) -> None:
    if file.size is not None and file.size > _MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Файл расписания слишком большой.",
        )
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx") or (
        file.content_type is not None
        and file.content_type not in _ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Ожидается файл .xlsx.",
        )
```

Confirm the current best-practice signal for `UploadFile.size` / `.content_type`
in the installed Starlette/FastAPI version before relying on them — look them up
in the current Starlette docs (per AGENTS.md "research current best practice").
If `.size` is `None` in the running version, keep the extension/content-type
checks and note it; the proxy cap in Step 3 is the hard backstop either way.

**Verify**: `just backend-typecheck` → exit 0. `just backend-lint` → exit 0.

### Step 3: Add a request-body cap at the reverse proxy (defense in depth)

The app-level `.size` check happens only after Starlette has buffered the
multipart body, so the hard limit belongs at the proxy. Add a Caddy
`request_body { max_size ... }` on the API (or specifically the import path) in
both Caddy files. In `etc/caddy/Caddyfile`, inside the `handle_path /api*` (or a
dedicated matcher for `/api/schedule/import`):

```
	handle_path /api* {
		request_body {
			max_size 10MB
		}
		reverse_proxy http://127.0.0.1:8000 {
			header_up X-Forwarded-Proto {header.X-Forwarded-Proto}
		}
	}
```

Add an English comment above it explaining *why* (the import endpoint buffers the
whole body before the app can reject it). Verify the exact Caddy directive name
and placement against the current Caddy docs before committing (directive syntax
has changed across Caddy versions). Mirror the same block into `Caddyfile.example`.

**Verify**: there is no lint gate for the Caddyfile in this repo. Confirm the
block is syntactically consistent with the surrounding file by eye, and that both
files carry the same cap.

### Step 4: Declare the new responses and regenerate the API contract

Add `413` and `415` to the operation's `responses={...}` dict (with
`"model": ErrorMessage` and a short English description) so the OpenAPI spec
documents them, then regenerate:

**Verify**: `just frontend-generate-api` → succeeds and updates
`shared/openapi/openapi.json` + `frontend/src/lib/api/schema.d.ts`. Then
`cd backend && uv run pytest -m unit -k openapi` → the spec drift-guard test
passes. Commit both regenerated files.

## Test plan

- This change encodes an authorization/So it warrants an integration test.
  Add `backend/tests/integration/schedule_mgmt/test_import_schedule.py` (if it
  does not already exist) or extend the existing schedule_mgmt tests, modelled on
  `backend/tests/integration/schedule_mgmt/test_set_current_event.py`
  (the reference example — resolve the interactor from `dishka_request`, use the
  `login`, `outbox`, `uow` fixtures and the `schedule_editor` / `visitor`
  personas). Cover, at the **interactor** level (the route's early check mirrors
  the same rule):
  - happy path: a `schedule_editor` import creates the events;
  - permission failure: a `visitor` import raises `AccessDenied` and writes
    nothing.
- The route-level `413`/`415`/pre-auth behavior is thin presentation glue over
  `HTTPException`; a full route test needs a DOM-less HTTP client harness this
  suite doesn't use. Assert it by hand once (see Done criteria) rather than
  building new harness — note this in the PR.
- Verification: `cd backend && uv run pytest -m integration backend/tests/integration/schedule_mgmt/`
  (needs Docker) → all pass. Prefer CI if Docker is unavailable.

## Done criteria

ALL must hold:

- [ ] `just backend-typecheck` exits 0
- [ ] `just backend-lint` exits 0
- [ ] The route calls `require_user()` + `perm_service.ensure(..., SCHEDULE_IMPORT)`
      **before** `run_in_threadpool(parse_schedule_from_excel, ...)`
      (confirm by reading the function top-to-bottom)
- [ ] Oversized and non-`.xlsx` uploads are rejected before the parse (413/415)
- [ ] Both `etc/caddy/Caddyfile` and `Caddyfile.example` carry a
      `request_body { max_size ... }` cap covering the import path
- [ ] `just frontend-generate-api` run and both regenerated files committed;
      `cd backend && uv run pytest -m unit -k openapi` passes
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The "Current state" excerpts don't match the live code (drift).
- Resolving `CurrentUserProvider` / `PermissionService` via `FromDishka` in the
  route raises a DI resolution error at import/startup — report the error rather
  than working around it (it would signal a scope/provider issue worth a human's
  eyes).
- The installed Starlette version does not expose `UploadFile.size` at all
  (not just returns `None`) — report so the size strategy can be reconsidered.
- The Caddy `request_body` directive name/placement can't be confirmed against
  current docs for the version in use.

## Maintenance notes

- If more upload endpoints appear, promote the size/type guard and the
  auth-before-work pattern into a shared FastAPI dependency (`require_permission`)
  — deliberately deferred here to keep this change small.
- A reviewer should confirm the interactor's own auth check is still present
  (defense in depth — the route gate is an optimization, not the sole guard) and
  that the proxy cap and the app cap don't contradict (proxy cap ≥ app cap).
- The `_MAX_IMPORT_BYTES` value is a guess sized to "a few hundred rows"; revisit
  if a real festival schedule ever approaches it.
