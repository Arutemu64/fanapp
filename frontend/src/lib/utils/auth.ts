import type { QueryClient } from '@tanstack/vue-query';
import type { Router } from 'vue-router';

import type { EventsClient } from '#lib/services/events.js';
import type { useToastStore } from '#lib/stores/toasts.js';

import { getCurrentUserQueryKey } from '#lib/api/generated/@tanstack/vue-query.gen.js';

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
	// eslint-disable-next-line no-control-regex
	if (/[\u0000-\u001f\u007f]/.test(raw)) return null;
	if (!raw.startsWith('/') || raw.startsWith('//')) return null;
	return raw;
}

// The catch-all record (`:pathMatch(.*)*`) matches every path, so it does not
// count as the route the user was heading to.
function matchesRoute(router: Router, path: string): boolean {
	const { matched } = router.resolve(path);
	return matched.length > 0 && !matched.some((record) => record.path.includes(':pathMatch'));
}

/**
 * Finish a successful login: load the new identity, confirm with a toast,
 * navigate to the page the user originally wanted (the validated `next` param,
 * home otherwise), then restart the SSE stream so live events resume under the
 * new identity. Shared by every login form.
 */
export async function completeLogin(
	toasts: ReturnType<typeof useToastStore>,
	eventsClient: EventsClient,
	queryClient: QueryClient,
	router: Router,
	message: string
): Promise<void> {
	// A logout queued while offline must not outlive a deliberate re-login: clear
	// it so the reconnect flush can't revoke this fresh session (see pendingLogout).
	clearLogoutPending();

	// Everything cached so far was fetched as a guest: mark it all stale, so what
	// is on screen refetches now and the rest when next shown. Identity is awaited,
	// since the guards on the way to `next` read it from the cache.
	void queryClient.invalidateQueries();
	await queryClient.refetchQueries({ queryKey: getCurrentUserQueryKey() });

	toasts.add(message, 'success');
	const next = sanitizeNextPath(new URL(window.location.href).searchParams.get(LOGIN_NEXT_PARAM));
	// `next` is sanitized to an in-app path above. The router resolves it with no
	// match when it names no route (or lands on the catch-all), and it comes from
	// the URL, so a hand-edited one can name anything: land on home rather than
	// strand the now-signed-in user on the login form.
	const home = '/';
	const destination = next !== null && matchesRoute(router, next) ? next : home;
	try {
		await router.push(destination);
	} catch {
		await router.push(home);
	}
	eventsClient.restart();
}
