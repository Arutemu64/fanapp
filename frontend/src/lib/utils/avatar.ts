import { Avatar, Style } from '@dicebear/core';
import definition from '@dicebear/styles/initial-face.json';

// Parsed once; a Style holds no per-user state, so sharing it across navigation
// and login/logout is safe. Rendering happens in the browser rather than through
// the hosted DiceBear API so avatars work offline and no user seed leaves the app.
const style = new Style(definition);

// Bounded because an organiser scrolling the users directory and a reroll that gets
// cancelled each draw faces nobody will ask for again. Map iterates in insertion
// order, so the first key is the oldest.
const DATA_URI_CACHE_LIMIT = 200;
const dataUriCache = new Map<string, string>();

export function getAvatarDataUri(seed: string): string {
	let uri = dataUriCache.get(seed);
	if (!uri) {
		uri = new Avatar(style, { seed }).toDataUri();
		if (dataUriCache.size >= DATA_URI_CACHE_LIMIT) {
			dataUriCache.delete(dataUriCache.keys().next().value!);
		}
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
