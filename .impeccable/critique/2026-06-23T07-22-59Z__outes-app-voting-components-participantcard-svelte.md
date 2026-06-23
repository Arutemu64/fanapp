---
target: participant card
total_score: 32
p0_count: 0
p1_count: 0
timestamp: 2026-06-23T07-22-59Z
slug: outes-app-voting-components-participantcard-svelte
---
# Critique — ParticipantCard

## Design Health Score: 32/40 (Good)

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Vote count not optimistic (waits full invalidate refetch) |
| 2 | Match System / Real World | 4 | Clear Russian, heart=votes metaphor natural |
| 3 | User Control and Freedom | 4 | Cancel vote = real undo |
| 4 | Consistency and Standards | 3 | hover:shadow-md breaks no-shadow>sm rule; primary vs red hue close |
| 5 | Error Prevention | 3 | Gated by canVote/disabled; cancel reversible |
| 6 | Recognition Rather Than Recall | 4 | Everything visible |
| 7 | Flexibility and Efficiency | 3 | One tap to vote |
| 8 | Aesthetic and Minimalist Design | 2 | Voted card 4 hues; 4% watermark near-invisible noise |
| 9 | Error Recovery | 3 | Errors to toast; reversible state |
| 10 | Help and Documentation | 3 | Page-level instruction covers it |

## Anti-Patterns Verdict
Not AI slop. Detector detect.mjs => [] exit 0, zero findings. On-brand, restrained, correct RU pluralization, real undo. Browser overlay unavailable (needs live backend).

## Priority Issues
- [P2] hover:shadow-md on non-interactive card — false affordance + violates Border-Before-Shadow elevation rule. Fix: remove; use border-color/ring on hover. (/impeccable polish)
- [P2] Voted card color overload — crimson No + always-red heart + green ring + green badge + red cancel = 3-4 hues. Fix: mute heart to gray-400. (/impeccable quieter)
- [P2] 4%-opacity watermark = invisible noise, redundant with header No, collides with action row. Fix: remove or commit. (/impeccable distill)
- [P3] 38px buttons under project's own 44px tap floor. Fix: bump to 44px + match reserved row min-h. (/impeccable adapt)
- [P3] Long unbroken title can overflow h3. Fix: add break-words. (/impeccable harden)

## Persona Red Flags
- Casey (mobile, primary): 38px < 44px thumb floor; non-optimistic count feels dead on flaky wifi.
- Sam (a11y): HeartSolid missing aria-hidden; no aria-live on vote state change. Contrast OK.
- Riley (stress): long-title overflow; double-vote guarded; null voting_number handled.

## Minor Observations
- aria-hidden the decorative heart.
- aria-live="polite" region for count change.
- Optimistic count bump fits calm-under-load brand.
