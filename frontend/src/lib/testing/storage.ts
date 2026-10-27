export function fakeStorage(): Storage {
	const map = new Map<string, string>();
	return {
		getItem: (k) => map.get(k) ?? null,
		setItem: (k, v) => void map.set(k, v),
		removeItem: (k) => void map.delete(k),
		clear: () => map.clear(),
		key: (i) => [...map.keys()][i] ?? null,
		get length() {
			return map.size;
		}
	};
}

export function throwingStorage(): Storage {
	const blocked = () => {
		throw new Error('SecurityError: Access is denied for this document.');
	};
	return {
		getItem: blocked,
		setItem: blocked,
		removeItem: blocked,
		clear: blocked,
		key: blocked,
		get length(): number {
			return blocked();
		}
	};
}
