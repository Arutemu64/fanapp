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
	// Formats narrow the search; one symbol lets ZXing stop at the first hit
	// (its default is 255). tryHarder, tryRotate and tryInvert already default on.
	const [result] = await readBarcodes(frame, { formats: [...formats], maxNumberOfSymbols: 1 });
	return result?.text ?? null;
}

// A full-resolution phone photo is ~12 MP, 48 MB of RGBA once copied into the
// decoder's memory. A screenshot's code survives this cap with room to spare.
const MAX_IMAGE_SIDE = 3000;

/**
 * Like `readBarcode`, for a picked image file. The browser decodes the file:
 * ZXing's own loader reads only PNG and JPEG, and an iPhone photo can be HEIC.
 * Rejects when the browser can't open the file as an image.
 */
export async function readBarcodeFromImage(
	file: Blob,
	formats: readonly BarcodeFormat[]
): Promise<string | null> {
	const bitmap = await createImageBitmap(file);
	const scale = Math.min(1, MAX_IMAGE_SIDE / Math.max(bitmap.width, bitmap.height));
	const width = Math.round(bitmap.width * scale);
	const height = Math.round(bitmap.height * scale);
	const canvas = document.createElement('canvas');
	canvas.width = width;
	canvas.height = height;
	const context = canvas.getContext('2d');
	if (context === null) {
		bitmap.close();
		throw new Error('Canvas 2D context unavailable');
	}
	context.drawImage(bitmap, 0, 0, width, height);
	bitmap.close();
	return readBarcode(context.getImageData(0, 0, width, height), formats);
}
