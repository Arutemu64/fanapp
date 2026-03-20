export function getApiErrorDetail(error: unknown): string | null {
	if (!error || typeof error !== 'object') {
		return null;
	}

	if ('detail' in error && typeof error.detail === 'string') {
		return error.detail;
	}

	return null;
}
