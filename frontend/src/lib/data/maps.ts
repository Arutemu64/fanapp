import type { Picture } from '@sveltejs/enhanced-img';

export interface MapEntry {
	id: string;
	picture: Picture;
	alt: string;
	// File name used when downloading the map.
	filename: string;
}

// Alt text is the only per-file metadata that can't be derived from the file:
// it's human-authored Russian and required for accessibility. Intrinsic
// dimensions, formats and responsive sizes come from <enhanced:img> at build
// time, so dropping in a map of any proportions needs only its alt entry here.
const ALT: Record<string, string> = {
	'map_1.jpg': 'Карта площадки 1',
	'map_2_3.jpg': 'Карта площадки 2 и 3'
};

// enhanced-img processes each match at build into a Picture (AVIF/WebP + sized
// variants, content-hashed so a swap busts every cache layer — browser, CDN,
// service worker). eager inlines the objects; import:'default' unwraps each
// module to its Picture.
const modules = import.meta.glob<Picture>('$lib/assets/map/*.jpg', {
	eager: true,
	query: { enhanced: true },
	import: 'default'
});

// Build the gallery from the discovered files, attaching alt text by name and
// sorting by id so the order is stable regardless of glob iteration order. A
// file with no ALT entry is skipped, so a map is shown only once it's described.
export const maps: MapEntry[] = Object.entries(modules)
	.map(([path, picture]) => {
		const filename = path.split('/').pop() ?? '';
		const alt = ALT[filename];
		if (!alt) return null;
		return {
			id: filename.replace(/\.[^.]+$/, ''),
			picture,
			alt,
			filename
		};
	})
	.filter((entry): entry is MapEntry => entry !== null)
	.sort((a, b) => a.id.localeCompare(b.id));
