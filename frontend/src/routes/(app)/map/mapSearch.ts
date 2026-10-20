import { createSearchIndex } from '#lib/utils/search.js';

interface SearchablePoint {
	number: number;
	name: () => string;
	floor?: () => string;
	keywords?: string[];
}

interface SearchableMap<P extends SearchablePoint> {
	id: string;
	label: () => string;
	points: P[];
}

export interface MapSearchResult<P extends SearchablePoint> {
	mapId: string;
	/** Where to look: the point's own floor where it has one («3 этаж»), else its plan's. */
	floorLabel: string;
	point: P;
}

/**
 * Search every floor's «Что где» at once, by name and alias, so "where is the
 * toilet?" needs no idea which floor to open first. Results keep the plans' order.
 */
export function createMapSearch<P extends SearchablePoint>(
	maps: readonly SearchableMap<P>[]
): (query: string) => MapSearchResult<P>[] {
	const entries = maps.flatMap((map) =>
		map.points.map((point) => ({
			mapId: map.id,
			floorLabel: point.floor?.() ?? map.label(),
			point
		}))
	);
	const index = createSearchIndex(entries, (entry) => [
		entry.point.name(),
		...(entry.point.keywords ?? [])
	]);
	return (query) => index.filter(query);
}
