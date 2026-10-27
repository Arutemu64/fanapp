type StorageKind = 'local' | 'session';

function storage(kind: StorageKind): Storage {
	return kind === 'local' ? localStorage : sessionStorage;
}

export function readStorage(kind: StorageKind, key: string): string | null {
	try {
		return storage(kind).getItem(key);
	} catch {
		return null;
	}
}

export function writeStorage(kind: StorageKind, key: string, value: string): boolean {
	try {
		storage(kind).setItem(key, value);
		return true;
	} catch {
		return false;
	}
}

export function removeStorage(kind: StorageKind, key: string): void {
	try {
		storage(kind).removeItem(key);
	} catch {
		// Storage is blocked, so there is nothing to remove.
	}
}
