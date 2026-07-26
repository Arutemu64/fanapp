// The venue maps shown on /map, shared by the page and its fullscreen viewer.

export interface MapEntry {
	id: string;
	src: string;
	// Short name for the card caption and the viewer title. Matches the heading
	// printed on the artwork itself, so the label and the image agree on screen.
	// Kept separate from `alt`, which has to stand alone when read out with no
	// surrounding context.
	label: string;
	alt: string;
	width: number;
	height: number;
	// File name used when downloading the map.
	filename: string;
}

// Per-file metadata keyed by the source file name. Image URLs are discovered
// from the bundle below, so adding a map needs only a new file in
// $lib/assets/map plus an entry here (label + alt text + intrinsic dimensions,
// which keep the layout stable while the image loads).
const META: Record<string, Omit<MapEntry, 'filename' | 'id' | 'src'>> = {
	'map_1.jpg': { alt: 'Карта площадки, 1 этаж', height: 831, label: '1 этаж', width: 1280 },
	'map_2_3.jpg': {
		alt: 'Карта площадки, 2 и 3 этаж',
		height: 787,
		label: '2 и 3 этаж',
		width: 1280
	}
};

// Vite resolves these imports to content-hashed URLs at build time, so a
// swapped map busts every cache layer (browser, CDN, service worker)
// automatically. eager = inline the URL strings; ?url = the asset URL rather
// than the decoded module.
const modules = import.meta.glob('$lib/assets/map/*.jpg', {
	eager: true,
	import: 'default',
	query: '?url'
});

// Build the gallery from the discovered files, attaching metadata by name and
// sorting by id so the order is stable regardless of glob iteration order.
export const maps: MapEntry[] = Object.entries(modules)
	.map(([path, src]) => {
		const filename = path.split('/').pop() ?? '';
		const meta = META[filename];
		if (!meta) return null;
		return {
			...meta,
			filename,
			id: filename.replace(/\.[^.]+$/, ''),
			src
		};
	})
	.filter((entry): entry is MapEntry => entry !== null)
	.sort((a, b) => a.id.localeCompare(b.id));
