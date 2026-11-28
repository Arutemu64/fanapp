# Design System: FAN FAN

> **Token values are not defined here.** The source of truth for colors, typography, spacing, radii and component defaults is the code: `frontend/src/app.css` (Tailwind theme + semantic tokens) and the vendored shadcn source in `frontend/src/lib/components/ui/`. This document carries the _why_ — the principles, named rules, and do's/don'ts that the code can't express. When a value below is illustrative (e.g. a hex in a rule), the code wins.

## 1. Overview

**Creative North Star: "The Pocket Convention"**

FAN FAN is the entire anime festival, thumb-first, in seconds. The user is a tired teen between events, one-handed, on flaky con-venue wifi, looking up what's next or casting a vote. The interface gets out of the way: bottom-anchored navigation on phones, a left sidebar on desktop, a single scannable column of content capped at `max-w-5xl`, and generous 44px tap targets everywhere. The tool disappears into the task.

The personality is **clear, lively, calm-under-load**. Vibrance comes from the spring palette — forest-green primary, blossom-pink secondary, pulled straight from the FAN FAN key art — and it is the _only_ flourish. Color does the emotional work in primary actions, active nav, unseen-badges, and state moments; the layout itself stays quiet, near-flat, and uncluttered. Surfaces separate by border and tonal layering, not by drop shadows. Density is low by intent: one primary thing per screen, breathing room around it, so a glance is enough.

This system explicitly rejects three things. It is not **childish or cartoonish** — the audience is young but wants to be taken seriously, so no sticker overload and no comic-book energy. It is not **generic AI slop** — no cream/sand body background, no tiny uppercase tracked eyebrows over every section, no identical icon-card grids, no gradient text. And it is not **cluttered** — no wall of information, no cramming; phone-first means hierarchy and air.

**Key Characteristics:**

- One-handed, one-glance: bottom nav on mobile, sidebar on desktop, single capped column.
- Color carries the joy; structure carries the calm.
- Near-flat surfaces — borders and tonal layering over shadows.
- Resilient by default: skeletons, cached-shell offline boot, calm error and stale states.
- Light and dark mode, WCAG AA, full `prefers-reduced-motion` support.

## 2. Colors

Spring 2027 uses forest green for actions and headings and blossom pink for secondary accents.

### Primary

- **Forest Green** (`#1e5b3a`, `primary-600`): The action and identity color. Primary buttons, active bottom-nav and sidebar items, unseen-notification dots, focus outlines, and key timestamps/links. Shades 600+ are darkened so white text on the fill clears AA (≥4.5:1). The light end (`primary-50`–`100`) tints selected/hover backgrounds; `primary-400`–`500` light up active icons in dark mode.

### Secondary

- **Blossom Pink** (`#c62e5a`, `secondary-600`) adds a small accent to secondary controls and the festival wordmark.

### Tertiary — semantic status

- **Success / Warning / Info** are semantic tokens (`--success`, `--warning`, `--info` in `app.css`), not raw palette classes. Success is green, warning is key-art amber (offline/stale/caution), info is blue-green. Error reuses the existing `--destructive`. Each token doubles as a readable text colour on its own `/10` tint and as a solid fill with its `-foreground`, and flips value between light and dark, so call sites use `text-success` / `bg-warning/10` / `border-info/30` with **no `dark:` override**. Used only as semantic accents on state — success (voted, live, linked), warning (offline/stale/destructive-confirm), info (sync/status) — never as decoration.
- **Medal** tokens (`--medal-gold` / `--medal-silver` / `--medal-bronze`, text in `--medal-foreground`) fill the quest leaderboard's top-three rank pills and nothing else. They are fills, not text colours, and stay the same in both themes, because the metal should look like metal on either surface. A podium place is the state they mark.

### Neutral

- **Ink** and **Muted** use green-tinted neutrals on white. Page titles use forest green.
- **Surface** and **App Background** share white in light mode. In dark mode, cards sit one tonal step above the page.
- **Border** separates cards, rows and the sidebar. The desktop header shows a divider only after scrolling.

### Named Rules

**The Color-Earns-Its-Place Rule.** Saturated color appears only on action, active state, or semantic state — primary button, current nav item, unseen badge, success/warning/error. Inactive and resting elements stay gray. If a color is decorative, remove it.

**Home hero.** Let the photograph fill the rounded card. Apply the dark overlay across the full image so labels remain readable as the crop changes.

## 3. Typography

**Display Font:** Unbounded Variable (with Onest Variable, then `ui-sans-serif`, `system-ui` fallback)
**Body Font:** Onest Variable (with `ui-sans-serif`, `system-ui` fallback)

Both are self-hosted via Fontsource with Cyrillic subsets — all copy is Russian, so Cyrillic coverage is non-negotiable; Onest was drawn Cyrillic-first. Unbounded sets the headings (`text-headline`, `text-section`) and brand moments (wordmark, hero, countdown numerics). Onest carries everything functional: card titles, buttons, labels, body, data.

**Character:** A wide, rounded geometric display for headings, a calm grotesque for the task. The contrast axis is wide-display vs. neutral-body — a deliberate pairing, not two near-identical sans.

### Hierarchy

- **Display** (Unbounded, 700, ~1.5rem+, line-height 1.15): Brand wordmark and rare identity moments only. Never body, never data.
- **Headline** (Unbounded, 600, 1.5rem, line-height 1.375): Page titles and error-card titles. `text-headline` at every width; long titles wrap in full.
- **Section** (Unbounded, 600, 1.125rem, line-height 1.375): Section and card-group headings. `text-section` at every width.
- **Title** (Onest, 600, 1rem, line-height 1.4): Card headings, notification titles, list-item leads.
- **Body** (Onest, 400, 1rem, line-height 1.6): Descriptions and prose. `text-body`; 14px (`text-sm`) is for secondary text only — helper lines, a subtitle under a heading, metadata rows. Cap prose at 65–75ch (the `max-w-5xl` single column already enforces this on phones).
- **Label** (Onest, 600, ~0.75rem, letter-spacing 0.05em, sometimes uppercase): Status pills ("Офлайн", "Ошибка 500"), meta. The _only_ place tracked uppercase is allowed.

### Named Rules

**The Onest-For-The-Job Rule.** Unbounded is headings and identity, Onest is interface. Display type never appears in a button, input, table cell, label, or a card's own title — Unbounded is wide, and in a list row it eats the line. A label set in Unbounded is a bug. Unbounded runs at 600, a step under the 700 a grotesque would take: its strokes are heavy for their number.

**The Read-Versus-Scan Rule.** The face follows the type role, as in Material 3: its expressive _brand_ face sets Display, Headline and Title Large, and its neutral _plain_ face sets the smaller titles, body and labels ([Material 3 type-scale tokens](https://github.com/androidx/androidx/blob/androidx-main/compose/material3/material3/src/commonMain/kotlin/androidx/compose/material3/tokens/TypeScaleTokens.kt)). Unbounded is our brand face, Onest our plain one. Which role a group heading takes is our own call, made by how the page is used. On a page read top to bottom once — the guide, Home's sections — a group is a real section: `text-section` in Unbounded, set like a magazine, each head over three times nearer its list than the block above it ([Practical Typography, Space above and below](https://practicaltypography.com/space-above-and-below.html)). On a page scanned and tapped through — a feed, settings groups, notification day labels («Сегодня», «Вчера») — it is a label: a quiet `text-sm` Onest caption in `muted-foreground`, since it repeats down the list and a display head on every repeat is noise that pushes rows off the screen. The page title is Unbounded either way.

**The Fixed-Scale Rule.** Type sizes are fixed rem steps, not fluid `clamp()`, and they don't step down on phones (no `text-sm sm:text-base`). Users view at consistent phone DPI and read here on a phone; a heading that shrinks in a panel looks worse, not designed.

## 4. Elevation

Card outlines and spacing give white surfaces their edges. Dark surfaces also use tonal layering.

### Shadow Vocabulary

- **Resting card surface** (`shadow-xs` + a `ring-1 ring-foreground/10` hairline, set once in `card.svelte`): the near-flat default for every `Card`. The hairline ring does the separating — it _is_ the border in the two-layer scheme — and the `shadow-xs` is barely-there. This is the vendored default; don't add a heavier shadow to a resting card.
- **Resting list shadow** (`shadow-sm`): a slightly stronger whisper reserved for standalone tappable list items (e.g. notification cards) to lift them off the field. Nothing heavier ships at rest.
- **Floating overlays** (dropdowns, toasts, dialogs): Larger ambient shadow, owned by the shadcn component, reserved for genuinely floating layers above the page.
- **Floating bottom nav** (`shadow-lg shadow-black/5`): the pill genuinely floats over scrolling content, so it earns a soft, low-opacity ambient shadow — large radius, near-zero alpha, never a dark drop.

### Named Rules

**The Border-Before-Shadow Rule.** To separate a surface from its background, reach for a border (or the `Card`'s hairline `ring`) and a tonal step first. A shadow beyond the resting `shadow-xs`/`shadow-sm` is only justified on something that genuinely floats (overlay). No `shadow-md`/`lg`/`xl` on resting content.

## 5. Components

shadcn-svelte (vendored as source in `#lib/components/ui/`) is the component substrate; these are the project's tuned defaults and the vocabulary every new screen must match. The semantic `--primary` is wired to the **forest-green brand** in `app.css` (`--color-primary-600` in light, the lighter `-400` in dark), so `bg-primary` / `text-primary` — the default `<Button>`, links, active nav, checked controls, `primary/10` accent tiles — all render on-brand. `--primary-foreground` is white in light / dark in dark so text clears AA on the fill either way.

### Buttons

- **Shape:** A pill that squares off to a 10px corner while pressed — the [Material 3 Expressive](https://m3.material.io/components/buttons/overview) round button and its press morph. Set once in `button.svelte`; don't add a radius at the call site. Labels stay Onest 14px / 500 (M3 Label Large), with 16px side padding and an 8px icon–label gap (24px past 56px tall); the morph replaces upstream's 1px press nudge.
- **Sizing:** The base already meets the thumb-first 44px tap target (default/icon 44px, sm 40px, lg 48px; `xs` 24px is a dense desktop-only opt-in), so a plain `<Button>` needs no `min-h-11`. Non-negotiable on a phone-first app — set in `button.svelte`'s `tv()` base, one rung above upstream shadcn.
- **Primary:** the default `<Button>` (`variant="default"`) — forest-green fill via the semantic `--primary`, full-width in stacked action groups.
- **Secondary / Ghost / Destructive:** `variant="outline"` (bordered) for the secondary action in a stack; `variant="ghost"` for tertiary ("back"); `variant="destructive"` reserved for destructive confirms.
- **Tonal (repeated actions):** `variant="tonal"` — a brand-tinted fill for an action that repeats down a list (the per-participant «Голосовать»). A column of solid fills would bury the page's one primary action, and a labelled button beats an icon here: no icon reads as "vote" on its own ([NN/g, Icon Usability](https://www.nngroup.com/articles/icon-usability/)).
- **Floating (over scrolling content):** `variant="floating"` — the bottom-nav pill's glass (`background/85` + blur, opaque under reduce-transparency) for a button that hovers over the page, like the schedule's current-event bar. The schedule bar stays visible whenever an act is current and shares the mobile dock’s width. On desktop it sits near the bottom of the schedule column, with a wider title area. It shows a live dot, title, stage status, and a locate icon that jumps to the current act. The dot pulses once when the schedule opens and once when a new act goes live. With reduced motion, the dot stays steady. An overflowing title scrolls once for 4.8 seconds. With reduced motion or large text, the title wraps. `outline` is near-transparent in dark mode, so content would read through a floating outline button.
- **Hover / Press / Focus:** Background shift on hover, and the same shift on press so a finger gets the feedback a mouse does; visible `focus-visible` outline. Transitions 150–250ms.

### Inputs / Fields

- **Style:** shadcn `Input`, `--radius`-derived corners, light border on surface. Lay fields out with `Field.FieldGroup` + `Field.Field` (`FieldLabel`, control, `FieldError`/`FieldDescription`), not raw `div` + `Label`.
- **Focus:** Border + ring shift to the ring token (shadcn default).
- **Error:** `data-invalid` on the `Field` + `aria-invalid` on the control → destructive border and `FieldError` text. Never colour alone; pair with a message.
- **OTP (signature):** `InputOTP` presents one input as six centered, bold digit boxes. They share the available width and keep the `h-11` (`sm:h-12`) input height as text scales. The input supports auto-advance, backspace, and paste. Error state sets `aria-invalid`.

### Cards / Containers

- **When to use a card:** a card frames one item among several — a list entry with its own actions (event, nomination, participant, schedule change), or one headed section of a page that has several (the organizer voting/settings/user pages). The login and error screens, a lone centred panel on an otherwise empty screen, are the other exception.
- **When not to:** never wrap a whole single-task page in a card — a form page (feedback, broadcast, ticket generation) or a settings page. The frame groups nothing, and on a phone it spends 32–48px of width on padding. Put the form straight on the page in the `max-w-2xl` column; put settings rows in `MenuGroup` grouped lists with a plain heading above (`SettingsSection`), the same shape as the `/profile` hub. Start from whitespace and add a boundary only where the grouping is otherwise unclear ([NN/g, Common Region](https://www.nngroup.com/articles/common-region/)); prefer a list to a stack of cards for same-shaped items ([NN/g, Cards](https://www.nngroup.com/articles/cards-component/)) — the organizer toolbox, the feedback feed and the broadcast history are each one `MenuGroup` of rows.
- **No boxes in boxes:** a card or `MenuGroup` holds rows separated by hairline dividers, never further bordered or tinted boxes.
- **Corner Style:** `rounded-2xl` (18px), set in `card.svelte`, and the same on card-shaped surfaces built by hand (`MenuGroup`, home cards). It sits between Material 3's Large (16dp) and Large Increased (20dp) shapes — rounder than M3's 12dp card default, to sit with the pill buttons. Content inside a card's 16–24px padding is its own surface: it keeps its own radius rather than a concentric one, which at that inset would round to zero.
- **Background:** `white` / `dark:bg-gray-800` surface.
- **Border:** `border-gray-200` / `dark:border-gray-700` — the primary separator.
- **Shadow Strategy:** `shadow-sm` only on standalone tappable list items; otherwise none (see Elevation).
- **Focus (clickable cards):** a clickable card uses a stretched-link overlay (an `<a href>` whose `::after` covers the card), never a whole-card anchor; the link shows a visible `focus-visible` ring for keyboard users. Non-interactive cards have no focus state.
- **Defaults live in the component source:** the flat Card surface is set once in `card.svelte` (the vendored shadcn source), not re-specified per card. Deviate up (`shadow-sm`) only where noted above.
- **Internal Padding:** `p-4` (16px) mobile, `p-6`–`p-8` desktop.

### Notices (signature)

- **Style:** Full-width `rounded-xl` tinted strip — icon + text, built from a status token (e.g. offline/stale: `bg-warning/10` + `border-warning/30` + `text-warning`; success/info follow the same shape).
- **Use:** Stale-data, offline, connection banners. Calm and informative, never alarming.

### Navigation

- **Mobile — Bottom Nav:** A floating glass pill with five links with 24px icons and visible 12px labels in a `rounded-full` capsule capped at `max-w-md`, inset from the screen edges and above the home indicator. The active icon and semibold label use `primary-800` in light mode and `primary-300` in dark mode. A `primary/12` fill (`/20` in dark mode) encloses the active icon and label. The capsule leaves room around the label and slides between tabs in 300ms, with instant movement under reduced motion. The bar uses `background/85` and 16px blur, with an opaque surface under reduced transparency. Floating controls offset from `--bottom-nav-clearance` in `app.css`.
- **Desktop — Sidebar + Navbar:** At `md:` and up, the primary links sit in a compact 104px dock inset from the top and left edges. The dock stays in place during page scroll, and its links scroll within it on short viewports. The sidebar uses an opaque card surface with an 18px radius, an inset outline, and an 8px gutter on the content side. Each 24px icon sits above a 12px label. The active and hover fills have 10px corners. The active highlight slides in 300ms and moves instantly under reduced motion. The sticky navbar carries the tab title and notification bell. Its desktop divider appears once content scrolls beneath it. The desktop connection notice sits below the navbar and aligns with the content column. On nested pages, the title starts the scrolling content and a leading back arrow appears in the navbar on phones and desktops.

### Icons

- **Set:** Lucide (`@lucide/svelte`), the library the vendored shadcn-svelte components already import, so app icons and component chrome share one stroke weight and corner style. It is chosen for consistency, not character: identity comes from the forest-green colour and Unbounded, and icons stay quiet next to them.
- **Use:** an icon earns its place by naming its content (calendar for Программа, map pin for Карта). A labelled button beats a lone icon when no glyph reads unambiguously (see Tonal buttons).

### Empty & Loading States

- **Loading:** Skeletons that mimic the content's shape — never a centered spinner in the content area.
- **Empty:** Teach the interface (what this screen will hold, one action), not "nothing here."
- **Error:** Centered card, role-colored icon chip (red danger / yellow offline), status label, Russian title + plain-spoken description, stacked retry / home / back actions.

## 6. Do's and Don'ts

### Do:

- **Do** keep every primary task one-handed and one-glance: bottom nav on mobile, ≥44px tap targets, a single `max-w-5xl` column.
- **Do** treat a wide screen as a rearrangement of the phone layout, never a second design: at `lg`/`xl` a page may put the same components side by side (Home's supporting column, the map's plan beside its list, the voting grid), but it never shows content, controls or navigation that phones don't get. Extra panes come only where the width earns them, Material 3's canonical layouts at expanded widths and up ([Android, window size classes](https://developer.android.com/develop/ui/compose/layouts/adaptive/window-size-classes)). Behaviour that must switch with the bottom nav ↔ sidebar swap matches `DESKTOP_MEDIA_QUERY` (`#lib/constants/layout`, kept equal to `--breakpoint-md` in `app.css` by a unit test), never a hardcoded width.
- **Do** let color earn its place — saturated forest green only on action, active state, and semantic state; gray at rest.
- **Do** separate surfaces with a subtle border before reaching for any shadow.
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
- **Don't** set interface text (buttons, inputs, labels, data, card titles) in Unbounded — display type in a label is a bug.
- **Don't** use `border-left`/`border-right` greater than 1px as a colored accent stripe on cards, list items, or notices — use a full tinted notice instead.
- **Don't** convey state by color alone, and never use full-saturation accents on inactive elements.
- **Don't** use fluid `clamp()` heading scales; type sizes are fixed rem steps.
- **Don't** reach for a modal first — exhaust inline and progressive alternatives.

## 7. antislop overrides

The antislop rulebook (`.agents/skills/antislop/`) is the slop filter; this file is the direction. Where they collide, the direction wins and the reason is recorded here (antislop R-37).

- **Em dash (R-02).** Kept. In Russian the тире is grammatical, not a style tic. It marks an omitted copula between subject and nominal predicate and joins clauses of a conjunctionless sentence ([Правила русской орфографии и пунктуации, §164–172](https://www.azbyka.ru/otechnik/Spravochniki/pravila-russkoj-orfografii-i-punktuatsii/42)). A comma or colon would change the grammar. Copy keeps the `\u00A0—` binding from `fanfan-russian-copy`, and event titles of the form «Персонаж — Фэндом» are data.
- **Fluid type (antislop-layoutmobile).** Rejected for the Fixed-Scale Rule (§3). A `clamp()` with viewport units can stop text reaching 200% under zoom, which fails WCAG 1.4.4 ([Adrian Roselli, Responsive Type and Zoom](https://adrianroselli.com/2019/12/responsive-type-and-zoom.html); [Smashing Magazine, Addressing Accessibility Concerns With Using Fluid Type](https://www.smashingmagazine.com/2023/11/addressing-accessibility-concerns-fluid-type/)).
- **Tracked uppercase (R-06).** Allowed on labels and status pills only (§3 Label), which includes the hero's phase label («До начала фестиваля», «Сейчас на сцене»). Section headings stay sentence case.
- **Live dot (R-19).** The dot marks a real state. Its ping runs three times and stops (`--animate-ping-brief` in `app.css`), because WCAG 2.2.2 requires auto-started motion beside other content to stop within 5s ([W3C, Understanding 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide)).
- **Glass (R-10).** Reserved for surfaces that float over scrolling content: the bottom nav and the `floating` button variant. Dialog overlays keep shadcn's faint blur.
