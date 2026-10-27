import { prepareZXingModule, readBarcodes, type ReadInputBarcodeFormat } from 'zxing-wasm/reader';
import wasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url';

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

export async function readBarcode(
	frame: ImageData,
	formats: readonly BarcodeFormat[]
): Promise<string | null> {
	const [result] = await readBarcodes(frame, { formats: [...formats], maxNumberOfSymbols: 1 });
	return result?.text ?? null;
}

const MAX_IMAGE_SIDE = 3000;

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
