# ADR-0049: Use cosplay2py for Cosplay2 sync

- **Status:** Accepted
- **Date:** 2026-10-30

## Context

Cosplay2 sync duplicates vendor endpoints and response models in a hand-written
HTTP client. The requested replacement, [cosplay2py](https://github.com/Arutemu64/cosplay2py),
provides typed async reads for topics and event applications on our existing
httpx2 stack.

## Decision

Use `AsyncCosplay2` from `cosplay2py>=0.3.0,<0.4` in `Cosplay2Source`.
Keep `CosplaySource` and its neutral DTOs as the application boundary.
The APP-scoped provider supplies existing configuration and timeouts and owns
client cleanup. Remove the local client and vendor DTOs.

The first release we adopt was published today. Exempt this package from uv's
seven-day release cutoff so it can resolve; keep the cutoff for all other
packages. Remove that exception after the initial release has aged seven days.

## Consequences

The SDK owns authentication headers, validation, and read retries. Its stricter
models require complete vendor responses. Failures propagate to the existing
sync tracker. Only approved applications with a nonempty voting title become
participants, as before.

SDK defaults retry transport failures and 429/502/503/504 twice, with a
30-second Retry-After ceiling. HTTP 500 is no longer retried. Mock-transport
tests exercise real SDK parsing and source mapping without contacting the vendor.
The dependency is locked to 0.3.0; the upper bound requires review before adopting
a potentially breaking 0.x minor release.

Keeping the local client would retain duplicated vendor behavior. Adding another
wrapper around the SDK would introduce a layer with no translation responsibility.
