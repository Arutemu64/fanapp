import { maps } from '#lib/data/maps.js';

export interface MapSelection {
	floorId: string;
	placeNumber: number | null;
}

const defaultFloorId = maps[0]?.id ?? '';

// The floor and the picked place live in the URL so a link can point at a place
// (`/map?floor=floor-2-3&place=14`), and so they survive a reload, the back button and
// a return by the Карта tab. An unknown floor or a place that isn't on it reads as
// nothing picked: a stale link still opens the map.
export function parseMapSelection(params: Pick<URLSearchParams, 'get'>): MapSelection {
	const floor = maps.find((entry) => entry.id === params.get('floor')) ?? maps[0];
	if (!floor) return { floorId: '', placeNumber: null };

	const place = Number.parseInt(params.get('place') ?? '', 10);
	const isOnFloor = floor.points.some((point) => point.number === place);
	return { floorId: floor.id, placeNumber: isOnFloor ? place : null };
}

export function buildMapSelectionQuery(selection: MapSelection): string {
	const params = new URLSearchParams();
	// The first floor is what a bare /map shows, so it stays out of the URL.
	if (selection.floorId !== defaultFloorId) {
		params.set('floor', selection.floorId);
	}
	if (selection.placeNumber !== null) {
		params.set('place', String(selection.placeNumber));
	}
	const query = params.toString();
	return query ? `?${query}` : '';
}
