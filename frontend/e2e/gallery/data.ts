import type {
	GetQuestOutput,
	GetVotingNominationOutput,
	LeaderboardEntryDto,
	NotificationDto,
	ScheduleEntryDto,
	ScheduleEventFullDto,
	SubscriptionFullDto
} from '../../src/lib/api/generated/types.gen';

export const GALLERY_NOW = new Date('2026-10-17T15:00:00+03:00');

const MINUTE_MS = 60_000;

type Act = [title: string, block: string | null, nomination: string | null, duration: number];

const ACTS: Act[] = [
	['Торжественное открытие фестиваля', null, null, 900],
	['Хацунэ Мику — Vocaloid', 'Блок 1', 'Одиночное дефиле', 180],
	['Эдвард Элрик — Стальной алхимик', 'Блок 1', 'Одиночное дефиле', 180],
	['Сейлор Мун — Сейлор Мун', 'Блок 1', 'Одиночное дефиле', 180],
	['Тандзиро Камадо — Клинок, рассекающий демонов', 'Блок 1', 'Одиночное дефиле', 180],
	['Перерыв', 'Блок 1', null, 900],
	['Команда 7 — Наруто', 'Блок 2', 'Групповое дефиле', 300],
	['Отряд разведки — Атака титанов', 'Блок 2', 'Групповое дефиле', 300],
	['Класс 1-А — Моя геройская академия', 'Блок 2', 'Групповое дефиле', 300],
	['Караоке-баттл', 'Блок 3', 'Караоке', 1800],
	['Награждение и закрытие', 'Блок 3', null, 1200]
];

const CURRENT_NUMBER = 3;

const schedule: ScheduleEventFullDto[] = ACTS.map(([title, , nomination, duration], index) => ({
	type: 'event',
	id: `event-${index + 1}`,
	number: index + 1,
	title,
	duration_seconds: duration,
	is_skipped: false,
	nomination_title: nomination,
	position: index + 1
}));

export const currentEventId = `event-${CURRENT_NUMBER}`;

export const scheduleEntries: ScheduleEntryDto[] = schedule.flatMap((event, index) => {
	const block = ACTS[index]?.[1] ?? null;
	const previousBlock = ACTS[index - 1]?.[1] ?? null;
	if (block === null || block === previousBlock) return [event];
	const blockStart: ScheduleEntryDto = {
		type: 'block_start',
		id: `block-${index + 1}`,
		title: block
	};
	return [blockStart, event];
});

function subscription(number: number, leadMinutes: number): SubscriptionFullDto {
	const event = schedule.find((row) => row.number === number);
	if (!event) throw new Error(`No act №${number} in the gallery schedule`);
	return {
		id: `subscription-${number}`,
		lead_minutes: leadMinutes,
		event: {
			id: event.id,
			number: event.number,
			title: event.title,
			position: event.position
		}
	};
}

export const subscriptions: SubscriptionFullDto[] = [subscription(5, 15), subscription(8, 30)];

const SINGLE_DEFILE_VOTES: readonly number[] = [8, 18, 23, 12];

export const singleDefile: GetVotingNominationOutput = {
	id: 'nomination-single',
	code: 'single',
	title: 'Одиночное дефиле',
	works_url: null,
	participants_count: 4,
	user_vote: { id: 'vote-1', participant_id: 'participant-2' },
	participants: schedule.slice(1, 5).map((event, index) => ({
		id: `participant-${index + 1}`,
		title: event.title,
		voting_number: index + 1,
		votes_count: SINGLE_DEFILE_VOTES[index] ?? 0,
		user_vote: index === 1 ? { id: 'vote-1' } : null
	}))
};

function notification(
	minutesAgo: number,
	type: NotificationDto['type'],
	title: string,
	body: string,
	overrides: Partial<NotificationDto> = {}
): NotificationDto {
	const createdAt = new Date(GALLERY_NOW.getTime() - minutesAgo * MINUTE_MS).toISOString();
	return {
		id: `notification-${minutesAgo}`,
		title,
		body,
		type,
		path: null,
		mailing_id: null,
		created_at: createdAt,
		seen_at: createdAt,
		...overrides
	};
}

export const notifications: NotificationDto[] = [
	notification(
		34,
		'schedule_subscription',
		'Уведомление о подписке',
		'До начала выступления <b>№005 «Тандзиро Камадо — Клинок, рассекающий демонов»</b> осталось <b>2 выступления</b>',
		{ path: '/schedule', seen_at: null }
	),
	notification(
		35,
		'schedule_change',
		'На сцене',
		'<b>Сейчас:</b> №003 <b>Эдвард Элрик — Стальной алхимик</b>\n<b>Затем:</b> №004 Сейлор Мун — Сейлор Мун',
		{ path: '/schedule', seen_at: null }
	),
	notification(
		60,
		'broadcast',
		'Рассылка от организаторов',
		'Голосование открыто! Выбирайте любимые костюмы до конца дня.'
	),
	notification(
		120,
		'broadcast',
		'Рассылка от организаторов',
		'Гардероб работает до 21:00. Не забудьте забрать вещи после закрытия.'
	)
];

const QUEST_RIVALS = [
	{ username: 'РыжийКот09', points: 185 },
	{ username: 'СонныйСамурай15', points: 160 },
	{ username: 'НочнойФилин88', points: 140 }
];
const QUEST_CHASERS = [
	{ username: 'НеоновыйПилот31', points: 95 },
	{ username: 'ОгненныйРамен21', points: 80 },
	{ username: 'ПушистыйХомяк77', points: 65 }
];

function questEntry(rank: number, username: string, points: number): LeaderboardEntryDto {
	return {
		rank,
		player: {
			id: `01890000-0000-7000-8000-0000000004${String(rank).padStart(2, '0')}`,
			number: 615200 + rank,
			username,
			avatar_seed: `galleryQuest${String(rank).padStart(2, '0')}`,
			points
		}
	};
}

const ownQuestEntry: LeaderboardEntryDto = {
	rank: 4,
	player: {
		id: '01890000-0000-7000-8000-000000000001',
		number: 482913,
		username: 'ПушистыйПингвин42',
		avatar_seed: 'e2eSeedVisitor',
		points: 120
	}
};

export const questStanding: GetQuestOutput = {
	points: 120,
	rank: 4,
	leaderboard_entries: [
		...QUEST_RIVALS.map((rival, index) => questEntry(index + 1, rival.username, rival.points)),
		ownQuestEntry,
		...QUEST_CHASERS.map((chaser, index) => questEntry(index + 5, chaser.username, chaser.points))
	],
	own_entry: null
};
