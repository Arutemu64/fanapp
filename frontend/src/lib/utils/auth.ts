import type { EventsClient } from '$lib/services/events.svelte';
import type { ToastService } from '$lib/services/toasts.svelte';

import { goto } from '$app/navigation';
import { resolve } from '$app/paths';

import { clearLogoutPending } from './pendingLogout';

/**
 * Query param carrying the in-app path a guest was trying to reach when the
 * `(protected)` guard bounced them to `/login`. Read back after a successful
 * login so the user lands where they were originally headed.
 */
export const LOGIN_NEXT_PARAM = 'next';

/**
 * Validate a candidate post-login destination. Only same-app absolute paths
 * (`/...`) are accepted; absolute URLs, protocol-relative `//host` forms and
 * backslash variants return `null`, so a crafted login link can never redirect
 * the user off-site (open redirect).
 */
export function sanitizeNextPath(raw: string | null): string | null {
	if (!raw) return null;
	// Browsers normalize backslashes to slashes in URLs, so '/\evil.com' would
	// become '//evil.com' after navigation — reject any backslash outright.
	if (raw.includes('\\')) return null;
	if (!raw.startsWith('/') || raw.startsWith('//')) return null;
	return raw;
}

/**
 * Finish a successful login: confirm with a toast, navigate to the page the
 * user originally wanted (the validated `next` param, home otherwise) while
 * revalidating all loaders so the session-aware UI updates, then restart the
 * SSE stream so live events resume under the new identity. Shared by every
 * login form.
 */
export async function completeLogin(
	toastService: ToastService,
	eventsClient: EventsClient,
	message: string
): Promise<void> {
	// A logout queued while offline must not outlive a deliberate re-login: clear
	// it so the reconnect flush can't revoke this fresh session (see pendingLogout).
	clearLogoutPending();

	toastService.add(message, 'success');
	const next = sanitizeNextPath(new URL(window.location.href).searchParams.get(LOGIN_NEXT_PARAM));
	// `next` was captured by the (protected) guard from `url.pathname`, which is
	// already base-qualified — wrapping it in resolve() would prepend the base
	// path a second time. It is sanitized to an in-app path above.
	// eslint-disable-next-line svelte/no-navigation-without-resolve
	await goto(next ?? resolve('/'), { invalidateAll: true });
	eventsClient.restart();
}
