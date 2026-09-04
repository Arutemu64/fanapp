# Design System: FAN FAN

> **Token values are not defined here.** The source of truth for colors, typography, spacing, radii and component defaults is the code: `frontend/src/app.css` (Tailwind theme + semantic tokens) and the vendored shadcn source in `frontend/src/lib/components/ui/`. This document carries the *why* — the principles, named rules, and do's/don'ts that the code can't express. When a value below is illustrative (e.g. a hex in a rule), the code wins.

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

### Tertiary — semantic status
- **Success / Warning / Info** are semantic tokens (`--success`, `--warning`, `--info` in `app.css`), not raw palette classes. Success is festival green (from the rind), warning is key-art amber (offline/stale/caution), info is the cyan-teal secondary hue (DESIGN's "occasional informational moment"). Error reuses the existing `--destructive`. Each token doubles as a readable text colour on its own `/10` tint and as a solid fill with its `-foreground`, and flips value between light and dark, so call sites use `text-success` / `bg-warning/10` / `border-info/30` with **no `dark:` override**. Used only as semantic accents on state — success (voted, live, linked), warning (offline/stale/destructive-confirm), info (sync/status) — never as decoration.

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
- **Resting card surface** (`shadow-xs` + a `ring-1 ring-foreground/10` hairline, set once in `card.svelte`): the near-flat default for every `Card`. The hairline ring does the separating — it *is* the border in the two-layer scheme — and the `shadow-xs` is barely-there. This is the vendored default; don't add a heavier shadow to a resting card.
- **Resting list shadow** (`shadow-sm`): a slightly stronger whisper reserved for standalone tappable list items (e.g. notification cards) to lift them off the field. Nothing heavier ships at rest.
- **Floating overlays** (dropdowns, toasts, dialogs): Larger ambient shadow, owned by the shadcn component, reserved for genuinely floating layers above the page.

### Named Rules
**The Border-Before-Shadow Rule.** To separate a surface from its background, reach for a border (or the `Card`'s hairline `ring`) and a tonal step first. A shadow beyond the resting `shadow-xs`/`shadow-sm` is only justified on something that genuinely floats (overlay). No `shadow-md`/`lg`/`xl` on resting content.

## 5. Components

shadcn-svelte (vendored as source in `$lib/components/ui/`) is the component substrate; these are the project's tuned defaults and the vocabulary every new screen must match. The semantic `--primary` is wired to the **watermelon brand** in `app.css` (`--color-primary-600` in light, the lighter `-400` in dark), so `bg-primary` / `text-primary` — the default `<Button>`, links, active nav, checked controls, `primary/10` accent tiles — all render on-brand. `--primary-foreground` is white in light / dark in dark so text clears AA on the fill either way.

### Buttons
- **Shape:** The vendored `<Button>` carries its own `--radius`-derived corner (`rounded-md`) and `font-medium` — leave it; don't force a radius tier onto it.
- **Sizing:** The base already meets the thumb-first 44px tap target (default/icon 44px, sm 40px, lg 48px; `xs` 24px is a dense desktop-only opt-in), so a plain `<Button>` needs no `min-h-11`. Non-negotiable on a phone-first app — set in `button.svelte`'s `tv()` base, one rung above upstream shadcn.
- **Primary:** the default `<Button>` (`variant="default"`) — watermelon fill via the semantic `--primary`, full-width in stacked action groups.
- **Secondary / Ghost / Destructive:** `variant="outline"` (bordered) for the secondary action in a stack; `variant="ghost"` for tertiary ("back"); `variant="destructive"` reserved for destructive confirms.
- **Hover / Focus:** Background shift on hover; visible `focus-visible` outline. Transitions 150–250ms.

### Inputs / Fields
- **Style:** shadcn `Input`, `--radius`-derived corners, light border on surface. Lay fields out with `Field.FieldGroup` + `Field.Field` (`FieldLabel`, control, `FieldError`/`FieldDescription`), not raw `div` + `Label`.
- **Focus:** Border + ring shift to the ring token (shadcn default).
- **Error:** `data-invalid` on the `Field` + `aria-invalid` on the control → destructive border and `FieldError` text. Never colour alone; pair with a message.
- **OTP (signature):** `InputOTP` — six individual `h-11 w-11` (44px, `sm:h-12`) center-aligned `text-lg font-bold` digit boxes with auto-advance, backspace-back, and paste-to-fill. Error state sets `aria-invalid`.

### Cards / Containers
- **Corner Style:** `rounded-xl` (12px) standard; `rounded-2xl` (16px) for large feature/error cards.
- **Background:** `white` / `dark:bg-gray-800` surface.
- **Border:** `border-gray-200` / `dark:border-gray-700` — the primary separator.
- **Shadow Strategy:** `shadow-sm` only on standalone tappable list items; otherwise none (see Elevation).
- **Focus (clickable cards):** a clickable card uses a stretched-link overlay (an `<a href>` whose `::after` covers the card), never a whole-card anchor; the link shows a visible `focus-visible` ring for keyboard users. Non-interactive cards have no focus state.
- **Defaults live in the component source:** the flat Card surface is set once in `card.svelte` (the vendored shadcn source), not re-specified per card. Deviate up (`rounded-2xl`, `shadow-sm`) only where noted above.
- **Internal Padding:** `p-4` (16px) mobile, `p-6`–`p-8` desktop.

### Notices (signature)
- **Style:** Full-width `rounded-xl` tinted strip — icon + text, built from a status token (e.g. offline/stale: `bg-warning/10` + `border-warning/30` + `text-warning`; success/info follow the same shape).
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
