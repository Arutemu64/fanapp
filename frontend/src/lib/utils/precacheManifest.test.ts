import { describe, expect, it } from 'vitest';

import { buildPrecacheManifest } from './precacheManifest';

const VERSION = '1791429';

function urlsOf(immutable: string[], assets: string[] = []): string[] {
	return buildPrecacheManifest({
		immutable: immutable.map((path) => ({ path })),
		assets: assets.map((path) => ({ path })),
		fallbackPage: '200.html',
		version: VERSION
	}).map((entry) => (typeof entry === 'string' ? entry : entry.url));
}

describe('buildPrecacheManifest', () => {
	it('precaches the hashed app shell', () => {
		expect(
			urlsOf([
				'_app/immutable/entry/app.CF4D9Ccr.js',
				'_app/immutable/assets/0.Cgo3sDEd.css',
				'_app/immutable/assets/logo.Bx1c2d3e.svg',
				'_app/immutable/assets/inter-cyrillic-wght-normal.DqGufNeO.woff2'
			])
		).toEqual([
			'_app/immutable/entry/app.CF4D9Ccr.js',
			'_app/immutable/assets/0.Cgo3sDEd.css',
			'_app/immutable/assets/logo.Bx1c2d3e.svg',
			'_app/immutable/assets/inter-cyrillic-wght-normal.DqGufNeO.woff2',
			'200.html'
		]);
	});

	it('leaves responsive image variants to the runtime cache', () => {
		expect(
			urlsOf([
				'_app/immutable/assets/map_1.B2c3d4e5.avif',
				'_app/immutable/assets/map_1.C3d4e5f6.webp',
				'_app/immutable/assets/main.D4e5f6g7.png',
				'_app/immutable/assets/main.E5f6g7h8.jpg'
			])
		).toEqual(['200.html']);
	});

	it.each([
		'_app/immutable/assets/inter-greek-wght-normal.A1b2c3d4.woff2',
		'_app/immutable/assets/inter-greek-ext-wght-normal.A1b2c3d4.woff2',
		'_app/immutable/assets/unbounded-vietnamese-wght-normal.A1b2c3d4.woff2'
	])('skips the unused font subset %s', (path) => {
		expect(urlsOf([path])).toEqual(['200.html']);
	});

	it('keeps latin-ext, which carries romaji macrons', () => {
		const path = '_app/immutable/assets/inter-latin-ext-wght-normal.A1b2c3d4.woff2';
		expect(urlsOf([path])).toContain(path);
	});

	it('precaches only the static files an offline shell needs', () => {
		expect(
			urlsOf(
				[],
				[
					'favicon.ico',
					'favicon.svg',
					'manifest.json',
					'icons/icon-192.png',
					'icons/badge-96.png',
					'og-image.png',
					'robots.txt',
					'schedule-template.xlsx'
				]
			)
		).toEqual([
			'favicon.ico',
			'favicon.svg',
			'manifest.json',
			'icons/icon-192.png',
			'icons/badge-96.png',
			'200.html'
		]);
	});

	it('keys hashed files by URL and the rest by build version', () => {
		const entries = buildPrecacheManifest({
			immutable: [{ path: '_app/immutable/entry/app.CF4D9Ccr.js' }],
			assets: [{ path: 'manifest.json' }],
			fallbackPage: '200.html',
			version: VERSION
		});

		expect(entries).toEqual([
			{ url: '_app/immutable/entry/app.CF4D9Ccr.js', revision: null },
			{ url: 'manifest.json', revision: VERSION },
			{ url: '200.html', revision: VERSION }
		]);
	});
});
