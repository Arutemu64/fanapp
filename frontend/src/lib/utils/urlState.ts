import { replaceState } from '$app/navigation';
import { page } from '$app/state';
import { untrack } from 'svelte';

/**
 * Mirror filter state into the current URL's query string.
 *
 * `replaceState` rather than `pushState`: filters change constantly, and one
 * history entry per change would leave the back button unusable. The state still
 * survives a reload, a shared link and a there-and-back navigation — which is
 * the point — it just isn't itself undoable with Back.
 *
 * A param whose value is empty is dropped, so an untouched page keeps a clean
 * URL. Callers must debounce: browsers throw a `SecurityError` when
 * `replaceState` is called too frequently
 * (https://developer.mozilla.org/en-US/docs/Web/API/History/replaceState).
 */
export function syncUrlParams(params: Record<string, string>): void {
	// Untracked: callers run this inside an $effect that should depend on their
	// own filter state, not on the URL this very call is about to rewrite —
	// otherwise every write schedules a redundant re-run of that effect.
	const currentUrl = untrack(() => page.url);
	const currentState = untrack(() => page.state);

	const nextUrl = new URL(currentUrl);
	for (const [key, value] of Object.entries(params)) {
		if (value === '') {
			nextUrl.searchParams.delete(key);
		} else {
			nextUrl.searchParams.set(key, value);
		}
	}

	if (nextUrl.href === currentUrl.href) return;

	// no-navigation-without-resolve guards against hardcoded internal paths that
	// would drop `paths.base`. This URL is a copy of `page.url` with query params
	// edited, so it already carries whatever base the app is served under —
	// there is no path here for `resolve()` to resolve.
	// eslint-disable-next-line svelte/no-navigation-without-resolve
	replaceState(nextUrl, currentState);
}
