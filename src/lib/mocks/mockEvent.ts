import type { ScheduleEventDTO } from '../types/schedule';

export const mockEvents: ScheduleEventDTO[] = [
	{
		id: 1,
		public_id: '001',
		title: 'Открытие фестиваля',
		is_current: false,
		is_skipped: true,
		order: 1,
		duration: 1800,
		queue: null,
		cumulative_duration: 1800,
		nomination: null,
		block: {
			id: 1,
			title: 'День 1 — Открытие'
		},
		subscription: null
	},
	{
		id: 2,
		public_id: '002',
		title: 'Вокальный номер "Весенние нотки"',
		is_current: true,
		is_skipped: false,
		order: 2,
		duration: 300,
		queue: 1,
		cumulative_duration: 2100,
		nomination: {
			id: 1,
			title: 'Лучший вокал'
		},
		block: {
			id: 2,
			title: 'День 1 — Вокальные номера'
		},
		subscription: {
			id: 101,
			counter: 3
		}
	},
	{
		id: 3,
		public_id: '003',
		title: 'Танец "Огонь и лёд"',
		is_current: false,
		is_skipped: false,
		order: 3,
		duration: 420,
		queue: 2,
		cumulative_duration: 2520,
		nomination: {
			id: 2,
			title: 'Лучший танец'
		},
		block: {
			id: 3,
			title: 'День 2 — Танцевальные номера'
		},
		subscription: null
	}
];
