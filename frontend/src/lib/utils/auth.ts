export const LOGIN_NEXT_PARAM = 'next';

export function sanitizeNextPath(raw: string | null): string | null {
	if (!raw) return null;
	if (raw.includes('\\')) return null;
	// eslint-disable-next-line no-control-regex -- matching control characters is the point
	if (/[\u0000-\u001f\u007f]/.test(raw)) return null;
	if (!raw.startsWith('/') || raw.startsWith('//')) return null;
	return raw;
}
