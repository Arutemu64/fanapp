import type { GetScheduleOutput } from '../../src/lib/api/generated';

import { expect, json, loggedInAs, test } from '../fixtures';

const schedule: GetScheduleOutput['schedule'] = [1, 2].map((number) => ({
	id: `event-${number}`,
	number,
	title: `Выступление ${number}`,
	duration: 180,
	order: number,
	is_current: false,
	is_skipped: false,
	nomination_title: 'Одиночное дефиле',
	block_title: 'Блок 1',
	queue: number
}));

test.describe('schedule', () => {
	// A single-select toggle group clears its value when the pressed item is tapped
	// again; the page must keep one scope selected and the list filtered to match.
	test('keeps the scope selected when the pressed option is tapped again', async ({
		page,
		api
	}) => {
		api.use({
			...loggedInAs(),
			'GET /schedule/': json({ schedule }),
			'GET /schedule/subscriptions/': json({
				subscriptions: [
					{
						id: 'subscription-1',
						user_id: 'user',
						counter: 2,
						event: { id: 'event-1', number: 1, title: 'Выступление 1', order: 1, queue: 1 }
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
		expect(api.unmatched).toEqual([]);
	});
});
