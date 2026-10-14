import { Avatar, Style } from '@dicebear/core';
import definition from '@dicebear/styles/initial-face.json';

// Parsed once; a Style holds no per-user state, so sharing it across navigation
// and login/logout is safe. Rendering happens in the browser rather than through
// the hosted DiceBear API so avatars work offline and no user seed leaves the app.
const style = new Style(definition);

const dataUriCache = new Map<string, string>();

/** Deterministic SVG data URI for a seed: the same seed always draws the same face. */
export function getAvatarDataUri(seed: string): string {
	let uri = dataUriCache.get(seed);
	if (!uri) {
		uri = new Avatar(style, { seed }).toDataUri();
		dataUriCache.set(seed, uri);
	}
	return uri;
}

/**
 * A fresh random seed. 9 random bytes encode to 12 URL-safe characters, which is
 * what the backend's AVATAR_SEED_PATTERN accepts.
 */
export function createAvatarSeed(): string {
	const bytes = crypto.getRandomValues(new Uint8Array(9));
	return btoa(String.fromCharCode(...bytes))
		.replaceAll('+', '-')
		.replaceAll('/', '_');
}
