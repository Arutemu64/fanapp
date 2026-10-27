import { m } from '#lib/paraglide/messages.js';

interface MapPoint {
	number: number;
	name: () => string;
	floor?: () => string;
}

interface Rect {
	x: number;
	y: number;
	w: number;
	h: number;
}

interface MapZone extends Rect {
	point: number;
}

interface FloorPlan {
	viewBox: string;
	walls: string;
	pillars: Rect[];
	stairs: Rect[];
	wells: Rect[];
	columns: [number, number, number][];
	captions: { x: number; y: number; text: () => string }[];
	zones: MapZone[];
	fontSize: number;
}

interface MapEntry {
	id: string;
	label: () => string;
	alt: () => string;
	plan: FloorPlan;
	points: MapPoint[];
}

export const WALL_WIDTH = 9;

function numbered(names: (() => string)[]): MapPoint[] {
	return names.map((name, index) => ({ number: index + 1, name }));
}

const FLOOR_1: FloorPlan = {
	viewBox: '150 140 610 700',
	fontSize: 22,
	walls: [
		'M196 153 H406 V387',
		'M196 153 V434 H261',
		'M197 387 H277',
		'M159 434 V487 H374',
		'M322 387 H704 V491 H729',
		'M729 543 H704 V762 H729',
		'M729 812 H704 V826 H604',
		'M553 826 H452 V542 H342',
		'M452 387 V455',
		'M494 491 V426 H547',
		'M611 426 H665 V491'
	].join(' '),
	pillars: [
		{ x: 403, y: 482, w: 10, h: 10 },
		{ x: 444, y: 482, w: 10, h: 10 },
		{ x: 489, y: 484, w: 12, h: 12 },
		{ x: 540, y: 484, w: 10, h: 12 },
		{ x: 612, y: 484, w: 10, h: 12 },
		{ x: 660, y: 484, w: 12, h: 12 }
	],
	stairs: [
		{ x: 456, y: 427, w: 38, h: 24 },
		{ x: 547, y: 427, w: 64, h: 28 },
		{ x: 556, y: 480, w: 54, h: 16 },
		{ x: 669, y: 427, w: 32, h: 24 },
		{ x: 688, y: 494, w: 16, h: 42 },
		{ x: 688, y: 770, w: 16, h: 42 },
		{ x: 222, y: 442, w: 24, h: 40 }
	],
	wells: [],
	columns: [
		[501, 537, 6],
		[656, 537, 6]
	],
	captions: [],
	zones: [
		{ point: 1, x: 552, y: 796, w: 52, h: 26 },
		{ point: 2, x: 491, y: 551, w: 178, h: 233 },
		{ point: 3, x: 558, y: 396, w: 40, h: 28 },
		{ point: 3, x: 711, y: 494, w: 30, h: 42 },
		{ point: 3, x: 711, y: 771, w: 30, h: 42 },
		{ point: 4, x: 617, y: 434, w: 40, h: 57 },
		{ point: 5, x: 501, y: 434, w: 40, h: 57 },
		{ point: 6, x: 342, y: 494, w: 33, h: 42 },
		{ point: 7, x: 370, y: 396, w: 74, h: 48 },
		{ point: 8, x: 211, y: 171, w: 173, h: 203 },
		{ point: 9, x: 202, y: 396, w: 49, h: 33 },
		{ point: 10, x: 176, y: 442, w: 35, h: 39 }
	]
};

const FLOOR_2_3: FloorPlan = {
	viewBox: '45 50 835 740',
	fontSize: 28,
	walls: [
		'M54 343 H119 V202 H831 V329 H870',
		'M54 407 H115 V682 H54',
		'M54 743 H115 V780 H831 V396 H870',
		'M449 202 V336',
		'M449 332 H751',
		'M449 396 V652',
		'M449 704 V780',
		'M449 704 H517',
		'M511 396 V509',
		'M511 604 V704',
		'M529 59 H831 V177 H529 Z'
	].join(' '),
	pillars: [
		...[401, 461, 521, 582, 650, 708].flatMap((y) => [
			{ x: 167, y, w: 12, h: 11 },
			{ x: 377, y, w: 12, h: 11 }
		]),
		{ x: 507, y: 549, w: 9, h: 12 }
	],
	stairs: [
		{ x: 172, y: 209, w: 39, h: 48 },
		{ x: 347, y: 209, w: 39, h: 48 },
		{ x: 126, y: 259, w: 43, h: 75 },
		{ x: 388, y: 259, w: 55, h: 75 },
		{ x: 678, y: 337, w: 51, h: 58 },
		{ x: 678, y: 707, w: 51, h: 68 },
		{ x: 176, y: 721, w: 35, h: 47 },
		{ x: 354, y: 721, w: 36, h: 47 },
		{ x: 546, y: 125, w: 44, h: 38 },
		{ x: 769, y: 125, w: 46, h: 38 }
	],
	wells: [
		{ x: 172, y: 259, w: 214, h: 57 },
		{ x: 517, y: 336, w: 159, h: 64 },
		{ x: 517, y: 704, w: 159, h: 75 }
	],
	columns: [[672, 556, 34]],
	captions: [{ x: 680, y: 84, text: m.map_point_on_floor_3 }],
	zones: [
		{ point: 1, x: 219, y: 379, w: 118, h: 39 },
		{ point: 2, x: 219, y: 423, w: 118, h: 266 },
		{ point: 3, x: 126, y: 413, w: 36, h: 266 },
		{ point: 4, x: 77, y: 352, w: 33, h: 49 },
		{ point: 4, x: 77, y: 691, w: 33, h: 50 },
		{ point: 5, x: 397, y: 413, w: 41, h: 97 },
		{ point: 6, x: 126, y: 708, w: 48, h: 61 },
		{ point: 6, x: 393, y: 708, w: 47, h: 61 },
		{ point: 7, x: 219, y: 318, w: 118, h: 31 },
		{ point: 7, x: 219, y: 723, w: 118, h: 46 },
		{ point: 7, x: 457, y: 640, w: 47, h: 61 },
		{ point: 7, x: 724, y: 495, w: 85, h: 111 },
		{ point: 8, x: 396, y: 533, w: 40, h: 102 },
		{ point: 9, x: 528, y: 614, w: 185, h: 85 },
		{ point: 10, x: 528, y: 405, w: 183, h: 86 },
		{ point: 11, x: 528, y: 224, w: 139, h: 87 },
		{ point: 12, x: 676, y: 224, w: 138, h: 87 },
		{ point: 13, x: 835, y: 340, w: 40, h: 48 },
		{ point: 14, x: 607, y: 96, w: 70, h: 68 },
		{ point: 15, x: 681, y: 96, w: 70, h: 68 }
	]
};

export const maps: MapEntry[] = [
	{
		id: 'floor-1',
		label: m.map_floor_1_label,
		alt: m.map_floor_1_alt,
		plan: FLOOR_1,
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
	{
		id: 'floor-2-3',
		label: m.map_floor_2_3_label,
		alt: m.map_floor_2_3_alt,
		plan: FLOOR_2_3,
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
];
