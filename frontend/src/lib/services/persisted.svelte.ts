import { readStorage, writeStorage } from '#lib/utils/safeStorage.js';

type StorageKind = 'local' | 'session';

interface PersistedOptions<T extends string> {
	kind?: StorageKind;
	parse?: (raw: string) => T | undefined;
}

export class Persisted<T extends string> {
	readonly #key: string;
	readonly #kind: StorageKind;
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
