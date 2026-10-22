import type { GetScheduleOutput } from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, test } from '../fixtures';

const schedule: GetScheduleOutput['schedule'] = [
	{ type: 'block_start', id: 'block-1', title: 'Блок 1', order: 0 },
	...[1, 2].map((number) => ({
		type: 'event' as const,
		id: `event-${number}`,
		number,
		title: `Выступление ${number}`,
		duration: 180,
		order: number,
		is_current: false,
		is_skipped: false,
		nomination_title: 'Одиночное дефиле',
		position: number
	}))
];

test.describe('schedule', { tag: '@critical' }, () => {
	// A single-select toggle group clears its value when the pressed item is tapped
	// again; the page must keep one scope selected and the list filtered to match.
	test('keeps the scope selected when the pressed option is tapped again', async ({
		page,
		api
	}) => {
		api.use({
			...loggedInAs(),
			'GET /schedule': json({ schedule }),
			'GET /schedule/subscriptions': json({
				subscriptions: [
					{
						id: 'subscription-1',
						user_id: 'user',
						lead_minutes: 10,
						event: { id: 'event-1', number: 1, title: 'Выступление 1', order: 1, position: 1 }
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
			'GET /schedule': json({ schedule }),
			'PATCH /me/settings': (route) => {
				patched = route.request().postDataJSON() as unknown;
				return json({});
			}
		});
		await page.goto('/schedule');
		await page.getByRole('button', { name: 'Настроить уведомления' }).click();

		// The switch is named by its visible title alone (WCAG 2.5.3).
		const allAnnouncements = page.getByRole('switch', { name: 'Все анонсы', exact: true });
		await expect(allAnnouncements).toBeChecked();

		await page.getByText('Все анонсы', { exact: true }).click();

		await expect(allAnnouncements).not.toBeChecked();
		await expect.poll(() => patched).toEqual({ receive_all_announcements: false });
		await expect(page.getByText('Настройки сохранены')).toHaveCount(0);
	});
});
