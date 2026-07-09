# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project maintainers

## Context

This is a small, largely solo-maintained project with a deliberately opinionated
architecture (hexagonal layering, DDD aggregates, a transactional outbox, a
specific DI container, an SPA frontend). The rules for *how* to work within that
architecture are well documented in `AGENTS.md` and `docs/*.md`. What is **not**
captured anywhere is *why* each of those foundational choices was made, and what
was rejected on the way — that reasoning currently lives only in the
maintainer's memory.

That is the highest-risk kind of undocumented knowledge: onboarding a
contributor (human or AI) means re-deriving settled decisions, and there is
nothing to stop a well-meaning change from unknowingly reversing one. Living
guides describe the present; they are the wrong shape for a dated, immutable
record of a decision and its trade-offs.

## Decision

We will keep Architecture Decision Records in `docs/adr/`, one Markdown file per
significant decision, using the lightweight Nygard/MADR-style template in
[`template.md`](template.md) (**Context → Decision → Consequences**).

- ADRs are numbered `NNNN-kebab-title.md` and are **immutable once Accepted**.
- A superseding decision is a *new* ADR; the old one's status is updated to point
  at it.
- We write an ADR only for architecturally significant choices — new external
  dependency, changed deployment topology, or an expensive-to-reverse pattern —
  not for routine changes.
- The `docs/adr/README.md` index and this convention are pointed to from the
  repository guidelines.

## Consequences

- The reasoning behind foundational choices survives turnover and is reviewable
  in a PR alongside the code that embodies it.
- A small, ongoing discipline: PRs that make an architecturally significant
  decision are expected to add an ADR, and reviewers can ask for one.
- Guides (`docs/*.md`) and ADRs have distinct jobs — guides say "how it works
  now", ADRs say "why we chose it". We accept a little duplication at the seams
  in exchange for that clarity.
