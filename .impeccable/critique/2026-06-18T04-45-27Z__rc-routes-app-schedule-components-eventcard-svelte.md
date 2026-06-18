---
target: schedule management changes
total_score: 33
p0_count: 0
p1_count: 0
timestamp: 2026-06-18T04-45-27Z
slug: rc-routes-app-schedule-components-eventcard-svelte
---
# Critique: Schedule management changes (EventCard staff strip, ConfirmActionModal, MoveEventModal warning)

## Health Score: 33/40 (Good)

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Confirm → toast on every action; optimistic skip flip; live/skip badges |
| 2 | Match System / Real World | 3 | Good metaphors; "Снять отметку" uses a play icon (implies start) |
| 3 | User Control and Freedom | 3 | Отмена + Esc/backdrop on modal; no toast-undo (confirm replaces it) |
| 4 | Consistency and Standards | 3 | Amber borderless warning diverges from app's yellow bordered StaleDataNotice/Alert |
| 5 | Error Prevention | 4 | Headline win: confirm before irreversible push broadcast |
| 6 | Recognition Rather Than Recall | 4 | Actions now visible inline + labeled vs hidden overflow dropdown |
| 7 | Flexibility and Efficiency | 3 | Every staff action now 2 taps; hot "mark current" repeated during live show |
| 8 | Aesthetic and Minimalist | 3 | Staff strip repeats 3 buttons per card; warning on every confirm incl. low-stakes |
| 9 | Error Recovery | 3 | toast.error on failure; optimistic skip reverts; API messages generic |
| 10 | Help and Documentation | 3 | Warning note is good contextual help |

## Anti-Patterns Verdict
Not AI slop. Uses existing design system, mobile-first, no banned patterns (no side-stripe, gradient text, glass, eyebrow). Detector clean (0 findings). Only off-system choice: amber warning box.

## Priority Issues
- [P2] Staff strip tap targets are 36px (h-9), below the 44px target PRODUCT sets for phone users (staff are non-tech, on phones too).
- [P2] Warning callout off-pattern: amber + no border vs canonical yellow bordered StaleDataNotice. Consistency + off-palette (DESIGN warning token is yellow-500).
- [P2] No primary emphasis in staff strip: "Отметить текущим" (repeated live-show action) reads same weight as Перенести/Пропустить — three equal ghost buttons.
- [P3] "Снять отметку" uses PlayOutline; play implies start, not stop.
- [P3] Warning fires on every confirm including low-stakes unmark/restore; slightly heavy.

## Persona Red Flags
- Casey (mobile): 36px targets under 44; right-aligned strip stair-steps when it wraps on narrow phones. Bottom-of-card placement is good thumb zone.
- Sam (a11y): skip uses red text + icon + label (not color alone) — good; confirm color OK; rely on flowbite Modal for focus trap/Esc — verify focus moves in.
- Organizer at soundboard (live op): extra confirm tap on every mark-current during a fast show is the main friction; justified by irreversible broadcast, but the hot action pays the most.
