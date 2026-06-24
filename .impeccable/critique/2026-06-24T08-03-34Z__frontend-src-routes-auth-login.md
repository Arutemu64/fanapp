---
target: login flow
total_score: 31
p0_count: 0
p1_count: 1
timestamp: 2026-06-24T08-03-34Z
slug: frontend-src-routes-auth-login
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Captcha invisible-token race shows soft error on first click; first code-send uses an inline Alert while resend uses a toast |
| 2 | Match System / Real World | 4 | Plain, warm Russian throughout; "Войти через Telegram", "Код подтверждения" read naturally |
| 3 | User Control and Freedom | 3 | Back + resend everywhere; minor structural inconsistency in where "Назад" lives |
| 4 | Consistency and Standards | 3 | "Назад" rendered by parent for password form but inside the component for verify; first-send Alert vs resend toast |
| 5 | Error Prevention | 3 | Inline email validation, numeric-only OTP, busy-locking; captcha-not-ready is a prevention gap |
| 6 | Recognition Rather Than Recall | 4 | Email persists across code/password modes; every control labeled |
| 7 | Flexibility and Efficiency | 3 | OTP paste + one-time-code autocomplete; short happy path; no real accelerators (fine here) |
| 8 | Aesthetic and Minimalist Design | 3 | Clean, on-brand; three stacked full-width buttons on the first screen add weight |
| 9 | Error Recovery | 3 | Plain Russian errors near source, 400-vs-other split; generic fallback string is vague |
| 10 | Help and Documentation | 2 | No "didn't get the email / check spam" guidance for a non-tech teen audience |
| **Total** | | **31/40** | **Good** |

## Anti-Patterns Verdict

**LLM assessment**: Does NOT read as AI-generated. This is a restrained, competent product login: brand crimson reserved for the single primary action, gray-50 field under a white card (not the cream/sand slop bg), no eyebrows, no gradient text, no icon-card grid, no side-stripe borders. Passes the product slop test — a user fluent in Linear/Stripe-grade tools would trust it and not pause at off components.

**Deterministic scan**: `detect.mjs --json` over `(auth)/` returned `[]` — zero findings. Clean.

**Visual overlays**: Browser automation unavailable in this remote container; no live overlay was produced. Fallback = source review + clean detector scan.

## Overall Impression

Genuinely solid. Resilient states are first-class (spinners, busy-locks, captcha handling, inline validation, OTP with paste/auto-advance/backspace). The single biggest opportunity is **hierarchy on the first screen**: three near-equal full-width buttons (Telegram, Продолжить, Войти с паролем) compete, and for a Telegram-native fandom audience the de-emphasized Telegram button may be backwards.

## What's Working

- **OTP input is excellent.** Auto-advance, backspace-back, paste-to-fill, `autocomplete="one-time-code"`, per-digit `sr-only` labels, numeric-only enforcement, 44px boxes. Best-in-class for the signature moment.
- **State conveyed by more than color.** Email validation pairs green/red border with helper text; busy states swap label + spinner; errors are Alerts with copy. Honors the "never color alone" rule.
- **Email persists across modes.** Switching code↔password keeps the typed address (bound through the parent) — recognition over recall, no re-typing.

## Priority Issues

- **[P1] First-screen hierarchy: three coequal full-width buttons.** Telegram (alternative), Продолжить (primary), Войти с паролем (light) stack as near-equal blocks. "One primary thing per screen" is diluted, and for a Telegram-heavy anime-con audience the fastest path (Telegram) is visually demoted while email-code gets the crimson. **Fix**: demote "Войти с паролем" to a text link under the form, and reconsider whether Telegram or email-code deserves the primary fill for this audience. **Command**: /impeccable layout
- **[P2] Captcha invisible-token race.** If the Turnstile token isn't ready when the user taps Продолжить, they get "Проверка ещё не завершена, попробуйте ещё раз через секунду" and must tap again — a soft failure at the very first action. **Fix**: keep the button enabled but show a brief pending state and auto-submit once the token resolves, or disable until ready with a quiet hint. **Command**: /impeccable harden
- **[P2] Inconsistent back-affordance + send feedback.** "Назад" is rendered by the parent for the password form but inside VerifyCodeForm; first code-send confirms with an inline green Alert while resend confirms with a toast. Same concept, two patterns. **Fix**: standardize back placement (own it in each form, or always in parent) and pick one send-confirmation channel. **Command**: /impeccable polish
- **[P2] No "didn't get the code" help.** Non-tech teens on flaky con wifi will hit missing/slow emails; the only recourse is a 60s resend cooldown. **Fix**: add a calm "Проверьте папку «Спам»" hint near the OTP and/or once the cooldown elapses. **Command**: /impeccable clarify
- **[P3] Dead focus call.** `document.getElementById('code-0')?.focus()` in CodeLoginForm targets an id that doesn't exist (the OTP boxes are `otp-digit-N`); OtpInput auto-focuses on mount so it's harmless but misleading. **Fix**: remove it. **Command**: /impeccable polish

## Persona Red Flags

**Casey (Distracted Mobile User)**: Primary action sits in a card centered vertically (`items-center`), so on a tall phone the buttons may land mid-screen rather than thumb-zone — acceptable but not optimal. State is preserved across code↔password (email persists) ✓. OTP paste and one-time-code autocomplete cut typing ✓. Resend cooldown is clear ✓. Main snag: the captcha race forces a second tap on a flaky connection — exactly when patience is lowest.

**Jordan (Confused First-Timer)**: First action is clear (email + Продолжить) and the "account created automatically" note removes signup anxiety ✓. But faced with three buttons, Jordan must decide between Telegram, code, and password with no hint which is recommended. If the email never arrives, there's no "check spam" guidance — Jordan stalls at the OTP screen. Generic "Произошла непредвиденная ошибка" gives no next step.

**FAN FAN attendee (project persona — teen anime fan, Telegram-native, on con wifi, in a hurry)**: Almost certainly already in the convention's Telegram bot, so Telegram SSO is plausibly the *fastest* path — yet it's the visually quietest button. Email-code adds an inbox round-trip on bad wifi. Worth questioning whether the default emphasis matches how this audience actually arrives.

## Minor Observations

- `disabled={isBusy && activeAction === null}` is a clever cross-form lock (disable inputs only when the *other* form is busy). It works but reads obscurely and has no comment — borderline against the "clear, simple code" rule.
- First-send path has no success toast while resend does; align for consistency.
- The generic catch-all error "Произошла непредвиденная ошибка" is an acceptable fallback but offers no recovery step.

## Questions to Consider

- For a Telegram-native fandom audience, should Telegram SSO carry the primary emphasis instead of email-code?
- Does the first screen need three login methods visible at once, or can password be progressive (link → reveal)?
- What does a confident "we already know you're in the Telegram bot" entry look like?
