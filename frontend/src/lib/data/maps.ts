import type { Picture } from '@sveltejs/enhanced-img';

import { m } from '#lib/paraglide/messages.js';

/** A numbered marker on the poster, listed under the maps as «Что где». */
export interface MapPoint {
	/** The number printed on the poster, so the list and the map agree. */
	number: number;
	name: () => string;
	/** Set where the poster shows a point off the map's main floor, e.g. «3 этаж». */
	floor?: () => string;
}

export interface MapEntry {
	id: string;
	picture: Picture;
	// Short caption under the thumbnail, e.g. «1 этаж».
	label: () => string;
	alt: () => string;
	// File name used when downloading the map.
	filename: string;
	points: MapPoint[];
}

function numbered(names: (() => string)[]): MapPoint[] {
	return names.map((name, index) => ({ number: index + 1, name }));
}

// The caption, alt text and legend are the only per-file metadata that can't be
// derived from the file: all are human-authored Russian, and alt is required
// for accessibility. The legend repeats the poster's own, in order, as text a
// phone can read without zooming into the image. Intrinsic dimensions, formats
// and responsive sizes come from <enhanced:img> at build time, so dropping in a
// map of any proportions needs only its entry here.
const TEXT: Record<string, Pick<MapEntry, 'label' | 'alt' | 'points'>> = {
	'map_1.png': {
		label: m.map_floor_1_label,
		alt: m.map_floor_1_alt,
		points: numbered([
			m.map_floor_1_point_01,
			m.map_floor_1_point_02,
			m.map_floor_1_point_03,
			m.map_floor_1_point_04,
			m.map_floor_1_point_05,
			m.map_floor_1_point_06,
			m.map_floor_1_point_07,
			m.map_floor_1_point_08,
			m.map_floor_1_point_09,
			m.map_floor_1_point_10
		])
	},
	'map_2.png': {
		label: m.map_floor_2_3_label,
		alt: m.map_floor_2_3_alt,
		points: [
			...numbered([
				m.map_floor_2_3_point_01,
				m.map_floor_2_3_point_02,
				m.map_floor_2_3_point_03,
				m.map_floor_2_3_point_04,
				m.map_floor_2_3_point_05,
				m.map_floor_2_3_point_06,
				m.map_floor_2_3_point_07,
				m.map_floor_2_3_point_08,
				m.map_floor_2_3_point_09,
				m.map_floor_2_3_point_10,
				m.map_floor_2_3_point_11,
				m.map_floor_2_3_point_12,
				m.map_floor_2_3_point_13
			]),
			{ number: 14, name: m.map_floor_2_3_point_14, floor: m.map_point_on_floor_3 },
			{ number: 15, name: m.map_floor_2_3_point_15, floor: m.map_point_on_floor_3 }
		]
	}
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
			filename,
			points: text.points
		};
	})
	.filter((entry): entry is MapEntry => entry !== null)
	.sort((a, b) => a.id.localeCompare(b.id));
