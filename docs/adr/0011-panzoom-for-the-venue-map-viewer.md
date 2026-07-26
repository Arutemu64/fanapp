# ADR-0011: `@panzoom/panzoom` for the venue-map viewer

- **Status:** Accepted
- **Date:** 2026-07-26
- **Deciders:** Project maintainers

## Context

`/map` ships the venue floor plans as 1280px JPEGs. On a phone the fitted map is
roughly 390px wide, so the numbered legend is only readable zoomed in — the
screen is useless without pinch-to-zoom. The previous viewer was a plain
fullscreen overlay with no zoom at all.

Pinch-zoom is the kind of thing that looks like twenty lines and is not: a
correct implementation needs two-pointer tracking, focal-point anchoring so the
map grows around the fingers rather than the centre, `ctrl`+wheel for trackpad
pinch, Safari's non-standard gesture events, and bounds so the image cannot be
flung off-screen. Frontend guidance says to prefer Flowbite-Svelte components,
but Flowbite has no image viewer or lightbox.

Bundle size matters here beyond the usual: the app is a PWA for a convention
venue, where wifi is saturated and mobile data is patchy.

## Decision

We will depend on **`@panzoom/panzoom`** (MIT, zero runtime dependencies, ~4kB
gzipped) for the gesture mathematics only, and keep the viewer's shell in Svelte:
`routes/(app)/map/components/MapViewer.svelte` owns a native `<dialog>` opened
with `showModal()`, the chrome, and the Russian copy.

Concretely:

- The library is wired through an `{@attach}` attachment on the `<img>`, so its
  lifecycle is the element's and `destroy()` runs on teardown.
- Panzoom's own `contain` option is **not** used. For an image fitted to the
  viewport, `contain: 'outside'` raises `minScale` until the map covers the
  screen — cropping a landscape map on a portrait phone — and `contain: 'inside'`
  caps `maxScale` at the fit scale, disabling zoom entirely. The component
  clamps pan itself at gesture end instead, which also gives the overshoot and
  spring-back that native photo viewers have.
- `maxScale` is measured from the file: the ceiling is the image's own pixel
  density against its fitted size, so a phone zooms to native resolution and
  stops rather than magnifying JPEG artefacts.
- The viewer uses a native `<dialog>` rather than Flowbite's `<Modal>` — see the
  carve-out recorded in [frontend.md](../frontend.md) §7.

## Consequences

- Pinch, drag, double-tap, wheel and the on-screen zoom controls all share one
  well-tested implementation instead of hand-rolled pointer code.
- Two library behaviours are load-bearing and must not be "simplified" away.
  Both are commented at their call sites, and both were found by driving the
  real browser, not by reading the docs:
  - Panzoom's default `handleStartEvent` calls `stopPropagation()` on
    `pointerdown`, and Svelte **delegates** pointer events to the app root — so
    the double-tap handlers must be bound on the element itself, not as
    `onpointerdown`/`onpointerup` attributes.
  - `panOnlyWhenZoomed` makes `pan()` a no-op at fit scale, so the bounds clamp
    passes `force: true`; without it the map stays off-centre after pinching
    back to 1×.
- Upstream is maintained but unhurried (4.6.2, April 2026). It is small,
  dependency-free and pinned in `pnpm-lock.yaml`, and it is confined to this one
  component, so a fork or replacement stays a single-file change.
- Renovate covers it with the rest of the frontend dependencies.

## Alternatives considered

- **PhotoSwipe** — the obvious "batteries included" pick, and it would have given
  bounds clamping, swipe-to-close and gallery swiping for free. Rejected: ~18kB
  gzipped of JS+CSS and a whole imperative DOM lifecycle to manage two static
  images, no release since May 2024, and its slide/gallery model is a poor fit
  for two unrelated floor plans that we label rather than swipe between.
- **Hand-rolled pointer handling** — rejected: this is the code most likely to be
  subtly wrong on one browser and never noticed, and it is not where this
  project's effort belongs.
- **Rely on the browser's native pinch-zoom** (no viewer, no dependency) —
  rejected: it zooms the whole page including the app chrome, pans via the visual
  viewport, and behaves inconsistently in an installed standalone PWA.
- **CSS-only zoom in a scroll container** (`overflow: auto` plus a scaled image)
  — genuinely attractive, since scroll panning is momentum-scrolled and bounded
  for free. Rejected because it still leaves the pinch *gesture* to write by
  hand, which is the expensive half.
