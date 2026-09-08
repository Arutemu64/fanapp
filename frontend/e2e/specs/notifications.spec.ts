import type { ApiSchemas } from '../fixtures';

import { expect, json, loggedInAs, test } from '../fixtures';

const UNREAD: ApiSchemas['NotificationDTO'] = {
	id: '01890000-0000-7000-8000-0000000000e1',
	user_id: '01890000-0000-7000-8000-000000000001',
	title: 'Скоро твоё событие',
	body: 'Косплей-дефиле начнётся через 15 минут на главной сцене.',
	type: 'schedule_change',
	path: '/schedule',
	mailing_id: null,
	created_at: new Date().toISOString(),
	seen_at: null
};

test.describe('notifications', { tag: '@critical' }, () => {
	test('renders the feed and marks loaded items read on open', async ({ page, api }) => {
		api.use(loggedInAs());
		api.use({
			'GET /notifications/': json<ApiSchemas['ListUserNotificationOutput']>({
				notifications: [UNREAD]
			}),
			// Opening the page marks the on-screen unread items read (mark-on-open).
			'POST /notifications/mark-read': json({})
		});

		await page.goto('/notifications');

		await expect(page.getByText('Скоро твоё событие')).toBeVisible();
		await expect(page.getByText(UNREAD.body)).toBeVisible();

		// The mark-on-open request fired for the one unread item.
		await expect.poll(() => api.countCalls('POST /notifications/mark-read')).toBe(1);
		expect(api.unmatched).toEqual([]);
	});

	test('shows the empty state when there are no notifications', async ({ page, api }) => {
		api.use(loggedInAs());
		// Baseline already returns an empty feed; navigate a logged-in user to it.
		await page.goto('/notifications');

		await expect(page.getByText('Уведомлений пока нет')).toBeVisible();
		// Nothing unread → no mark-read call.
		expect(api.countCalls('POST /notifications/mark-read')).toBe(0);
		expect(api.unmatched).toEqual([]);
	});
});
