/**
 * Shared validation helpers for forms.
 * Keep functions pure and free of side effects.
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const OTP_REGEX = /^\d{6}$/;

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

/**
 * Whether a string is a well-formed 6-digit one-time code.
 */
export function isValidOtp(value: string): boolean {
	return OTP_REGEX.test(value);
}
