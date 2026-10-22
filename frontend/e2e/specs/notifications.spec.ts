import type {
	ListUserNotificationsOutput,
	NotificationDto,
	UnreadNotificationsCountOutput
} from '../../src/lib/api/generated/types.gen';

import { emitSse, expect, json, loggedInAs, test } from '../fixtures';

const UNREAD: NotificationDto = {
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
			'GET /notifications': json<ListUserNotificationsOutput>({
				next_cursor: null,
				notifications: [UNREAD]
			}),
			// Opening the page marks the on-screen unread items read (mark-on-open).
			'POST /notifications/mark-read': json({})
		});

		await page.goto('/notifications');

		const item = page.getByRole('listitem').filter({ hasText: 'Скоро твоё событие' });
		await expect(item).toBeVisible();
		await expect(page.getByText(UNREAD.body)).toBeVisible();

		// The mark-on-open request fired for the one unread item.
		await expect.poll(() => api.countCalls('POST /notifications/mark-read')).toBe(1);

		// Marked read on the server, but still flagged new for this visit — the
		// cue for what the user hasn't seen yet must not vanish on arrival.
		await expect(item.getByRole('link', { name: 'Новое: Скоро твоё событие' })).toBeVisible();
		await expect(page.getByText('Новых: 1')).toBeVisible();
	});

	test('offers mark-all when unread items sit beyond the loaded page', async ({ page, api }) => {
		let unreadCount = 30;
		api.use(loggedInAs());
		api.use({
			'GET /notifications': json<ListUserNotificationsOutput>({
				next_cursor: null,
				notifications: [UNREAD]
			}),
			'POST /notifications/mark-read': json({}),
			'GET /notifications/unread-count': () =>
				json<UnreadNotificationsCountOutput>({ count: unreadCount }),
			'POST /notifications/mark-all-read': () => {
				unreadCount = 0;
				return json({});
			}
		});

		await page.goto('/notifications');

		const markAll = page.getByRole('button', { name: 'Прочитать все' });
		await markAll.click();

		await expect(markAll).toBeHidden();
		expect(api.countCalls('POST /notifications/mark-all-read')).toBe(1);
	});

	test('does not link an organizer mailing back to the feed it sits in', async ({ page, api }) => {
		api.use(loggedInAs());
		api.use({
			'GET /notifications': json<ListUserNotificationsOutput>({
				next_cursor: null,
				notifications: [
					{
						...UNREAD,
						id: '01890000-0000-7000-8000-0000000000e2',
						title: 'Рассылка от организаторов',
						body: 'Гардероб работает до 21:00. <a href="https://example.com/map">Схема</a>',
						type: 'broadcast',
						path: '/notifications',
						seen_at: new Date().toISOString()
					}
				]
			})
		});

		await page.goto('/notifications');

		const item = page.getByRole('listitem').filter({ hasText: 'Рассылка от организаторов' });
		await expect(item).toBeVisible();
		// Only the organizer's own link in the body — no card link wrapping it.
		await expect(item.getByRole('link')).toHaveCount(1);
		await expect(item.getByRole('link', { name: 'Схема' })).toBeVisible();
	});

	test('the bell opens the feed on every screen size', async ({ page, api }) => {
		api.use(loggedInAs());
		api.use({
			'GET /notifications/unread-count': json<UnreadNotificationsCountOutput>({ count: 3 })
		});

		await page.goto('/');
		await page.getByRole('link', { name: 'Открыть уведомления, непрочитанных: 3' }).click();

		await expect(page).toHaveURL(/\/notifications$/);
	});

	test('pages by cursor and refetches later pages from the fresh first page', async ({
		page,
		api
	}) => {
		const seenAt = new Date().toISOString();
		const first: NotificationDto = { ...UNREAD, seen_at: seenAt };
		const older: NotificationDto = {
			...UNREAD,
			id: '01890000-0000-7000-8000-0000000000e3',
			title: 'Со второй страницы',
			seen_at: seenAt
		};
		const newest: NotificationDto = {
			...UNREAD,
			id: '01890000-0000-7000-8000-0000000000e4',
			title: 'Только что пришло',
			seen_at: seenAt
		};
		let firstPage = [first];
		let firstPageCursor = 'cursor-after-first';
		const requests: URLSearchParams[] = [];
		api.use(loggedInAs());
		api.use({
			'GET /notifications': (route) => {
				const params = new URL(route.request().url()).searchParams;
				requests.push(params);
				if (params.get('cursor') === null) {
					return json<ListUserNotificationsOutput>({
						next_cursor: firstPageCursor,
						notifications: firstPage
					});
				}
				return json<ListUserNotificationsOutput>({ next_cursor: null, notifications: [older] });
			}
		});
		const item = (title: string) => page.getByRole('listitem').filter({ hasText: title });

		await page.goto('/notifications');
		await expect(item(first.title)).toBeVisible();
		const loadMore = page.getByRole('button', { name: 'Показать ещё' });
		await loadMore.click();

		await expect(item(older.title)).toBeVisible();
		await expect(loadMore).toBeHidden();
		expect(requests.map((params) => [params.get('limit'), params.get('cursor')])).toEqual([
			['20', null],
			['20', 'cursor-after-first']
		]);

		// A new arrival refetches every loaded page. The second must follow the
		// refreshed first page's cursor, not the one it was first loaded with, or
		// loaded pages could overlap — the feeds no longer dedupe.
		firstPage = [newest, first];
		firstPageCursor = 'cursor-after-refetch';
		await emitSse(page, 'notification_created', newest);

		await expect(item(newest.title)).toBeVisible();
		await expect.poll(() => requests.at(-1)?.get('cursor')).toBe('cursor-after-refetch');
		await expect(item(older.title)).toHaveCount(1);
	});

	test('shows the empty state when there are no notifications', async ({ page, api }) => {
		api.use(loggedInAs());
		// Baseline already returns an empty feed; navigate a logged-in user to it.
		await page.goto('/notifications');

		await expect(page.getByText('Уведомлений пока нет')).toBeVisible();
		await expect(page.getByRole('link', { name: 'Настроить уведомления' })).toHaveAttribute(
			'href',
			'/profile/notifications'
		);
		// Nothing unread → no mark-read call.
		expect(api.countCalls('POST /notifications/mark-read')).toBe(0);
	});
});
