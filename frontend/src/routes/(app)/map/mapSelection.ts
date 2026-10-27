import { maps } from '#lib/data/maps.js';

export interface MapSelection {
	floorId: string;
	placeNumber: number | null;
}

const defaultFloorId = maps[0]?.id ?? '';

export function parseMapSelection(params: Pick<URLSearchParams, 'get'>): MapSelection {
	const floor = maps.find((entry) => entry.id === params.get('floor')) ?? maps[0];
	if (!floor) return { floorId: '', placeNumber: null };

	const place = Number.parseInt(params.get('place') ?? '', 10);
	const isOnFloor = floor.points.some((point) => point.number === place);
	return { floorId: floor.id, placeNumber: isOnFloor ? place : null };
}

export function buildMapSelectionQuery(selection: MapSelection): string {
	const params = new URLSearchParams();
	if (selection.floorId !== defaultFloorId) {
		params.set('floor', selection.floorId);
	}
	if (selection.placeNumber !== null) {
		params.set('place', String(selection.placeNumber));
	}
	const query = params.toString();
	return query ? `?${query}` : '';
}
