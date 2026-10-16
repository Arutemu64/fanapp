/**
 * Query param carrying the in-app path a guest was trying to reach when the
 * `(protected)` guard bounced them to `/login`. Read back after a successful
 * login so the user lands where they were originally headed.
 */
export const LOGIN_NEXT_PARAM = 'next';

/**
 * Validate a candidate post-login destination. Only same-app absolute paths
 * (`/...`) are accepted; absolute URLs, protocol-relative `//host` forms and
 * backslash and control-character variants return `null`, so a crafted login
 * link can never redirect the user off-site (open redirect).
 */
export function sanitizeNextPath(raw: string | null): string | null {
	if (!raw) return null;
	// Browsers normalize backslashes to slashes in URLs, so '/\evil.com' would
	// become '//evil.com' after navigation — reject any backslash outright.
	if (raw.includes('\\')) return null;
	// URL parsers also strip tab/CR/LF anywhere, so '/\t/evil.com' would become
	// '//evil.com' — reject every control character.
	// eslint-disable-next-line no-control-regex -- matching control characters is the point
	if (/[\u0000-\u001f\u007f]/.test(raw)) return null;
	if (!raw.startsWith('/') || raw.startsWith('//')) return null;
	return raw;
}
