# ADR-0029: Inline SVG floor plans instead of poster images

- **Status:** Accepted
- **Date:** 2026-10-15
- **Deciders:** Project maintainers

## Context

The map page showed the festival's two printed posters (2835×4252 PNGs) as
cropped thumbnails that opened in a PhotoSwipe viewer
([ADR-0019](0019-photoswipe-for-the-map-viewer.md)). A visitor looking for one
place had to read the number off a text legend, open the viewer, pinch-zoom and
hunt for that number on the poster. The posters also carry what only makes
sense on a printed sign: a title, a legend in tiny type and a «Я тут» marker
fixed to where the sign stood.

## Decision

We will draw each floor as **inline SVG built from data** in
`frontend/src/lib/data/maps.ts`: walls, stairs and wells as decoration, and
numbered zones as tappable rectangles, traced from the posters in their
900×1350 preview's coordinates.

- Tapping a zone or a legend row selects that place: every zone with its
  number (stairs and photo zones appear more than once) is highlighted, the
  rest dim, and a `role="status"` line under the plan names it.
- The SVG is one `role="img"` with an accessible name. The legend rows are
  `aria-pressed` buttons and are the keyboard and screen-reader path to the
  same selection, so the zones stay pointer-only rather than doubling every
  tab stop. A text alternative beside an interactive map is the documented
  pattern for this ([BOIA](https://www.boia.org/blog/interactive-maps-and-accessibility-4-tips),
  [ApexMaps accessibility](https://apexcharts.com/apexmaps/docs/accessibility/)).
- Colours come from the theme tokens, so the plan follows light and dark mode.

## Consequences

- The PNGs (and their AVIF/WebP build variants) and the `photoswipe`
  dependency are gone; the plans are a few kB of route JS and render crisp at
  any width without a zoom viewer.
- The map is no longer downloadable as a file; the browser's own zoom still
  works on the page.
- A new or changed venue layout means re-tracing coordinates by hand instead of
  dropping in a new poster. Acceptable: the venue changes rarely, and the
  traced geometry is small and reviewable as a diff.
- The `--z-modal` z-index rung existed only for the viewer and is removed.

## Alternatives considered

- **Keep the posters and overlay hotspots** — still ships multi-megabyte
  images and the poster's sign-only furniture, and the hotspot positions would
  be tied to one raster.
- **A pan/zoom library over the SVG** (`panzoom`, `svg-pan-zoom`) — not needed
  once the plan is legible at phone width; it would bring back a dependency and
  gesture conflicts with page scroll.
