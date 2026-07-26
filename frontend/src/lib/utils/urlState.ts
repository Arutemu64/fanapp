import { goto } from '$app/navigation';
import { page } from '$app/state';
import { onDestroy } from 'svelte';

// Long enough to swallow a burst of typing, short enough that the address bar
// has caught up by the time a user stops to read the results.
const URL_WRITE_DELAY_MS = 300;

/**
 * A filter value backed by a URL search param, so it survives a reload, a
 * shared link, and a there-and-back navigation.
 *
 * The URL is the source of truth: `current` reads from `page.url`, so a change
 * from outside — Back/Forward, a link carrying the param — shows up in the UI
 * with nothing to keep in sync.
 *
 * Writes go through `goto`, which is what the SvelteKit docs recommend for
 * filter state, and deliberately *not* through shallow routing's
 * `replaceState`: that updates the address bar but leaves `page.url` untouched,
 * so a value written with it could never be read back. `replaceState: true`
 * keeps filters out of the back button, and `keepFocus`/`noScroll` stop a
 * navigation per keystroke from pulling focus out of the search box or jumping
 * the page to the top.
 *
 * Construct it during component initialization — it registers an `onDestroy` to
 * drop a pending write when the page goes away.
 */
export class UrlParam {
	#key: string;
	// The value typed since the last write landed; null once the URL agrees, so
	// reads fall through to it. It exists only so typing feels instant — between
	// a keystroke and the debounced write the URL still holds the old value.
	#pending: string | null = $state(null);
	#timer: ReturnType<typeof setTimeout> | undefined;

	constructor(key: string) {
		this.#key = key;
		onDestroy(() => clearTimeout(this.#timer));
	}

	get current(): string {
		return this.#pending ?? page.url.searchParams.get(this.#key) ?? '';
	}

	set current(value: string) {
		this.#pending = value;
		clearTimeout(this.#timer);
		this.#timer = setTimeout(() => void this.#write(), URL_WRITE_DELAY_MS);
	}

	async #write(): Promise<void> {
		const value = this.#pending;
		if (value === null) return;

		const nextUrl = new URL(page.url);
		if (value === '') {
			// An empty filter drops the param, so an untouched page keeps a clean URL.
			nextUrl.searchParams.delete(this.#key);
		} else {
			nextUrl.searchParams.set(this.#key, value);
		}

		if (nextUrl.href !== page.url.href) {
			// no-navigation-without-resolve guards against hardcoded internal paths
			// that would drop `paths.base`. This is a copy of `page.url` with one
			// query param edited, so it already carries whatever base the app is
			// served under — there is no path here for `resolve()` to resolve.
			// eslint-disable-next-line svelte/no-navigation-without-resolve
			await goto(nextUrl, { replaceState: true, keepFocus: true, noScroll: true });
		}

		// Only now: `goto` resolves once `page.url` has caught up, and clearing any
		// earlier would flash the previous value back into the input. A keystroke
		// that arrived mid-navigation wins — it has queued its own write already.
		if (this.#pending === value) {
			this.#pending = null;
		}
	}
}

/**
 * A boolean filter backed by a URL search param. Present and `1` means on;
 * anything else, including absence, means off.
 */
export class UrlFlag {
	#param: UrlParam;

	constructor(key: string) {
		this.#param = new UrlParam(key);
	}

	get current(): boolean {
		return this.#param.current === '1';
	}

	set current(value: boolean) {
		this.#param.current = value ? '1' : '';
	}
}
