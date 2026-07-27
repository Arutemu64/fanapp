// Mirror a page's filter controls (search box, toggles) into the query string.
//
// The filters themselves stay in component state: reading them in `load`
// instead would re-run it on every keystroke, because SvelteKit tracks each
// search param a `load` reads. So the URL is a one-way mirror — seeded into
// component state once at init, written back from the controls' handlers.

import { goto } from '$app/navigation';
import { page } from '$app/state';
import { onDestroy } from 'svelte';

// How long a typed query waits before it reaches the URL. Filtering runs off
// local state and stays instant; this only delays the address bar, and keeps a
// typed word from running the router once per character.
const DEBOUNCE_MS = 250;

/** One entry per filter. `null` or an empty string removes the param. */
export type FilterParams = Record<string, string | null>;

export type UrlFilterSync = {
	/**
	 * Write the page's filters into the query string, replacing any write still
	 * waiting out its debounce. Pass every filter the page owns on each call:
	 * a param carried only by a superseded call never lands.
	 */
	set(params: FilterParams, options?: { debounce?: boolean }): void;
};

/**
 * Create a query-string mirror for one page's filters.
 *
 * Call this during component initialization — the syncer cancels its pending
 * write on destroy, and needs the component's lifecycle to do it.
 */
export function createUrlFilterSync(): UrlFilterSync {
	let pendingWrite: ReturnType<typeof setTimeout> | undefined;

	// A debounced write that outlived its page would call `goto` for a route the
	// user has already left, yanking them back to it.
	onDestroy(() => clearTimeout(pendingWrite));

	function write(params: FilterParams) {
		const url = new URL(page.url);

		for (const [name, value] of Object.entries(params)) {
			if (value) {
				url.searchParams.set(name, value);
			} else {
				// Keep an untouched page on a clean URL, and let a cleared filter
				// disappear instead of lingering as an empty `?q=`.
				url.searchParams.delete(name);
			}
		}

		if (url.href === page.url.href) return;

		// `replaceState` keeps a typed word from leaving one history entry per
		// character (back would then walk it letter by letter); `keepFocus` holds
		// the caret in the search box across the navigation and `noScroll` leaves
		// the reading position alone. Nothing refetches — no `load` on these pages
		// reads `url`, so the dependency tracking never fires.
		//
		// The URL is a copy of `page.url` with params edited, so it is already
		// base-qualified — resolve() would prepend the base path a second time.
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		goto(url, { replaceState: true, keepFocus: true, noScroll: true }).catch(() => {
			// `goto` rejects when another navigation interrupts it. The query string
			// is a convenience mirror, so a dropped write isn't worth surfacing —
			// but an unhandled rejection would reach Sentry.
		});
	}

	return {
		set(params, options) {
			clearTimeout(pendingWrite);

			if (options?.debounce) {
				pendingWrite = setTimeout(() => write(params), DEBOUNCE_MS);
				return;
			}

			write(params);
		}
	};
}
