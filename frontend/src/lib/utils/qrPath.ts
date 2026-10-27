import { encode } from 'uqr';

export interface QrPath {
	size: number;
	d: string;
}

const QUIET_ZONE = 4;

export function qrPath(text: string): QrPath {
	const qr = encode(text, { ecc: 'M', border: QUIET_ZONE });
	const segments: string[] = [];
	qr.data.forEach((row, y) => {
		row.forEach((dark, x) => {
			if (dark) {
				segments.push(`M${x} ${y}h1v1h-1z`);
			}
		});
	});
	return { size: qr.size, d: segments.join('') };
}
