import { readStorage, writeStorage } from '$lib/utils/safeStorage';

type StorageKind = 'local' | 'session';

interface PersistedOptions<T extends string> {
	/** Which Web Storage to back the value with. Defaults to `'local'`. */
	kind?: StorageKind;
	/**
	 * Narrow a raw stored string into `T`, returning `undefined` to fall back —
	 * so a hand-edited or stale key can never seed an invalid value. Omit when any
	 * stored string is acceptable.
	 */
	parse?: (raw: string) => T | undefined;
}

/**
 * A `$state` value mirrored into Web Storage through `safeStorage`, so a
 * preference survives a reload with no read/write boilerplate at the call site:
 * read `.current`, assign `.current`, done.
 *
 * Deliberately routed through `safeStorage` rather than raw Web Storage (or a
 * generic library persisted-state): in-app webviews — Telegram's Android
 * webview, sandboxed iframes, some privacy modes — throw on the very *access* of
 * `localStorage`, which would take down the caller. Here a blocked store
 * degrades to an in-memory value: the preference just doesn't outlive the tab.
 *
 * String values only. Web Storage stores strings, and staying with them avoids
 * a serialize/deserialize surface no caller needs yet — a future object-valued
 * caller adds it then, rather than everyone paying for it now.
 */
export class Persisted<T extends string> {
	#key: string;
	#kind: StorageKind;
	#value = $state<T>() as T;

	constructor(key: string, fallback: T, options: PersistedOptions<T> = {}) {
		this.#key = key;
		this.#kind = options.kind ?? 'local';
		this.#value = this.#load(fallback, options.parse);
	}

	get current(): T {
		return this.#value;
	}

	set current(value: T) {
		this.#value = value;
		writeStorage(this.#kind, this.#key, value);
	}

	#load(fallback: T, parse?: (raw: string) => T | undefined): T {
		const raw = readStorage(this.#kind, this.#key);
		if (raw === null) {
			return fallback;
		}
		if (!parse) {
			return raw as T;
		}
		return parse(raw) ?? fallback;
	}
}
