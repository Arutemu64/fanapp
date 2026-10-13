/**
 * What vite-imagetools' `as=picture` yields: one `srcset` string per
 * non-fallback format, plus the fallback format's largest variant as `img`.
 */
export interface MapPicture {
	/** `srcset` per format, e.g. `{ avif: '… 640w, …', webp: '…' }`. The fallback format has none. */
	sources: Record<string, string>;
	img: { src: string; w: number; h: number };
}

export interface MapEntry {
	id: string;
	picture: MapPicture;
	// Short caption under the thumbnail, e.g. «1 этаж».
	label: string;
	alt: string;
	// File name used when downloading the map.
	filename: string;
}

// The caption and alt text are the only per-file metadata that can't be
// derived from the file: both are human-authored Russian, and alt is required
// for accessibility. Intrinsic dimensions, formats and responsive sizes come
// from vite-imagetools at build time, so dropping in a map of any proportions
// needs only its entry here.
const TEXT: Record<string, { label: string; alt: string }> = {
	'map_1.png': { label: '1 этаж', alt: 'Карта 1 этажа' },
	'map_2.png': { label: '2 и 3 этажи', alt: 'Карта 2 и 3 этажа' }
};

// vite-imagetools processes each match at build into a picture (AVIF/WebP +
// sized variants, content-hashed so a swap busts every cache layer — browser,
// CDN, service worker). The widths bracket the thumbnail (512px at 2x) and run
// up to the 2835px original, which PhotoSwipe's zoom reaches for. PNG is the
// fallback format, last by imagetools' convention. eager inlines the objects;
// import:'default' unwraps each module to its picture.
const modules = import.meta.glob<MapPicture>('#lib/assets/map/*.{jpg,jpeg,png}', {
	eager: true,
	query: { w: '640;1280;1920;2835', format: 'avif;webp;png', as: 'picture' },
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
