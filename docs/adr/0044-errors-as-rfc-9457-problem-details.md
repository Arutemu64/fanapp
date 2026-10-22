# ADR-0044: Errors as RFC 9457 problem details

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Project maintainers

## Context

Every error response was a home-grown `ErrorMessage { code, details }`. The
frontend branched on `code` (a closed enum in the spec) and picked Russian copy
from it, so the format worked. It was not a standard any HTTP tool or a future
second client would recognise. [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html)
defines that standard, `application/problem+json`. FastAPI has no built-in
support: the upstream proposal ([#14517](https://github.com/fastapi/fastapi/discussions/14517))
is unanswered and its PR was closed unmerged.

## Decision

We will answer every error as RFC 9457 problem details, media type
`application/problem+json`:

- **Standard members:** `type`, `title`, `status`. `type` is derived from the
  code, `/problems/<kebab-code>`: a relative reference with the full path, which
  §3.1.1 allows, since an absolute URI would need the deployment's host. Nothing
  is served there. `title` is the HTTP status phrase. No `detail` or `instance`.
- **`code` stays, as an extension member.** It is what the client branches on
  and what the spec stamps as an enum, with its compile-time copy check.
- **Problem-specific data are top-level extension members** (§3.2):
  `retry_after`, `reason`, `errors`, … The `details` wrapper is gone.
- One builder, `problem_response()` (`presentation/web/exceptions.py`), makes
  every error body. `FanfanAPI` moves each 4xx/5xx response in the spec to the
  problem+json media type.

## Consequences

- An error body is recognisable to generic tooling, and a second client gets a
  documented format instead of ours.
- `type` and `code` carry the same identity. They cannot disagree, since one is
  computed from the other, but a client must not be taught to parse `type`.
- Changing a code changes its `type` URI. Both are part of the contract.
- The frontend reads members from the top level (`getApiProblem` in
  `lib/api/errors.ts`). hey-api already parses any `+json` type as JSON.

## Alternatives considered

- **Keep `{ code, details }`.** RFC 9457 §4.1 itself says an existing format
  that carries the information is fine. Rejected by the maintainers in favour of
  the standard.
- **`type: about:blank` plus `code`.** §4.2.1 reserves `about:blank` for "no
  additional semantics beyond that of the HTTP status code", which our codes
  contradict.
- **Drop `code`, identify by `type`.** Would make the client parse URIs and
  would lose the enum in the spec that drives the copy check.
- **A per-code English `title`.** Never shown: the client renders Russian copy
  from `code`.
