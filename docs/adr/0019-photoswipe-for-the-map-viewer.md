# ADR-0019: PhotoSwipe for the map viewer

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Project maintainers

## Context

The map page opens each venue floor plan full-screen so visitors can find a
stand or a toilet on their phone mid-festival. The viewer was hand-rolled around
`@panzoom/panzoom`, and on phones it felt nothing like a native photo viewer:

- a pan stopped dead on release, with no momentum, and nothing kept the map on
  screen, so a flick could lose it entirely;
- the viewer had no history entry, so the Android/iOS back gesture left the map
  page instead of closing the map;
- pinch only worked if it started on the image, and double-tap reset rather than
  zoomed, so a touch user had no single-pointer way to zoom in (WCAG 2.5.1);
- the viewer reused the thumbnail's `sizes`, so zooming upscaled a ~1366 px
  variant of a 2835 px map and blurred its labels.

Panzoom can be patched for the last three but has no inertia or edge resistance,
which is most of what "natural" means for touch.

## Decision

We will use **PhotoSwipe v5** (`photoswipe`, pinned exactly, no dependencies)
for the map viewer in `frontend/src/routes/(app)/map/+page.svelte`.

- The core `PhotoSwipe` class is opened programmatically from SvelteKit page
  state (`pushState('', { mapViewerIndex })`, typed in `App.PageState`), so back
  closes the viewer and the viewer's own close controls drop the entry.
- Slides take the `<enhanced:img>` WebP `srcset`; PhotoSwipe raises `sizes` as
  the user zooms, so wider variants up to the original load on demand.
- UI strings, ARIA role descriptions and a download button are set in the page;
  the root z-index is mapped onto the app's `--z-modal` rung.

## Consequences

- Momentum pan, bounded panning with edge resistance, double-tap zoom to a
  point, swipe and pinch to close, swiping between maps and a zoom animation
  from the thumbnail come from the library instead of from our code.
- About 17 kB gzipped of JS plus its CSS, loaded only with the map route chunk.
- PhotoSwipe releases rarely (5.4.4, May 2024). It uses only standard DOM APIs,
  so it is unlikely to break on its own; updates arrive through Renovate like
  any other dependency and are reviewed as a diff.
- PhotoSwipe ignores `close()` until its opening animation ends; the page defers
  a close requested that early (see `closeViewer`). Keep that if the wiring
  changes.

## Alternatives considered

- **Keep `@panzoom/panzoom` and patch it** — fixes history, gesture area and
  resolution, but leaves panning without inertia or bounds.
- **`@zoom-image/svelte`** — headless and actively released, but only the zoom
  primitive: gestures, bounds, the overlay and close gestures would all be ours
  to build.
- **`svelte-zoom`** — unmaintained since 2022.
- **OpenSeadragon** — deep-zoom tiles are overkill for two static floor plans.
