---
name: FAN FAN
description: Mobile-first PWA that puts a Russian anime convention in the attendee's pocket.
colors:
  primary-50: "#fff1f5"
  primary-100: "#ffe3ea"
  primary-200: "#ffccd9"
  primary-300: "#ff9fb9"
  primary-400: "#fb6491"
  primary-500: "#f4316b"
  primary-600: "#d61450"
  primary-700: "#b30f43"
  primary-800: "#960d3a"
  primary-900: "#7d1035"
  secondary-50: "#ecfdff"
  secondary-100: "#cff7fc"
  secondary-200: "#a3eef9"
  secondary-300: "#66dfef"
  secondary-400: "#1fc6d9"
  secondary-500: "#0c9fb8"
  secondary-600: "#07788c"
  secondary-700: "#0a6173"
  secondary-800: "#0e4f5e"
  secondary-900: "#103f4c"
  surface-light: "#ffffff"
  surface-dark: "#1f2937"
  app-bg-light: "#f9fafb"
  app-bg-dark: "#030712"
  ink: "#111827"
  ink-inverse: "#ffffff"
  muted-light: "#6b7280"
  muted-dark: "#9ca3af"
  border-light: "#e5e7eb"
  border-dark: "#374151"
  danger: "#ef4444"
  warning: "#eab308"
  success: "#22c55e"
typography:
  display:
    fontFamily: "Unbounded Variable, Inter Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "normal"
  headline:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "normal"
  title:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  body:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.05em"
rounded:
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary-600}"
    textColor: "{colors.ink-inverse}"
    rounded: "{rounded.lg}"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.primary-700}"
    textColor: "{colors.ink-inverse}"
  button-alternative:
    backgroundColor: "{colors.surface-light}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    height: "44px"
  input-default:
    backgroundColor: "{colors.surface-light}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "42px"
  card:
    backgroundColor: "{colors.surface-light}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "16px"
  notice-warning:
    backgroundColor: "{colors.warning}"
    textColor: "{colors.warning}"
    rounded: "{rounded.lg}"
    padding: "10px 12px"
---

# Design System: FAN FAN

## 1. Overview

**Creative North Star: "The Pocket Convention"**

FAN FAN is the entire anime festival, thumb-first, in seconds. The user is a tired teen between events, one-handed, on flaky con-venue wifi, looking up what's next or casting a vote. The interface gets out of the way: bottom-anchored navigation on phones, a left sidebar on desktop, a single scannable column of content capped at `max-w-5xl`, and generous 44px tap targets everywhere. The tool disappears into the task.

The personality is **clear, lively, calm-under-load**. Vibrance comes from the watermelon palette — crimson-pink primary, cyan-teal secondary, pulled straight from the FAN FAN key art — and it is the *only* flourish. Color does the emotional work in primary actions, active nav, unseen-badges, and state moments; the layout itself stays quiet, near-flat, and uncluttered. Surfaces separate by border and tonal layering, not by drop shadows. Density is low by intent: one primary thing per screen, breathing room around it, so a glance is enough.

This system explicitly rejects three things. It is not **childish or cartoonish** — the audience is young but wants to be taken seriously, so no sticker overload and no comic-book energy. It is not **generic AI slop** — no cream/sand body background, no tiny uppercase tracked eyebrows over every section, no identical icon-card grids, no gradient text. And it is not **cluttered** — no wall of information, no cramming; phone-first means hierarchy and air.

**Key Characteristics:**
- One-handed, one-glance: bottom nav on mobile, sidebar on desktop, single capped column.
- Color carries the joy; structure carries the calm.
- Near-flat surfaces — borders and tonal layering over shadows.
- Resilient by default: skeletons, cached-shell offline boot, calm error and stale states.
- Light and dark mode, WCAG AA, full `prefers-reduced-motion` support.

## 2. Colors

A watermelon duo over a cool gray neutral field: warm crimson-pink for action and identity, cool cyan-teal for support, everything else quiet gray until a state needs to speak.

### Primary
- **Watermelon Crimson** (`#d61450`, `primary-600`): The action and identity color. Primary buttons, active bottom-nav and sidebar items, unseen-notification dots, focus outlines, and key timestamps/links. Shades 600+ are darkened so white text on the fill clears AA (≥4.5:1). The light end (`primary-50`–`100`) tints selected/hover backgrounds; `primary-400`–`500` light up active icons in dark mode.

### Secondary
- **Cyan-Teal Rind** (`#0c9fb8`, `secondary-500`): Support accent for secondary emphasis, complementary chips/highlights, and the occasional informational moment. Never competes with primary for the same action; it is the cooler counterweight that keeps the crimson from going one-note.

### Tertiary
- **Festival Green & Yellow** (Tailwind `green-500` `#22c55e`, `yellow-500` `#eab308`): Drawn from the rind and key-art yellow, used only as semantic accents — green for success, yellow for warning/offline/stale notices. Not decoration.

### Neutral
- **Ink** (`#111827`, `gray-900` / white in dark): Headings and high-emphasis text.
- **Muted** (`#6b7280` light / `#9ca3af` dark, `gray-500`/`gray-400`): Body copy, descriptions, idle nav icons, secondary labels.
- **Surface** (`#ffffff` light / `#1f2937` dark, `gray-800`; navbar/sidebar use `gray-900`): Cards, panels, sheets.
- **App Background** (`#f9fafb` light / `#030712` dark, `gray-50`/`gray-950`): The recessed field behind surfaces; one tonal step below surface, never the same value.
- **Border** (`#e5e7eb` light / `#374151` dark, `gray-200`/`gray-700`): Card outlines, dividers, nav top-border. The primary depth tool in place of shadow.

### Named Rules
**The Color-Earns-Its-Place Rule.** Saturated color appears only on action, active state, or semantic state — primary button, current nav item, unseen badge, success/warning/error. Inactive and resting elements stay gray. If a color is decorative, remove it.

**The Two-Layer Rule.** App background and surface are always one tonal step apart (`gray-50` field, `white` surface; `gray-950` field, `gray-800`/`gray-900` surface). Never paint a surface the same value as its background — separation is the depth.

## 3. Typography

**Display Font:** Unbounded Variable (with Inter Variable, then `ui-sans-serif`, `system-ui` fallback)
**Body Font:** Inter Variable (with `ui-sans-serif`, `system-ui` fallback)

Both are self-hosted via Fontsource with Cyrillic subsets — all copy is Russian, so Cyrillic coverage is non-negotiable. Inter carries everything functional: headings, buttons, labels, body, data. Unbounded is the geometric, rounded display face reserved for brand moments (wordmark, hero/section identity) — it supplies the "lively" without the body text ever shouting.

**Character:** A workhorse humanist sans for the task, a distinctive geometric display for identity. The contrast axis is geometric-display vs. humanist-body — a deliberate pairing, not two near-identical sans.

### Hierarchy
- **Display** (Unbounded, 700, ~1.5rem+, line-height 1.15): Brand wordmark and rare identity moments only. Never body, never data.
- **Headline** (Inter, 700, ~1.25rem, line-height 1.25): Page titles (in navbar), error-card titles. `text-xl`/`text-2xl`.
- **Title** (Inter, 600, ~1rem, line-height 1.4): Card headings, notification titles, list-item leads.
- **Body** (Inter, 400, ~0.875rem, line-height 1.6): Descriptions and prose. `text-sm`/`text-base`; cap prose at 65–75ch (the `max-w-5xl` single column already enforces this on phones).
- **Label** (Inter, 600, ~0.75rem, letter-spacing 0.05em, sometimes uppercase): Status pills ("Офлайн", "Ошибка 500"), meta. The *only* place tracked uppercase is allowed.

### Named Rules
**The Inter-For-The-Job Rule.** Unbounded is identity, Inter is interface. Display type never appears in a button, input, table cell, or label. A label set in Unbounded is a bug.

**The Fixed-Scale Rule.** Type sizes are fixed rem steps, not fluid `clamp()`. Users view at consistent phone DPI; a heading that shrinks in a panel looks worse, not designed.

## 4. Elevation

This system is **near-flat by default**. Depth is conveyed by tonal layering (a recessed `gray-50`/`gray-950` background under a `white`/`gray-800` surface) and by 1px borders — not by drop shadows. The result reads calm and modern rather than lifted.

### Shadow Vocabulary
- **Resting list shadow** (`box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05)`, Tailwind `shadow-sm`): The single sanctioned shadow. A whisper under standalone list items (notification cards) to lift them off the field. Nothing heavier ships at rest.
- **Floating overlays** (Flowbite default for dropdowns, toasts, modals): Larger ambient shadow, owned by the component library, reserved for genuinely floating layers above the page.

### Named Rules
**The Border-Before-Shadow Rule.** To separate a surface from its background, reach for a `border-gray-200`/`gray-700` and a tonal step first. A shadow is only justified on something that genuinely floats (overlay) or is a tappable standalone card (`shadow-sm`). No `shadow-md`/`lg`/`xl` on resting content.

## 5. Components

Flowbite-Svelte is the component substrate; these are the project's tuned defaults and the vocabulary every new screen must match.

### Buttons
- **Shape:** Gently rounded, `rounded-xl` (12px) for app actions; `font-medium`.
- **Sizing:** `min-h-11` (44px) minimum — thumb-first tap target, non-negotiable on a phone-first app.
- **Primary:** Watermelon Crimson fill (`primary-600`, `color="primary"`), white text, full-width in stacked action groups. Hover deepens to `primary-700`.
- **Alternative / Light / Ghost:** `color="alternative"` (white/bordered) for the secondary action in a stack; `color="light"` for tertiary ("back"). `color="red"` reserved for destructive confirms.
- **Hover / Focus:** Background shift on hover; visible `focus-visible` outline. Transitions 150–250ms.

### Inputs / Fields
- **Style:** Flowbite `Input`, `rounded-lg` (8px), light border on surface, ~42px height.
- **Focus:** Border shifts to primary with a soft ring (Flowbite default).
- **Error:** `color="red"` — red border + helper text. Never color alone; pair with a message.
- **OTP (signature):** Six individual `h-11 w-11` (44px, `sm:h-12`) center-aligned `text-lg font-extrabold` digit boxes with auto-advance, backspace-back, and paste-to-fill. Error state flips all six to `color="red"`.

### Cards / Containers
- **Corner Style:** `rounded-xl` (12px) standard; `rounded-2xl` (16px) for large feature/error cards.
- **Background:** `white` / `dark:bg-gray-800` surface.
- **Border:** `border-gray-200` / `dark:border-gray-700` — the primary separator.
- **Shadow Strategy:** `shadow-sm` only on standalone tappable list items; otherwise none (see Elevation).
- **Focus (link cards):** a whole-card link (`<a href>`) shows a visible `focus-visible` ring for keyboard users; non-interactive cards have no focus state. Wired once in the central Card theme (root `+layout.svelte`), so it can't be forgotten per card.
- **Defaults are centralized:** the flat, `rounded-xl` surface is the app-wide Card default (Flowbite `ThemeProvider` in the root layout), not something each card re-specifies. Deviate up (`rounded-2xl`, `shadow-sm`) only where noted above.
- **Internal Padding:** `p-4` (16px) mobile, `p-6`–`p-8` desktop.

### Notices (signature)
- **Style:** Full-width `rounded-xl` tinted strip — icon + text. Tinted background, matching border, darker same-hue text (e.g. offline/stale: `bg-yellow-50` + `border-yellow-200` + `text-yellow-800`).
- **Use:** Stale-data, offline, connection banners. Calm and informative, never alarming.

### Navigation
- **Mobile — Bottom Nav:** Fixed, 4 columns, `border-t`, `white`/`gray-900` fill, respects `env(safe-area-inset-bottom)`, `md:hidden`. Active item = solid icon in `primary-600`/`primary-400`; idle = outline icon in `gray-500`/`gray-400` with primary on hover. Active state pairs icon *fill* change with color — never color alone.
- **Desktop — Sidebar + Navbar:** Sidebar (`md:` and up) for primary nav; top navbar carries the current page title and account/notification entry points. Bottom nav is hidden on desktop.

### Empty & Loading States
- **Loading:** Skeletons that mimic the content's shape — never a centered spinner in the content area.
- **Empty:** Teach the interface (what this screen will hold, one action), not "nothing here."
- **Error:** Centered card, role-colored icon chip (red danger / yellow offline), status label, Russian title + plain-spoken description, stacked retry / home / back actions.

## 6. Do's and Don'ts

### Do:
- **Do** keep every primary task one-handed and one-glance: bottom nav on mobile, ≥44px tap targets, a single `max-w-5xl` column.
- **Do** let color earn its place — saturated watermelon only on action, active state, and semantic state; gray at rest.
- **Do** separate surfaces with a border and a tonal step (`gray-50` field under `white` surface) before reaching for any shadow.
- **Do** use Inter for all interface text; reserve Unbounded for the wordmark and rare identity moments.
- **Do** pair every state with text/icon, not color alone (active nav = solid icon + primary; error = red border + message).
- **Do** ship skeletons for loading, teaching empty states, and calm cached/offline notices — resilience is first-class.
- **Do** write all user-facing copy in warm, plain-spoken Russian; keep code comments in English.
- **Do** honor `prefers-reduced-motion` and keep transitions 150–250ms, conveying state only.

### Don't:
- **Don't** go childish or cartoonish — no sticker overload, no comic-book energy, no talking down to teens.
- **Don't** ship the generic AI template: no cream/sand body background, no tiny uppercase tracked eyebrow over every section, no identical icon-card grids, no gradient text.
- **Don't** clutter — no wall of information, no cramming; one primary thing per screen with air around it.
- **Don't** put a drop shadow heavier than `shadow-sm` on resting content; `shadow-md`/`lg`/`xl` are for floating overlays only.
- **Don't** set interface text (buttons, inputs, labels, data) in Unbounded — display type in a label is a bug.
- **Don't** use `border-left`/`border-right` greater than 1px as a colored accent stripe on cards, list items, or notices — use a full tinted notice instead.
- **Don't** convey state by color alone, and never use full-saturation accents on inactive elements.
- **Don't** use fluid `clamp()` heading scales; type sizes are fixed rem steps.
- **Don't** reach for a modal first — exhaust inline and progressive alternatives.
