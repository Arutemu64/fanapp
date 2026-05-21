/**
 * Shared validation helpers for forms.
 * Keep functions pure and SSR-safe.
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Validates a raw email string.
 * Does not normalize — check separately if needed.
 */
export function isValidEmail(value: string): boolean {
	if (!value) return false;
	return EMAIL_REGEX.test(value);
}

/**
 * Trims and lowercases an email for consistent comparison and API calls.
 */
export function normalizeEmail(value: string): string {
	return value.trim().toLowerCase();
}
