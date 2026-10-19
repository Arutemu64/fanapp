import type {
	GetQuestOutput,
	ListQuestAwardsOutput,
	ListQuestHistoryOutput,
	PublicConfigDto,
	QuestPlayerDto
} from '../../src/lib/api/generated/types.gen';
import type { Handlers } from './api';

import { json } from './api';

const NAMES = [
	'РыжийКот09',
	'СонныйСамурай15',
	'НочнойФилин88',
	'НеоновыйПилот31',
	'МятныйПончик50',
	'ОгненныйРамен21',
	'ПушистыйХомяк77',
	'ДобрыйДракон36',
	'ШустрыйНиндзя03',
	'ЗолотойГрифон58'
];

export function questPlayer(index: number, points: number): QuestPlayerDto {
	return {
		id: `01890000-0000-7000-8000-0000000001${String(index).padStart(2, '0')}`,
		username: NAMES[index] ?? `player_${index}`,
		avatar_seed: `questSeed${index}`,
		points
	};
}

export const QUEST: GetQuestOutput = {
	points: 35,
	rank: 23,
	leaderboard: NAMES.map((_, index) => ({
		rank: index + 1,
		player: questPlayer(index, 240 - index * 15)
	})),
	own_entry: {
		rank: 23,
		player: {
			id: '01890000-0000-7000-8000-000000000001',
			username: 'ЛунныйЛис07',
			avatar_seed: 'e2eSeedVisitor',
			points: 35
		}
	}
};

const minutesAgo = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString();

export const QUEST_HISTORY: ListQuestHistoryOutput = {
	next_cursor: null,
	awards: [
		{
			id: '01890000-0000-7000-8000-000000000401',
			amount: 15,
			message: 'Косплей-фотозона',
			created_at: minutesAgo(5),
			cancelled_at: null
		},
		{
			id: '01890000-0000-7000-8000-000000000402',
			amount: 20,
			message: 'Викторина на главной сцене',
			created_at: minutesAgo(40),
			cancelled_at: null
		},
		{
			id: '01890000-0000-7000-8000-000000000403',
			amount: 10,
			message: 'Ошибочное начисление',
			created_at: minutesAgo(50),
			cancelled_at: minutesAgo(45)
		}
	]
};

export const QUEST_AWARDS: ListQuestAwardsOutput = {
	next_cursor: null,
	awards: [
		{
			id: '01890000-0000-7000-8000-000000000301',
			amount: 20,
			message: 'Нашла все пасхалки на карте',
			created_at: minutesAgo(2),
			cancelled_at: null,
			user: { id: questPlayer(0, 0).id, username: 'РыжийКот09' },
			awarded_by: { id: '01890000-0000-7000-8000-000000000002', username: 'ЛовкийСтраж12' },
			can_cancel: true
		},
		{
			id: '01890000-0000-7000-8000-000000000302',
			amount: 10,
			message: 'Викторина по Гибли',
			created_at: minutesAgo(40),
			cancelled_at: null,
			user: { id: questPlayer(2, 0).id, username: 'НочнойФилин88' },
			awarded_by: { id: '01890000-0000-7000-8000-000000000002', username: 'ЛовкийСтраж12' },
			can_cancel: false
		},
		{
			id: '01890000-0000-7000-8000-000000000303',
			amount: 50,
			message: 'Косплей-челлендж',
			created_at: minutesAgo(55),
			cancelled_at: minutesAgo(50),
			user: { id: questPlayer(5, 0).id, username: 'ОгненныйРамен21' },
			awarded_by: { id: '01890000-0000-7000-8000-000000000002', username: 'ЛовкийСтраж12' },
			can_cancel: false
		}
	]
};

/** The public config with the quest switched on. */
export function questConfig(): Handlers {
	const now = Date.now();
	const day = 24 * 60 * 60 * 1000;
	return {
		'GET /config': json<PublicConfigDto>({
			festival_start: new Date(now - day).toISOString(),
			festival_end: new Date(now + day).toISOString(),
			quest_enabled: true,
			quest_max_award: 100
		})
	};
}
