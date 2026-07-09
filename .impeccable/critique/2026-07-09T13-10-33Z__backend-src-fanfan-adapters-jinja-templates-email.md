---
target: email templates
total_score: 26
p0_count: 1
p1_count: 2
timestamp: 2026-07-09T13-10-33Z
slug: backend-src-fanfan-adapters-jinja-templates-email
---
# Critique: Auth Email Templates

Target: backend/src/fanfan/adapters/jinja/templates/ — _email_layout.jinja2, email_login_code.jinja2, email_confirmation_code.jinja2 (login code + email confirmation OTP emails).

## Design Health Score (7 applicable heuristics; 3 n/a for one-way transactional email)
| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Code + expiry clear; no "never share this code" cue |
| 2 | Match System / Real World | 3 | Plain Russian; brand name spelled 3 ways (ФАН ФАН / FAN FAN / email) |
| 3 | User Control and Freedom | n/a | one-way transactional |
| 4 | Consistency and Standards | 1 | Email brand orange+sky-blue vs app watermelon-crimson+teal |
| 5 | Error Prevention | 2 | {{ username }} renders literal None when unset |
| 6 | Recognition Rather Than Recall | 3 | Big labeled code |
| 7 | Flexibility and Efficiency | 3 | Code in subject line; no copy affordance |
| 8 | Aesthetic and Minimalist Design | 3 | Clean; gradient bar off-palette |
| 9 | Error Recovery | n/a | static email |
| 10 | Help and Documentation | 3 | Footer + ignore-if-not-you; no support contact |
Effective 21/28 (~26/40). Acceptable; one P0 showstopper.

## Anti-Patterns Verdict
Not AI slop — restrained, table-based, mirrors app card UI. Problem is wrong brand.
Detector: 30 issues across 2 rendered emails. 16x design-system-color (undocumented orange/sky-blue: #fe795d #ef562f #0ea5e9 #0369a1 #0284c7 #bae6fd #cc4522 #ffd5cc #4b5563) — none in app palette (primary #d61450, secondary #0c9fb8). 10x design-system-font + 4x overused-font (Inter/Unbounded via Google Fonts; Inter is documented — partial false positive; real issue is remote <link> loading).

## What's Working
1. Restraint and hierarchy — one card, one code, clear OTP peak.
2. Deliverability-aware — tables + inline styles + Outlook background-color fallback; code in subject line.
3. Copy — warm plain Russian, correct reassurance line.

## Priority Issues
[P0] Email brand identity contradicts the app. Wordmark/accent bar/confirmation code orange (#ef562f/#fe795d); login code sky-blue (#0284c7). App is crimson #d61450 + teal #0c9fb8. Layout comment literally says "orange wordmark" — predates watermelon palette. Auth email is highest-trust surface; mismatched palette reads as phishing. Fix: map all colors to real tokens (wordmark/accents -> primary-600 #d61450 + tints; login block -> secondary #0c9fb8 + #ecfdff; accent bar #d61450->#0c9fb8), ideally from a single shared source. -> /impeccable colorize

[P1] {{ username }} renders literal "None". Interactors pass user.username raw while recipient name falls back. Unset username -> "Здравствуйте, None!" (verified). Fix: template guard {% if username %} or interactor fallback. -> /impeccable harden

[P1] Low-contrast security text fails WCAG AA. Footer + "если вы не запрашивали" line are #9ca3af on white ~2.5:1 (AA needs 4.5). DESIGN.md commits to AA and flags this exact failure. Wordmark orange at 12px also fails. Fix: bump muted to >=#6b7280, security line #4b5563, small wordmark primary-700 #b30f43. -> /impeccable audit

[P2] HTML-only, no plain-text alternative. EmailMessage has only html_body; FastMail sends MessageType.html. Hurts spam scoring + text/screen-reader clients for an OTP that must deliver. Fix: add text_body, send multipart/alternative. -> /impeccable harden

[P2] Google Fonts <link> won't load in email (clients strip it) — Unbounded brand moment never renders; remote-content vector. Delete link/preconnect, keep inline fallback stacks. -> /impeccable distill

## Persona Red Flags
Casey (mobile, primary): code in subject good, responsive at 375px good; low-contrast lines vanish in sunlight; no tap-to-copy on code.
Sam (a11y): contrast fails (2.5:1); HTML-only no clean text fallback; role=presentation correct; lang=ru set; color-scheme unset -> dark-mode auto-invert risk.
Riley (stress): "Здравствуйте, None!"; brand name 3 ways in one email.

## Minor Observations
- Gradient bar decorative/off-palette; solid primary-600 more on-brand.
- No preheader text (low prio; code already in subject).
- Confirmation label #cc4522 on #fff5f2 ~4.4:1 borderline.
- Missing "Никому не сообщайте этот код" security nudge.
- Inconsistent recipient fallback ("" vs "Пользователь") across interactors.

## Questions to Consider
- Emails predate watermelon palette — drift nobody caught? A shared color source stops recurrence.
- Should confirmation feel more celebratory than login?
- Is HTML-only deliberate or an oversight?
