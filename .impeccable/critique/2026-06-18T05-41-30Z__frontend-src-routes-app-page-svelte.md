---
target: main page
total_score: 31
p0_count: 0
p1_count: 2
timestamp: 2026-06-18T05-41-30Z
slug: frontend-src-routes-app-page-svelte
---
# Critique — Main Page (`(app)/+page.svelte`)

Mobile-first home: hero card (countdown + date/venue + socials + key art) over a state-driven "Подготовься к фестивалю" action-card grid.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Live countdown + shell ConnectionBanner; strong signaling |
| 2 | Match System / Real World | 4 | Native Russian, correct 3-form plural declension, real venue/map |
| 3 | User Control and Freedom | 3 | PWA install button gives no in-component feedback; new-tab links unflagged |
| 4 | Consistency and Standards | 3 | Icon-bubble drift: h-9 vs h-11, rounded-xl vs rounded-2xl |
| 5 | Error Prevention | 3 | No failure/placeholder state if key art image fails to load |
| 6 | Recognition Rather Than Recall | 4 | Everything visible; icons + labels paired |
| 7 | Flexibility and Efficiency | 3 | No during-event path; section vanishes for done-everything users |
| 8 | Aesthetic and Minimalist | 3 | Eyebrow + glow + 4 co-equal cards add mild noise |
| 9 | Error Recovery | 2 | No empty/offline state for home content itself |
| 10 | Help and Documentation | 2 | No first-timer orientation on what the app does |
| **Total** | | **31/40** | **Good — solid foundation, rough edges at states** |

## Anti-Patterns Verdict

Does this look AI-generated? Mostly no — but two decorative tics and one card grid sit on the line.

LLM: Page escapes slop because substance is real — key art, real address+map, socials, behaviorally-driven to-do grid (`$derived.by`). Three tells: (1) GetReadySection is the named "identical icon-card grid" anti-ref, rescued by meaning-mapped accents + link-vs-button affordance but every card has identical visual weight; (2) blur-3xl primary glow (HeroCard:72-76) = "atmospheric glow" tic, one instance, defensible but task-valueless; (3) uppercase tracked eyebrow "ДО НАЧАЛА ФЕСТИВАЛЯ" (HeroCard:131-135) = literally the banned trope, survivable (once, labels live data) and redundant with aria-label. No gradient text.

Deterministic scan: detect.mjs ran clean across all five files — exit 0, zero findings, `[]`. Detector and review agree: nothing mechanically slop-flagged. Remaining concerns are judgment calls a regex won't catch.

Visual overlays: No headless browser in this environment — no overlay produced.

## Overall Impression

Competent, on-brand product home; does NOT read as AI slop at a glance. A11y discipline is senior-level (countdown grid aria-hidden with static-date SR fallback, seconds don't flip, reduced-motion gated in CSS+JS). Biggest opportunity isn't slop — it's temporal relevance: hero is built around a countdown to festival START, which hits zero exactly when most users open the app (during the con), degrading to a static date while to-do cards become stale chores. No "happening now / next up" mode.

## What's Working

1. A11y + reduced-motion is the opposite of slop (HeroCard:136-166, 243-248).
2. The card list is real product logic, not a static feature grid (GetReadySection:64-128).
3. Russian is native-quality — proper день/дня/дней declension with 11-14 special case (HeroCard:47-61).

## Priority Issues

[P1] Hero image eager + placeholderless — emotional peak loads as grey box on con wifi. /main.webp (1500x844, loading=eager, no LQIP) is top aspect-[16/9] block. Fix: brand-tinted bg bed + blur-up on wrapper. → /impeccable harden

[P1] Countdown has no during-event mode — dies when most users arrive. Once hasStarted, hero collapses to static date; get-ready cards become stale. Fix: flip hero post-hasStarted to "Идёт сейчас / Дальше" mode linking to schedule. → /impeccable shape

[P2] Card grid has no internal hierarchy — peak-end ends flat. 4 co-equal cards; user can't tell which step matters. Fix: promote the most important card (account for guests, ticket for ticketless) to full-width or bg-primary-50 fill. → /impeccable layout

[P2] No empty/orientation state. Section vanishes for done-everything users (GetReadySection:131); first-timer gets no app-purpose. Fix: teaching state when cards.length===0 + one-line app purpose under hero. → /impeccable onboard

[P3] Muted 12px gray-500 body at legibility floor (GetReadyCard:45, GetReadySection:137). ~4.8:1, faint at 12px. Fix: bump to text-gray-600. → /impeccable polish

## Persona Red Flags

Casey (mobile): new-tab links unflagged (HeroCard:181-204); primary action below image+countdown+venue+socials. Targets are 44px+.
Jordan (first-timer): no app orientation; win — "Создать аккаунт" explains why.
Tired teen mid-con (project persona): zeroed countdown + static date + stale chores; home doesn't serve during-event need; battery drains on 1s interval for static screen.

## Minor Observations

- Dead width: max-w-6xl (+page.svelte:14) inside shell max-w-5xl (+layout:41) never applies.
- Three values for one icon-bubble motif — tokenize.
- Countdown date shown twice (intentional for SR, visually redundant).
- actionLabel default "Открыть" + arrow generic; use verb-specific labels.
- PWA card button has no loading/disabled state.

## Questions to Consider

1. Should the hero flip to "happening now / next up" post-start instead of a static date?
2. Is "Подготовься" a home feed or an onboarding checklist in disguise? What fills the gap when it vanishes?
3. When does "just one" instance of a banned pattern (glow, eyebrow) become the slop you're auditing against?
4. Four equal-weight cards: hierarchy, or just alignment?
