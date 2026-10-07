import type {
	GetVotingNominationOutput,
	NotificationDto,
	ScheduleEventFullDto,
	SubscriptionFullDto
} from '../../src/lib/api/generated';

// The demo festival behind the README gallery: the acts and nominations of the
// backend's demo seed (seed_demo_data.py), so the gallery and the README hero
// show one programme. Blocks are numbered sections, as at the real festival.

const MINUTE_MS = 60_000;

type Act = [title: string, block: string | null, nomination: string | null, duration: number];

const ACTS: Act[] = [
	['Торжественное открытие фестиваля', null, null, 900],
	['Хацунэ Мику — Vocaloid', 'Блок 1', 'Одиночное дефиле', 180],
	['Эдвард Элрик — Стальной алхимик', 'Блок 1', 'Одиночное дефиле', 180],
	['Сейлор Мун — Сейлор Мун', 'Блок 1', 'Одиночное дефиле', 180],
	['Тандзиро Камадо — Клинок, рассекающий демонов', 'Блок 1', 'Одиночное дефиле', 180],
	['Перерыв', null, null, 900],
	['Команда 7 — Наруто', 'Блок 2', 'Групповое дефиле', 300],
	['Отряд разведки — Атака титанов', 'Блок 2', 'Групповое дефиле', 300],
	['Класс 1-А — Моя геройская академия', 'Блок 2', 'Групповое дефиле', 300],
	['Караоке-баттл', 'Блок 3', 'Караоке', 1800],
	['Награждение и закрытие', null, null, 1200]
];

const CURRENT_NUMBER = 3;

export const schedule: ScheduleEventFullDto[] = ACTS.map(
	([title, block, nomination, duration], index) => ({
		id: `event-${index + 1}`,
		number: index + 1,
		title,
		duration,
		order: index + 1,
		is_current: index + 1 === CURRENT_NUMBER,
		is_skipped: false,
		nomination_title: nomination,
		block_title: block,
		queue: index + 1
	})
);

function subscription(number: number, counter: number): SubscriptionFullDto {
	const event = schedule.find((row) => row.number === number);
	if (!event) throw new Error(`No act №${number} in the gallery schedule`);
	return {
		id: `subscription-${number}`,
		user_id: 'gallery-visitor',
		counter,
		event: {
			id: event.id,
			number: event.number,
			title: event.title,
			order: event.order,
			queue: event.queue
		}
	};
}

export const subscriptions: SubscriptionFullDto[] = [subscription(5, 2), subscription(8, 3)];

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
	body: string
): NotificationDto {
	const createdAt = new Date(Date.now() - minutesAgo * MINUTE_MS).toISOString();
	return {
		id: `notification-${minutesAgo}`,
		user_id: 'gallery-visitor',
		title,
		body,
		type,
		path: null,
		mailing_id: null,
		created_at: createdAt,
		seen_at: createdAt
	};
}

export const notifications: NotificationDto[] = [
	notification(
		34,
		'schedule_subscription',
		'Уведомление о подписке',
		'До начала выступления <b>№005 «Тандзиро Камадо — Клинок, рассекающий демонов»</b> осталось <b>2 выступления</b>'
	),
	notification(
		35,
		'schedule_change',
		'На сцене',
		'<b>Сейчас:</b> №003 <b>Эдвард Элрик — Стальной алхимик</b>\n<b>Затем:</b> №004 Сейлор Мун — Сейлор Мун'
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
