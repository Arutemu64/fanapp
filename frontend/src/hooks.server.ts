import * as Sentry from '@sentry/sveltekit';
import type { HandleServerError } from '@sveltejs/kit';

// SPA-only: pages render on the client and auth/guards live in universal load
// functions. The node server just serves the static shell, so the only server
// hook left is Sentry error tracking.
export const handle = Sentry.sentryHandle();

export const handleError: HandleServerError = Sentry.handleErrorWithSentry(({ error }) => {
	const err = error as { code?: string } | undefined;

	// Localized Russian error response to fulfill the Russian Copy policy
	return {
		message: 'Произошла непредвиденная ошибка на сервере.',
		code: err?.code ?? 'UNKNOWN'
	};
});
