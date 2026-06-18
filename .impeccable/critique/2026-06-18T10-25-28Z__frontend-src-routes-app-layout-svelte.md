---
target: general app shell (navbar, sidebar, bottom nav, main container)
total_score: 29
p0_count: 0
p1_count: 0
timestamp: 2026-06-18T10-25-28Z
slug: frontend-src-routes-app-layout-svelte
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | ConnectionBanner + active states strong; sidebar vs bottom-nav active state diverges |
| 2 | Match System / Real World | 3 | Clear RU labels, standard icons; thumbs-up is a loose metaphor for "voting/nominations" |
| 3 | User Control and Freedom | 3 | Dismiss/close/skip-link all present; logout has no confirm (low risk) |
| 4 | Consistency and Standards | 3 | Two nav systems signal "current" differently; red-vs-primary unread dot; dark border shade drift |
| 5 | Error Prevention | 3 | Locked staff rows prevent forbidden nav; logout unconfirmed |
| 6 | Recognition Rather Than Recall | 3 | Labeled nav everywhere; locked-row reason is hover-only title |
| 7 | Flexibility and Efficiency | 3 | Bottom nav fast-path + skip link; no accelerators (fine for phone PWA) |
| 8 | Aesthetic and Minimalist Design | 3 | Clean and near-flat; mobile hamburger duplicates the bottom nav for regular users |
| 9 | Error Recovery | 3 | ConnectionBanner reconnect + honest copy; toasts elsewhere |
| 10 | Help and Documentation | 2 | Only contextual help is the locked-item tooltip |
| **Total** | | **29/40** | **Good — solid foundation, address consistency drift** |

## Anti-Patterns Verdict

Does NOT look AI-generated. Earned familiarity: Flowbite substrate tuned to a documented design system, restrained gray shell with watermelon reserved for action/active state. Detector clean (0 findings across all 7 shell files). No cream bg, no eyebrows, no gradient text, no side-stripes, no card-grid. The shell passes the product slop test — a Linear/Notion-fluent user would trust it.

The slop risk here is the inverse of decoration: the shell is *so* gray that brand identity nearly vanishes from it (the one sanctioned Unbounded moment — the wordmark — is plain Inter).

## Overall Impression

Competent, calm, system-faithful app shell. Resilience (ConnectionBanner three-state) and accessibility (skip link, focus rings, 44px targets, aria roles) are genuinely first-class. The weaknesses are all consistency drift, not structural: the two mobile nav systems disagree on how they show "current location," the unread dot contradicts the design system's own color rule, and the brand never gets to speak in the shell. Single biggest opportunity: unify the nav active-state language and let the wordmark carry identity.

## What's Working

1. **ConnectionBanner is exemplary calm-under-load.** Three honest states (offline / lost / reconnecting), a 4s grace window so blips stay silent, role=alert vs status used correctly, motion-safe spinner, a real reconnect button. This is the "resilient by default" principle shipped, not promised.
2. **Accessibility baseline is real, not theater.** SkipLink → focusable #main-content with visible outline, 44px tap targets on bell, focus-visible rings throughout, aria-pressed on ThemeToggle, aria-disabled + aria-live used deliberately.
3. **Bottom nav is textbook for the brief.** 4 labeled destinations, safe-area inset, active = solid icon + primary (fill change paired with color, never color alone), thumb-zone fixed. Exactly the one-handed/one-glance principle.

## Priority Issues

- **[P2] Mobile navigation is duplicated.** Bottom nav and the hamburger sidebar both expose Home/Schedule/Map/Voting. For a regular (non-staff) attendee, the hamburger contains *only* duplicates of the thumb-reach bottom bar plus Feedback + theme. Two nav models, two active-state systems that can disagree, for one set of destinations.
  - Why it matters: extraneous cognitive load and a "which one do I use?" pause; the hamburger earns its place only for staff/org/feedback/theme.
  - Fix: for non-staff users, drop the hamburger entirely (or repurpose it to a slim "more" containing Feedback + theme + profile); keep the full sidebar for staff/desktop. Make active state identical across both.
  - Suggested command: /impeccable distill

- **[P2] Unread dot uses bg-red-500, contradicting the design system.** DESIGN.md lists "unseen-notification dots" under primary-600. Red reads as error/danger, not "new," and there's no count.
  - Why it matters: self-inconsistency, and red mis-signals — an attendee glances and reads "problem," not "new notification."
  - Fix: switch the dot to bg-primary-600 / dark:bg-primary-500; consider a small count for >1.
  - Suggested command: /impeccable colorize

- **[P2] Sidebar and bottom nav disagree on "current location."** Bottom nav swaps idle→solid icon in primary on active; the sidebar's icon class is static (gray-500) regardless of active, so the active sidebar item's icon never goes primary. The two primary navs signal selection differently.
  - Why it matters: weakens recognition of where-am-I and reads as two different products stitched together (Heuristic 4).
  - Fix: drive the sidebar icon color/fill off activeUrl the same way the bottom nav does (solid + primary on active).
  - Suggested command: /impeccable polish

- **[P3] Brand wordmark not set in Unbounded.** The sidebar "ФАН ФАН" is text-xl font-semibold Inter. Per the system, the wordmark is the *one* sanctioned Unbounded identity moment — and it's the brand's only appearance in the shell.
  - Why it matters: the shell loses its single chance to carry identity; the watermelon system is invisible at rest, so the wordmark is where personality should live.
  - Fix: set the wordmark in Unbounded Variable (font-display), keep everything else Inter.
  - Suggested command: /impeccable typeset

- **[P3] Locked staff-row reason is hover-only.** The "Нужен доступ — попроси организатора" explanation lives in a `title` attribute; on touch (the primary device) and for keyboard users it never appears, leaving a greyed row + lock icon with no stated reason.
  - Why it matters: mobile-first audience can't discover why an item is locked.
  - Fix: surface the reason inline (subtext) or via a tap/press affordance, not hover.
  - Suggested command: /impeccable clarify

## Persona Red Flags

**Casey (Distracted Mobile User):** Opens the hamburger and finds the same four items already under their thumb — a wasted tap. The red unread dot reads as "something's wrong" mid-scroll. Otherwise thumb-zone, safe-area, and state-preservation are handled well.

**Jordan (Confused First-Timer):** Two ways to reach Schedule (bottom bar + hamburger) invites "are these different?" hesitation. A locked staff row shows a lock but no reason on their phone (hover-only title). Wordmark doesn't establish a memorable brand anchor on first load.

**Sam (Accessibility-Dependent):** Strong baseline — skip link, focus rings, aria roles, 44px targets. But the unread state is conveyed by a color dot with no text/count, and the locked-row reason is hover-only — both fail "don't rely on hover/color alone." Non-navigable locked rows (no href) may also drop out of tab order.

## Minor Observations

- Dark border shades drift: navbar dark:border-gray-700/50 vs sidebar/bottom-nav dark:border-gray-800. DESIGN.md border standard is gray-700. Pick one.
- Navbar is translucent white/80 + backdrop-blur-md (a light glass treatment). Defensible for a sticky header, but it's the one spot edging toward the "glass by default" ban — keep it intentional.
- Notification dropdown header "Уведомления" has text-center inside a justify-between flex row (no effect).
- Logout drops the cache and requires re-login — on flaky con wifi that's a sharp edge for an accidental tap; a confirm or undo-toast would soften it.
- Voting permanently occupies 1 of 4 bottom-nav slots though it's time-bound; worth revisiting whether it earns a fixed slot year-round.

## Questions to Consider

- For a regular attendee, what does the hamburger menu give them that the bottom bar doesn't — and if the answer is "nothing," should it exist for them?
- If the watermelon palette is the brand's whole personality, why is the shell almost entirely gray? Where is the one moment it should sing?
- Should "current location" look identical in every nav surface, so the app never feels like two products?
