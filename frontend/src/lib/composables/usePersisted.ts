import { customRef, type Ref } from 'vue';

import { readStorage, writeStorage } from '#lib/utils/safeStorage.js';

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

function load<T extends string>(
	kind: StorageKind,
	key: string,
	fallback: T,
	parse?: (raw: string) => T | undefined
): T {
	const raw = readStorage(kind, key);
	if (raw === null) {
		return fallback;
	}
	if (!parse) {
		return raw as T;
	}
	return parse(raw) ?? fallback;
}

/**
 * A ref mirrored into Web Storage through `safeStorage`, so a preference
 * survives a reload with no read/write boilerplate at the call site: read
 * `.value`, assign `.value`, done.
 *
 * Deliberately routed through `safeStorage` rather than raw Web Storage (or a
 * generic library persisted-state such as VueUse's `useStorage`): in-app
 * webviews — Telegram's Android webview, sandboxed iframes, some privacy modes —
 * throw on the very *access* of `localStorage`, which would take down the
 * caller. Here a blocked store degrades to an in-memory value: the preference
 * just doesn't outlive the tab.
 *
 * A `customRef` writes through synchronously on assignment; a `watch` would
 * defer the write to the next flush.
 *
 * String values only. Web Storage stores strings, and staying with them avoids
 * a serialize/deserialize surface no caller needs yet — a future object-valued
 * caller adds it then, rather than everyone paying for it now.
 */
export function usePersisted<T extends string>(
	key: string,
	fallback: T,
	options: PersistedOptions<T> = {}
): Ref<T> {
	const kind = options.kind ?? 'local';
	let value = load(kind, key, fallback, options.parse);

	return customRef<T>((track, trigger) => ({
		get() {
			track();
			return value;
		},
		set(next) {
			value = next;
			writeStorage(kind, key, next);
			trigger();
		}
	}));
}
