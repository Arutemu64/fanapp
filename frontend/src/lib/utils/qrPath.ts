import { encode } from 'uqr';

export interface QrPath {
	/** Width and height in modules, quiet zone included. */
	size: number;
	/** One SVG path drawing every dark module as a 1×1 square. */
	d: string;
}

// ISO/IEC 18004 asks for a quiet zone four modules wide; phone scanners lose
// codes that sit flush against other content.
const QUIET_ZONE = 4;

/** An SVG path for `text` as a QR code, so it renders without {@html}. */
export function qrPath(text: string): QrPath {
	// M recovers ~15% damage: enough for a glare-washed phone screen held up
	// to another phone, while keeping a short code at the smallest version.
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
