# ADR-0032: ZXing (WebAssembly) for camera barcode scanning, precached

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Project maintainers

## Context

Attendees link a ticket by its number. A TicketsCloud e-ticket carries that
number three times: a QR code and two Code 128 barcodes, all encoding the same
digits as the printed number (checked against a real ticket). Scanning one
saves typing a 16-digit number. A planned quest game will scan QR codes around
the venue, so the scanner has to be reusable.

The browser-native Barcode Detection API is not enough. Firefox has none, and
Safari ships it disabled by default, iOS included
([caniuse](https://caniuse.com/mdn-api_barcodedetector),
[MDN](https://developer.mozilla.org/en-US/docs/Web/API/Barcode_Detection_API)).
Chromium-based browsers do support it. The scanner runs at the venue, where the
connection is worst, and the app already works offline from its precached shell
(ADR-0020).

## Decision

We decode with [`zxing-wasm`](https://github.com/Sec-ant/zxing-wasm)'s `reader`
build (ZXing-C++ compiled to WebAssembly) **in every browser**, the
Chromium ones with a native detector included. The `.wasm` is imported through
Vite's `?url`, so it is content-hashed under `_app/immutable/`, and
`prepareZXingModule`'s `locateFile` points the library at it instead of its
default jsDelivr URL (`#lib/utils/barcodeReader.ts`). `buildPrecacheManifest`
admits `.wasm`, so the decoder installs with the app shell.

`#lib/components/BarcodeScannerDialog.svelte` is the one camera surface: a
`Dialog` that opens the rear camera, decodes a few frames a second, and hands
the first code of the formats its caller names to `onDetect`.

## Consequences

- One decoder everywhere: a code that scans on one phone scans on all of them,
  and bugs reproduce on any device.
- Every install downloads the decoder, about 0.97 MB raw (`zxing-wasm` 3.1.5;
  about 0.42 MB gzipped as served through Caddy's `encode`), whether or not
  the user ever scans. Because the URL is content-hashed (`revision: null`), a
  deploy re-downloads it only when a `zxing-wasm` bump changes the file.
- Scanning works offline once the app has been opened online. What the caller
  does with the code (linking a ticket) may still need the network.
- Don't move the `.wasm` to `static/`: a fixed URL is revisioned with the build
  version and re-downloaded on every deploy.

## Alternatives considered

- **Native `BarcodeDetector` with a ZXing fallback** (`barcode-detector`
  polyfill): rejected. Two decoders with different quirks, and native support is
  missing exactly where much of our audience is (iOS).
- **Runtime cache on first scan** instead of precaching: rejected. A user who
  never scanned at home would download the decoder at the venue, on the worst
  network of the day.
- **Load the `.wasm` from jsDelivr** (the library default): rejected. A
  third-party CDN at runtime, outside the service worker's precache, and
  unreachable offline.
