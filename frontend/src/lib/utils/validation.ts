const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const OTP_REGEX = /^\d{6}$/;

export function isValidEmail(value: string): boolean {
	if (!value) return false;
	return EMAIL_REGEX.test(value);
}

export function normalizeEmail(value: string): string {
	return value.trim().toLowerCase();
}

export function isValidOtp(value: string): boolean {
	return OTP_REGEX.test(value);
}
