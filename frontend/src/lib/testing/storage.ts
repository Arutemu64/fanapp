// Test-only fakes. The Vitest runner is Node with no DOM (ADR-0011), so there is
// no real Web Storage: install these with `vi.stubGlobal('localStorage', …)`.

/** Map-backed Storage for the pass-through cases. */
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

/** Storage whose every access throws, like a blocked in-app webview. */
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
