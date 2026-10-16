/**
 * A UUIDv7 (RFC 9562 §5.7): a 48-bit Unix-millisecond timestamp, then random
 * bits, so IDs the client generates sort by time like the server's `uuid7()`.
 *
 * Hand-rolled rather than a dependency: `crypto.randomUUID()` only makes v4,
 * and the layout below is the whole algorithm.
 */
export function uuidv7(now: number = Date.now()): string {
	const timestamp = now.toString(16).padStart(12, '0');
	const random = Array.from(crypto.getRandomValues(new Uint8Array(10)), (byte) =>
		byte.toString(16).padStart(2, '0')
	).join('');

	// The variant nibble keeps two random bits under its fixed `0b10` prefix.
	const variant = ((Number.parseInt(random.slice(3, 4), 16) & 0x3) | 0x8).toString(16);

	return [
		timestamp.slice(0, 8),
		timestamp.slice(8, 12),
		`7${random.slice(0, 3)}`,
		`${variant}${random.slice(4, 7)}`,
		random.slice(7, 19)
	].join('-');
}
