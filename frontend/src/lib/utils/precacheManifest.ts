import type { PrecacheEntry } from 'workbox-precaching';

const SHELL_FILE = /\.(js|css|html|svg|ico|webmanifest|woff2|json|wasm)$/;

const ICON = /^icons\/[^/]+\.png$/;

const UNUSED_FONT_SUBSET = /-(greek|greek-ext|vietnamese)-[^/]*\.woff2$/;

interface BuildOutput {
	immutable: readonly { path: string }[];
	assets: readonly { path: string }[];
	fallbackPage: string;
	version: string;
}

export function buildPrecacheManifest(output: BuildOutput): PrecacheEntry[] {
	const entries: PrecacheEntry[] = [];

	for (const { path } of output.immutable) {
		if (SHELL_FILE.test(path) && !UNUSED_FONT_SUBSET.test(path)) {
			entries.push({ url: path, revision: null });
		}
	}

	for (const { path } of output.assets) {
		if (SHELL_FILE.test(path) || ICON.test(path)) {
			entries.push({ url: path, revision: output.version });
		}
	}

	entries.push({ url: output.fallbackPage, revision: output.version });

	return entries;
}
