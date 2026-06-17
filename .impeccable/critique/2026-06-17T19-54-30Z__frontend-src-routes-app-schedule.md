---
target: schedule
total_score: 28
p0_count: 0
p1_count: 2
timestamp: 2026-06-17T19-54-30Z
slug: frontend-src-routes-app-schedule
---
# Critique — Schedule (frontend/src/routes/(app)/schedule)

## Design Health Score: 28/40 (Good, bottom edge)

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Strong feedback; no list skeleton; mark-current toast-only |
| 2 | Match System / Real World | 3 | ты/вы formality mixed across sibling modals |
| 3 | User Control & Freedom | 3 | SubscribeModal no Cancel; modal footers inconsistent |
| 4 | Consistency & Standards | 2 | Copy tone + modal footers + display font diverge |
| 5 | Error Prevention | 3 | Counter clamp, disabled steps, unsubscribe confirm |
| 6 | Recognition Rather Than Recall | 3 | Icons+labels, visible filters |
| 7 | Flexibility & Efficiency | 3 | Inline bell, jump-to-current FAB, search |
| 8 | Aesthetic & Minimalist | 3 | Clean; empty-state glow + display heading decorative |
| 9 | Error Recovery | 3 | Plain inline Russian errors |
| 10 | Help & Documentation | 2 | None; low-need domain |

## Anti-Patterns Verdict
Not AI slop. detect.mjs clean (exit 0, []). EventCard real craft: optimistic skip, two-tier sticky headers, reduced-motion ping, aria-pressed bell.

## What's Working
1. EventCard state model — optimistic skip self-healing $effect, live badge, inline subscribe. Best component in app.
2. Sticky two-tier hierarchy (block pink chip / nomination cyan dot / rows).
3. Resilience: stale notice, SSE invalidate, one-tap no-results recovery.

## Priority Issues
[P1] Staff dropdown likely clipped by overflow-clip nomination wrapper (+page.svelte:251). Flowbite Dropdown inline + Floating UI absolute strategy. Bottom-row staff actions unreachable. Fix: portal/strategy:fixed. → harden
[P1] Modal vocabulary inconsistent: ты/вы mix (Subscribe neutral, Move/Unsubscribe ты) + footers differ (1 btn / Отмена+action / disabled-gated). Fix: one register, Отмена everywhere, same order. → clarify
[P2] font-display in empty-state headings (+page.svelte:293) violates Inter-For-The-Job; reserve Unbounded for № signature. → typeset
[P2] SubscribeModal stepper fragile: w-44 input + absolute overlapping label + pb-5 number; collision risk on 3-digit. → distill

## Persona Red Flags
Casey (mobile): served; two stacked FABs may crowd on small phones.
Sam (a11y): strong; SubscribeModal no Cancel (Esc/backdrop only); visible "выступлений" not linked to input.
Staff organizer: P1 dropdown clip; mark-current lacks optimistic feedback (skip has it) — double-tap risk on flaky wifi.

## Minor
- MoveEventModal console.error noise in prod (lines 62,73).
- Empty-state blur-3xl glow only decorative-only element.
- scroll-mt-28 magic number couples to header heights.
