import type { Picture } from '@sveltejs/enhanced-img';

export interface MapEntry {
	id: string;
	picture: Picture;
	// Short caption under the thumbnail, e.g. «1 этаж».
	label: string;
	alt: string;
	// File name used when downloading the map.
	filename: string;
}

// The caption and alt text are the only per-file metadata that can't be
// derived from the file: both are human-authored Russian, and alt is required
// for accessibility. Intrinsic dimensions, formats and responsive sizes come
// from <enhanced:img> at build time, so dropping in a map of any proportions
// needs only its entry here.
const TEXT: Record<string, { label: string; alt: string }> = {
	'map_1.png': { label: '1 этаж', alt: 'Карта 1 этажа' },
	'map_2.png': { label: '2 и 3 этажи', alt: 'Карта 2 и 3 этажа' }
};

// enhanced-img processes each match at build into a Picture (AVIF/WebP + sized
// variants, content-hashed so a swap busts every cache layer — browser, CDN,
// service worker). eager inlines the objects; import:'default' unwraps each
// module to its Picture.
const modules = import.meta.glob<Picture>('#lib/assets/map/*.{jpg,jpeg,png}', {
	eager: true,
	query: { enhanced: true },
	import: 'default'
});

// Build the gallery from the discovered files, attaching the text by name and
// sorting by id so the order is stable regardless of glob iteration order. A
// file with no TEXT entry is skipped, so a map is shown only once it's described.
export const maps: MapEntry[] = Object.entries(modules)
	.map(([path, picture]) => {
		const filename = path.split('/').pop() ?? '';
		const text = TEXT[filename];
		if (!text) return null;
		return {
			id: filename.replace(/\.[^.]+$/, ''),
			picture,
			label: text.label,
			alt: text.alt,
			filename
		};
	})
	.filter((entry): entry is MapEntry => entry !== null)
	.sort((a, b) => a.id.localeCompare(b.id));
