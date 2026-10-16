# ADR-0036: uqr for drawing QR codes

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Project maintainers

## Context

A quest player shows a QR code from their profile, and a volunteer scans it
with the existing scanner ([ADR-0032](0032-zxing-wasm-for-camera-scanning.md)).
The code has to appear instantly and offline, often on the venue's bad Wi-Fi.

The app already ships `zxing-wasm`, but only its reader. The writer is a
separate WebAssembly binary: 632 KiB on disk in 3.1.5, next to the reader's
944 KiB. The README lists the writer subpath at about 636 KiB
([zxing-wasm README](https://cdn.jsdelivr.net/npm/zxing-wasm@3.1.3/README.md)).

## Decision

We will draw QR codes with [`uqr`](https://github.com/unjs/uqr), pinned
exactly. We use only its `encode()` to get the module matrix, and
`#lib/utils/qrPath.ts` turns that into a single SVG path. `QrCode.svelte`
renders the path as plain markup, so no `{@html}` is needed. The code uses
error correction level M and a four-module quiet zone. It is always drawn dark
on white, because scanners read light-on-dark codes poorly.

## Consequences

- About 4.3 KB gzipped, with no dependencies
  ([DepScope](https://depscope.dev/pkg/npm/uqr)). It is bundled into the JS, so
  nothing new is precached and the code renders synchronously offline.
- The library is still at 0.1.x. The QR encoding standard does not change, and
  the encoder is a port of Nayuki's QR-Code-generator
  ([uqr README](https://github.com/unjs/uqr)), so the risk is low. If it is
  abandoned, any matrix encoder can replace it behind `qrPath`.
- Reading and writing use different libraries. They meet only at the QR
  standard, so that costs nothing.

## Alternatives considered

- **`zxing-wasm/writer`.** It would mean a second wasm download for every
  player and another precache entry, plus async initialisation before the code
  can render. All that for a one-way encode that needs none of ZXing's breadth.
- **`uqr`'s `renderSVG()`.** It returns an SVG string that would need
  `{@html}`. Building the path from `encode()` keeps the markup in Svelte.
