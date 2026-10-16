import { prepareZXingModule, readBarcodes, type ReadInputBarcodeFormat } from 'zxing-wasm/reader';
import wasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url';

// ZXing decodes in every browser, including the Chromium ones that ship a native
// BarcodeDetector: one decoder means one set of quirks, so a code that scans on
// one phone scans on all of them.
//
// The library fetches its .wasm from jsDelivr by default. Serving it from our own
// build instead puts it under `_app/immutable/` with a content hash, so the
// service worker precaches it with the app shell (precacheManifest.ts): a phone
// that opened the app at home scans at the venue without a connection, and a
// deploy re-downloads the decoder only when the file itself changes.
prepareZXingModule({
	overrides: {
		locateFile: (path: string, prefix: string) => {
			if (path.endsWith('.wasm')) {
				return wasmUrl;
			}
			return prefix + path;
		}
	}
});

export type BarcodeFormat = ReadInputBarcodeFormat;

/** The text of the first code of one of `formats` found in the frame, or `null`. */
export async function readBarcode(
	frame: ImageData,
	formats: readonly BarcodeFormat[]
): Promise<string | null> {
	const [result] = await readBarcodes(frame, {
		formats: [...formats],
		maxNumberOfSymbols: 1,
		tryHarder: true
	});
	return result?.text ?? null;
}
