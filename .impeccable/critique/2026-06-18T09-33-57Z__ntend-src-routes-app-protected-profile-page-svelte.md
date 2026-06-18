---
target: profile
total_score: 30
p0_count: 0
p1_count: 2
timestamp: 2026-06-18T09-33-57Z
slug: ntend-src-routes-app-protected-profile-page-svelte
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Button spinners, toasts, stale notice, push-state probe all present; page itself blocks on load() (no skeleton) |
| 2 | Match System / Real World | 3 | Warm Russian copy throughout; raw "ID аккаунта" exposes a technical Telegram id |
| 3 | User Control and Freedom | 3 | Modals dismiss via Esc/outside; verify step correctly locks outside-close; no Cancel button but standard |
| 4 | Consistency and Standards | 4 | Uniform ProfileCardShell, min-h-11 targets, alternative=secondary everywhere — cohesive |
| 5 | Error Prevention | 2 | Telegram "Отвязать" fires immediately on click — destructive, no confirm dialog |
| 6 | Recognition Rather Than Recall | 3 | Everything labeled, icons paired with text; no memory demands |
| 7 | Flexibility and Efficiency | 3 | "Проверить уведомления" is a nice power affordance; no shortcuts (fine for mobile profile) |
| 8 | Aesthetic and Minimalist Design | 3 | Calm and uncluttered, but 5 identical card headers + dev-vanity footer add noise |
| 9 | Error Recovery | 3 | getApiErrorDetail gives specific inline messages, form not wiped, OTP error states good |
| 10 | Help and Documentation | 3 | Abundant inline helper text + iOS PWA explainer modal; no dedicated help |
| **Total** | | **30/40** | **Good — solid foundation, address weak areas** |

## Anti-Patterns Verdict

**Does this look AI-generated?** Mostly no — it reads as a competent settings surface with earned familiarity. But two settings-template tells are present.

**LLM assessment**: The repeated `ProfileCardShell` (gray icon-chip + bold title + muted description, ×5 stacked) is the canonical SaaS-settings card template. DESIGN.md explicitly bans "identical icon-card grids," and the profile is exactly that — five visually-identical shells. Consistency is a product virtue, but here it tips into monotony: nothing signals that "Основные данные" (identity) is a different *kind* of thing from "Уведомления" (settings). The neutral gray icon chips are decorative — they don't earn their place per the project's own Color-Earns-Its-Place rule. Watermelon primary barely appears on this page (only filled buttons); for a brand whose whole thesis is "color carries the joy," the profile reads gray and flat.

**Deterministic scan**: `detect.mjs` on the profile directory returned `[]` (exit 0) — clean, no automated slop hits. The detector does not catch the two tells below; both are manual findings.

**Visual overlays**: No browser automation available in this environment, so no live overlay was injected and no `[Human]` tab exists. Fallback: source + detector review only.

## Overall Impression

Competent, calm, on-spec for "the tool disappears into the task." Resilience is genuinely first-class (stale notice, cached load, optimistic-with-rollback toggles, guarded unlink). The biggest opportunity: the page is *too* uniform and *too* gray — it fully nails the "structure carries the calm" half of the brand but forgets the "color carries the joy" half, and the identical-shell repetition flirts with the settings-template look the design system explicitly rejects.

## What's Working

1. **Resilience is real, not decorative.** Stale/offline notice, `fetchWithCache` with hard-fail only on full miss, push toggles that roll back on API error, Telegram unlink blocked until an email recovery path exists. This is the "calm-under-load" personality executed properly.
2. **Consistent component vocabulary.** Every secondary action is `color="alternative"`, every tap target is `min-h-11`, every card is the same shell. A user learns the surface once. This is exactly what the product register rewards.
3. **Thoughtful OTP/email flow.** The verify step locks outside-close to protect an in-flight code, resend has a 60s cooldown, errors are specific and inline. High-stakes moment handled with care.

## Priority Issues

- **[P1] Destructive Telegram unlink has no confirmation.** `SecurityCard` line 166–180: clicking "Отвязать" calls `handleTelegramUnlink` immediately. For a teen who may have linked Telegram as their main login, one mis-tap removes a login method. The email-required guard prevents lockout but not accidental unlinking.
  - **Why it matters**: Error Prevention is the weakest heuristic (2/4); a single tap performs an irreversible account change with no speed bump.
  - **Fix**: Add a confirm step — inline "точно отвязать?" two-button swap, or a small confirm modal. Match the same pattern wherever else destructive actions live.
  - **Suggested command**: `/impeccable harden`

- **[P1] Five identical card shells read as a settings template.** Every section is the same gray-icon-chip header. DESIGN.md bans "identical icon-card grids"; the identity card and the settings cards deserve different visual weight.
  - **Why it matters**: Visual monotony + the exact AI-settings look the brand rejects. Nothing tells the eye what's primary.
  - **Fix**: Make `BasicUserInfoCard` visually distinct (larger, watermelon-tinted header or accent, no gray chip), and demote/vary the settings cards. Use hierarchy, not five clones.
  - **Suggested command**: `/impeccable layout`

- **[P2] Brand color is almost absent — page reads gray.** Watermelon primary appears only on filled buttons; every icon chip, badge, and accent is neutral gray. The brand thesis ("color carries the joy") isn't expressed on a core daily surface.
  - **Why it matters**: On-spec emotionally-flat; the convention's energy is missing where attendees spend time.
  - **Fix**: Introduce primary tint strategically — active/connected states, the identity card, the ticket-linked confirmation. Keep it on state, not decoration (respect Color-Earns-Its-Place).
  - **Suggested command**: `/impeccable colorize`

- **[P2] Banned eyebrow pattern inside the notifications card.** `PushNotificationsCard` lines 271 & 320: "КАНАЛЫ" and "ТИПЫ УВЕДОМЛЕНИЙ" are tiny uppercase tracked labels — the exact eyebrow the parent skill and DESIGN.md call out (label uppercase is reserved for status pills only).
  - **Why it matters**: A direct rule violation and a recognizable AI tell, twice in one card.
  - **Fix**: Replace with sentence-case sub-headers (`text-sm font-semibold`, no uppercase/tracking), or drop the dividers and let spacing group the rows.
  - **Suggested command**: `/impeccable typeset`

- **[P2] Raw technical detail + dev-vanity copy leak to a non-tech teen.** `SecurityCard` shows "ID аккаунта: {provider_id}" (a meaningless number to the user), and the page footer reads "Работает на Svelte и FastAPI." Neither serves an attendee.
  - **Why it matters**: Aesthetic-minimalist + Match-real-world both ding; it's clutter and jargon on an audience explicitly defined as non-technical.
  - **Fix**: Drop the raw provider id (or replace with the Telegram @username if available). Cut the tech-stack footer line; keep the warm "С любовью" line if you want personality.
  - **Suggested command**: `/impeccable clarify`

## Persona Red Flags

**Casey (Distracted Mobile User)** — the primary persona here:
- One-tap destructive unlink (`SecurityCard`) is dangerous for a thumb on the move; no confirm = accidental account change.
- Otherwise strong: actions are full-width, bottom-nav padding + safe-area handled in the layout, state persists via cached load on return.

**Sam (Accessibility-Dependent)**:
- Toggle state is conveyed by Flowbite's visual switch; verify these announce checked/disabled to screen readers (the `aria-label`s are present — good).
- Password show/hide buttons have proper `aria-pressed` + `aria-label` and focus-visible rings — solid.
- Telegram connected/disconnected uses a Badge with *text* ("Подключён"/"Не подключён"), not color alone — good. Confirm `green`/`gray` badge contrast in dark mode.

**"Лера", tired teen attendee (project persona)** — non-tech, phone, between events:
- "ID аккаунта: 84727…" means nothing to her — reads as scary technical noise.
- The footer's framework names are irrelevant; she came to manage her ticket and notifications.
- Page feels gray/utilitarian — none of the convention's watermelon energy she sees on the key art.

## Minor Observations

- `BasicUserInfoCard` passes `title="Основные данные"` to the shell *and* renders its own @username/role block — the generic "Основные данные / Всё о тобе" header is slightly redundant above the actual identity content.
- `getRoleColor` can return `yellow`; a yellow role badge sits visually close to the yellow no-email warning Alert in the same column — check they don't read as the same signal.
- Test-notification button label "Проверить уведомления" is good; the success toast is long ("тост, колокольчик и системное пуш-уведомление") — fine but near the toast length limit on a narrow phone.
- ProfileCardShell uses `shadow-sm` on every card; DESIGN.md sanctions `shadow-sm` only for standalone tappable list items — these cards aren't tappable, so per the Border-Before-Shadow rule they should rely on border + tonal step alone.

## Questions to Consider

- What if the identity card looked like *you* (avatar-forward, a touch of watermelon) and the settings cards were quieter beneath it — instead of five equal clones?
- Does the unlink need to be one tap, or should a destructive account change always cost two?
- Where on this page does an attendee actually *feel* the convention? Right now: nowhere. What single moment could carry the brand?
