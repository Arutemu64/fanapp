import { Avatar, Style } from '@dicebear/core';
import definition from '@dicebear/styles/initial-face.json';

const style = new Style(definition);

const DATA_URI_CACHE_LIMIT = 200;
const dataUriCache = new Map<string, string>();

export function getAvatarDataUri(seed: string): string {
	let uri = dataUriCache.get(seed);
	if (!uri) {
		uri = new Avatar(style, { seed }).toDataUri();
		if (dataUriCache.size >= DATA_URI_CACHE_LIMIT) {
			const oldest = dataUriCache.keys().next();
			if (!oldest.done) {
				dataUriCache.delete(oldest.value);
			}
		}
		dataUriCache.set(seed, uri);
	}
	return uri;
}

export function createAvatarSeed(): string {
	const bytes = crypto.getRandomValues(new Uint8Array(9));
	return btoa(String.fromCharCode(...bytes))
		.replaceAll('+', '-')
		.replaceAll('/', '_');
}
