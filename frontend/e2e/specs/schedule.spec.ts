import type { ScheduleDto } from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, test } from '../fixtures';

const schedule: ScheduleDto['entries'] = [
	{ type: 'block_start', id: 'block-1', title: 'Блок 1' },
	...[1, 2].map((number) => ({
		type: 'event' as const,
		id: `event-${number}`,
		number,
		title: `Выступление ${number}`,
		duration_seconds: 180,
		is_skipped: false,
		nomination_title: 'Одиночное дефиле',
		position: number
	}))
];

test.describe('schedule', { tag: '@critical' }, () => {
	test('keeps the scope selected when the pressed option is tapped again', async ({
		page,
		api
	}) => {
		api.use({
			...loggedInAs(),
			'GET /schedule': json({ current_event_id: null, entries: schedule }),
			'GET /schedule/subscriptions': json({
				subscriptions: [
					{
						id: 'subscription-1',
						lead_minutes: 10,
						event: { id: 'event-1', number: 1, title: 'Выступление 1', position: 1 }
					}
				]
			})
		});
		await page.goto('/schedule');

		const all = page.getByRole('radio', { name: 'Все' });
		const subscribed = page.getByRole('radio', { name: 'Мои подписки' });

		await subscribed.click();
		await expect(subscribed).toBeChecked();
		await expect(page.getByText('Выступление 2')).toBeHidden();

		await subscribed.click();
		await expect(subscribed).toBeChecked();
		await expect(all).not.toBeChecked();
		await expect(page.getByText('Выступление 2')).toBeHidden();
	});

	test('toggles every-act announcements from the schedule by tapping the title', async ({
		page,
		api
	}) => {
		let patched: unknown;
		api.use({
			...loggedInAs(),
			'GET /schedule': json({ current_event_id: null, entries: schedule }),
			'PATCH /me/settings': (route) => {
				patched = route.request().postDataJSON() as unknown;
				return json({});
			}
		});
		await page.goto('/schedule');
		await page.getByRole('button', { name: 'Настроить уведомления' }).click();

		const allAnnouncements = page.getByRole('switch', { name: 'Все анонсы', exact: true });
		await expect(allAnnouncements).toBeChecked();

		await page.getByText('Все анонсы', { exact: true }).click();

		await expect(allAnnouncements).not.toBeChecked();
		await expect.poll(() => patched).toEqual({ receive_all_announcements: false });
		await expect(page.getByText('Настройки сохранены')).toHaveCount(0);
	});
});
