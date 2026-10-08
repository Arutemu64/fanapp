import type { PrecacheEntry } from 'workbox-precaching';

// The app shell: code, styles, fonts, the SVG logo/favicon and the web app
// manifest. Raster images are deliberately not on this list: the responsive
// AVIF/WebP/… variants <enhanced:img> emits would store every width and format
// at install, which is wasteful and discouraged
// (https://developer.chrome.com/docs/workbox/precaching-dos-and-donts); the
// worker serves them cache-first at runtime instead.
const SHELL_FILE = /\.(js|css|html|svg|ico|webmanifest|woff2|json)$/;

// PWA icons are the one raster set we precache: the manifest and push
// notifications point at them, so they must resolve offline.
const ICON = /^icons\/[^/]+\.png$/;

// Font subsets a Russian UI never renders. Left out of the precache, they still
// load on demand via unicode-range (and fall back to a system font offline).
// latin-ext stays: romaji macrons (ō, ū) live there.
const UNUSED_FONT_SUBSET = /-(greek|greek-ext|vietnamese)-[^/]*\.woff2$/;

function isPrecachedImmutable(path: string): boolean {
	return SHELL_FILE.test(path) && !UNUSED_FONT_SUBSET.test(path);
}

// `static/` also holds og-image.png (only link-preview crawlers read it),
// robots.txt and the schedule-import template; none belongs in an offline shell.
function isPrecachedAsset(path: string): boolean {
	return SHELL_FILE.test(path) || ICON.test(path);
}

interface BuildOutput {
	// `immutable` and `assets` from `$app/manifest`.
	immutable: readonly { path: string }[];
	assets: readonly { path: string }[];
	// The adapter-static fallback page every SPA navigation is served from.
	fallbackPage: string;
	// `version` from `$app/env`: changes on every build.
	version: string;
}

/**
 * The Workbox precache list for one build.
 *
 * Immutable files have a content hash in their name, so `revision: null` lets
 * Workbox treat the URL itself as the cache key and skip re-downloading them
 * across deploys. `static/` files and the fallback page keep a fixed URL, so
 * they are revisioned with the build version and refreshed on every deploy —
 * a few small files, traded for not hashing them ourselves.
 */
export function buildPrecacheManifest(output: BuildOutput): PrecacheEntry[] {
	const entries: PrecacheEntry[] = [];

	for (const { path } of output.immutable) {
		if (isPrecachedImmutable(path)) {
			entries.push({ url: path, revision: null });
		}
	}

	for (const { path } of output.assets) {
		if (isPrecachedAsset(path)) {
			entries.push({ url: path, revision: output.version });
		}
	}

	entries.push({ url: output.fallbackPage, revision: output.version });

	return entries;
}
