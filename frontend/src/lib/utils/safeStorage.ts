/**
 * Web Storage (localStorage/sessionStorage) that can't crash the caller.
 *
 * In-app browsers (notably Telegram's Android webview, iOS WKWebView, sandboxed
 * iframes, `data:` URLs and some privacy modes) partition or block storage, so
 * even *accessing* the `localStorage`/`sessionStorage` property throws
 * SecurityError — a `if (window.localStorage)` feature-detect throws on the same
 * line. The only robust guard is a try/catch around the actual read/write,
 * treating failure as "no value stored". Reach for these helpers instead of
 * touching Web Storage directly so a hostile storage environment degrades
 * gracefully rather than taking down whatever code ran the access.
 *
 * The `app.html` boot script guards inline instead: it runs before this bundle
 * loads, so it can't import from here.
 */

type StorageKind = 'local' | 'session';

function storage(kind: StorageKind): Storage {
	return kind === 'local' ? localStorage : sessionStorage;
}

/** Read a key, or `null` if it is unset or storage is unavailable. */
export function readStorage(kind: StorageKind, key: string): string | null {
	try {
		return storage(kind).getItem(key);
	} catch {
		return null;
	}
}

/** Write a key, returning whether the value was actually persisted. */
export function writeStorage(kind: StorageKind, key: string, value: string): boolean {
	try {
		storage(kind).setItem(key, value);
		return true;
	} catch {
		return false;
	}
}

/** Remove a key; a no-op when storage is unavailable. */
export function removeStorage(kind: StorageKind, key: string): void {
	try {
		storage(kind).removeItem(key);
	} catch {
		// Storage blocked — nothing to remove.
	}
}
