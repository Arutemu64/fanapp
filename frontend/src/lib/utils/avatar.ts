import { Avatar, Style } from '@dicebear/core';
import definition from '@dicebear/styles/initial-face.json';

const style = new Style(definition);

export function getAvatarDataUri(seed: string): string {
	return new Avatar(style, { seed }).toDataUri();
}

export function createAvatarSeed(): string {
	const bytes = crypto.getRandomValues(new Uint8Array(9));
	return btoa(String.fromCharCode(...bytes))
		.replaceAll('+', '-')
		.replaceAll('/', '_');
}
