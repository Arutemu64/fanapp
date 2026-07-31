# Architecture Decision Records (ADR)

This directory holds the project's Architecture Decision Records — short,
immutable documents that capture **why** a significant architectural choice was
made, the context around it, and the consequences we accepted. `AGENTS.md` and
the guides in [`docs/`](../) describe how the system works *today*; ADRs explain
*why it got that way* and *what we rejected* — the reasoning that would
otherwise live only in someone's head.

## When to write an ADR

Write one when a change:

- introduces a new external dependency or vendor integration,
- changes the deployment topology or a runtime boundary,
- picks a pattern or convention that would be **expensive to reverse**, or
- resolves a genuinely contested trade-off worth remembering.

Routine changes do **not** need an ADR. If a skill or guide that has never seen
this repo could already state the rule, it belongs in a `docs/*.md` guide, not
here.

## Format

We use a lightweight [Nygard-style](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
/ [MADR](https://adr.github.io/madr/)-inspired template: **Context → Decision →
Consequences**, with a status header. Keep each ADR to roughly one screen and
focused on a **single** decision. Copy [`template.md`](template.md) to start.

## Lifecycle

ADRs are **immutable once Accepted**. To change a past decision, write a *new*
ADR that supersedes the old one, and update the old one's status to
`Superseded by ADR-NNNN`. Never rewrite the reasoning of an accepted record —
git history and the supersession chain are the archive.

Statuses: `Proposed` → `Accepted` / `Rejected` → `Superseded` / `Deprecated`.

## Naming

`NNNN-kebab-case-title.md`, zero-padded, monotonically increasing. The number is
permanent — it is how other ADRs and commits reference the decision.

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-hexagonal-ddd-layering.md) | Hexagonal + DDD layering with enforced boundaries | Accepted |
| [0003](0003-persistence-gateways-over-repositories.md) | Persistence gateways over repositories (no CQRS split) | Accepted |
| [0004](0004-transactional-outbox-for-domain-events.md) | Transactional outbox for domain-event delivery | Accepted |
| [0005](0005-ports-as-protocol-with-explicit-adapter-subclassing.md) | Ports as `Protocol` with explicit adapter subclassing | Accepted |
| [0006](0006-dishka-for-dependency-injection.md) | Dishka for dependency injection | Accepted |
| [0007](0007-client-rendered-spa-frontend.md) | Client-rendered SvelteKit SPA frontend | Accepted |
| [0008](0008-schedule-timing-computed-in-application-layer.md) | Absolute schedule times computed in the application layer | Accepted |
| [0009](0009-yandex-smartcaptcha-over-cloudflare-turnstile.md) | Yandex SmartCaptcha over Cloudflare Turnstile | Accepted |
| [0010](0010-http-triggered-background-jobs.md) | HTTP-triggered background jobs use a status row, outbox and durable consumer | Accepted |
| [0011](0011-vitest-for-frontend-unit-tests.md) | Vitest for frontend unit tests | Accepted |
| [0012](0012-single-oauth-callback-keyed-on-the-oidc-subject.md) | One OAuth callback per provider, identity keyed on the OIDC subject | Accepted |
| [0013](0013-schedule-wait-derived-at-the-edge.md) | Schedule API publishes anchors; the wait is derived at each edge | Accepted |
