import type {
	GetVotingStatusOutput,
	PublicConfigDto,
	ScheduleDto,
	UnreadNotificationsCountOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, test } from '../fixtures';
import { json } from '../mocks/api';
import { loggedInAs } from '../mocks/personas';

test.describe('offline', { tag: '@critical' }, () => {
	test('voting shows the online-only state when the network is down', async ({ page, api }) => {
		api.use({
			'GET /voting/status': (route) => route.abort(),
			'GET /voting/nominations': (route) => route.abort()
		});
		await page.goto('/voting');

		await expect(page.getByText('Раздел доступен только онлайн')).toBeVisible();
	});

	test('the connection banner re-checks on tap and confirms the recovery', async ({
		page,
		api
	}) => {
		await page.goto('/');
		await expect(page.getByRole('heading', { level: 1, name: 'Главная' })).toBeVisible();

		api.use({ 'GET /debug/health': (route) => route.abort() });
		await page.evaluate(() => window.dispatchEvent(new Event('offline')));
		await expect(page.getByRole('status').getByText('Нет связи с сервером')).toBeAttached();

		api.use({ 'GET /debug/health': json({ status: 'healthy' }) });
		await page.getByRole('button', { name: 'Повторить' }).click();

		await expect(page.getByRole('status').getByText('Связь восстановлена')).toBeAttached({
			timeout: 10_000
		});
		await expect(page.getByRole('button', { name: 'Повторить' })).toHaveCount(0);
	});

	test('after reconnecting, the banner says it is updating until the screen has reloaded', async ({
		page,
		api
	}) => {
		const hour = 3_600_000;
		api.use({
			'GET /config': json<PublicConfigDto>({
				festival_start: new Date(Date.now() - hour).toISOString(),
				festival_end: new Date(Date.now() + 24 * hour).toISOString(),
				quest_enabled: false,
				quest_max_award: 100,
				schedule_changeover_seconds: 30
			}),
			'GET /schedule': json<ScheduleDto>({
				current_event_id: 'event-1',
				schedule: [
					{
						type: 'event',
						id: 'event-1',
						number: 1,
						title: 'Одиночное дефиле',
						duration_seconds: 300,
						is_skipped: false,
						nomination_title: null,
						position: 1
					}
				]
			}),
			'GET /voting/status': json<GetVotingStatusOutput>({
				can_vote: false,
				status: 'not_authenticated',
				voting_start: new Date(Date.now() - hour).toISOString(),
				voting_end: new Date(Date.now() + 24 * hour).toISOString()
			})
		});
		await page.clock.install();
		await page.goto('/');
		await expect(page.getByText('Одиночное дефиле')).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Голосование открыто' })).toBeVisible();
		await expect(page.getByText('Создать аккаунт')).toBeVisible();

		api.use({ 'GET /debug/health': (route) => route.abort() });
		await page.evaluate(() => window.dispatchEvent(new Event('offline')));
		await expect(page.getByRole('status').getByText('Нет связи с сервером')).toBeAttached();

		await page.clock.fastForward('01:05');

		let reconnect = () => {};
		const reconnected = new Promise<void>((resolve) => (reconnect = resolve));
		let release = () => {};
		const released = new Promise<void>((resolve) => (release = resolve));
		api.use({
			'GET /debug/health': async () => {
				await reconnected;
				return json({ status: 'healthy' });
			},
			'GET /voting/status': async () => {
				await released;
				return json({
					can_vote: false,
					status: 'not_authenticated',
					voting_start: null,
					voting_end: null
				});
			}
		});
		await page.getByRole('button', { name: 'Повторить' }).click();
		reconnect();

		await expect(page.getByRole('status').getByText('Обновляем…')).toBeAttached();
		release();
		await expect(page.getByRole('status').getByText('Связь восстановлена')).toBeAttached();
	});

	test('feedback written offline waits in the queue and goes out on reconnect', async ({
		page,
		api
	}) => {
		const sent: unknown[] = [];
		api.use({
			...loggedInAs(),
			'POST /feedback': (route) => {
				sent.push(route.request().postDataJSON());
				return json({ feedback_id: 'feedback-1' }, 201);
			}
		});
		const warmedUp = Promise.all(
			['/notifications', '/schedule/subscriptions'].map((path) =>
				page.waitForResponse((response) => new URL(response.url()).pathname.endsWith(path))
			)
		);
		await page.goto('/feedback');
		const field = page.getByRole('textbox', { name: 'Твоё сообщение' });
		await expect(field).toBeVisible();
		await warmedUp;

		api.use({
			'GET /debug/health': (route) => route.abort(),
			'POST /feedback': (route) => route.abort()
		});
		await page.evaluate(() => window.dispatchEvent(new Event('offline')));
		await expect(page.getByRole('status').getByText('Нет связи с сервером')).toBeAttached();

		await field.fill('Карта зала очень помогла');
		await page.getByRole('button', { name: 'Отправить сообщение' }).click();

		await expect(page.getByText('Отправим, когда появится связь')).toBeVisible({
			timeout: 10_000
		});
		await expect(field).toHaveValue('');
		await expect(page.getByRole('status').getByText('1 действие ждёт отправки')).toBeAttached();
		expect(sent).toEqual([]);

		api.use({
			'GET /debug/health': json({ status: 'healthy' }),
			'POST /feedback': (route) => {
				sent.push(route.request().postDataJSON());
				return json({ feedback_id: 'feedback-1' }, 201);
			}
		});
		await page.getByRole('button', { name: 'Повторить' }).click();

		await expect(page.getByText('Спасибо, сообщение отправлено')).toBeVisible();
		expect(sent).toEqual([{ text: 'Карта зала очень помогла' }]);
	});

	test('an online-only switch explains itself offline instead of saving', async ({ page, api }) => {
		let patched = false;
		api.use({
			...loggedInAs(),
			'GET /notifications/unread-count': json<UnreadNotificationsCountOutput>({ count: 1 }),
			'GET /schedule': json({ current_event_id: null, schedule: [] }),
			'PATCH /me/settings': () => {
				patched = true;
				return json({});
			}
		});
		await page.goto('/schedule');
		await page.getByRole('button', { name: 'Настроить уведомления' }).click();
		const allAnnouncements = page.getByRole('switch', { name: 'Все анонсы', exact: true });
		await expect(allAnnouncements).toBeChecked();
		await expect(
			page.getByRole('link', { name: 'Открыть уведомления, непрочитанных: 1' })
		).toBeVisible();

		api.use({ 'GET /debug/health': (route) => route.abort() });
		await page.evaluate(() => window.dispatchEvent(new Event('offline')));
		await expect(allAnnouncements).toHaveAttribute('aria-disabled', 'true');

		await allAnnouncements.focus();
		await page.keyboard.press('Space');

		await expect(page.getByText('Доступно только онлайн', { exact: true })).toBeVisible();
		await expect(allAnnouncements).toBeChecked();
		expect(patched).toBe(false);
	});

	test('a cold start with no saved identity shows the offline state, not login', async ({
		page,
		api
	}) => {
		api.use({
			'GET /me': (route) => route.abort(),
			'GET /debug/health': (route) => route.abort()
		});
		await page.goto('/notifications');

		await expect(page.getByRole('main').getByText('Нет связи с сервером')).toBeVisible({
			timeout: 10_000
		});
		await expect(page).toHaveURL('/notifications');
	});

	test('a pending offline logout outlives a cache that still holds the user', async ({
		page,
		api
	}) => {
		api.use({ ...loggedInAs(), 'POST /auth/logout': json({}) });
		await page.goto('/notifications');
		await expect(page.getByRole('heading', { name: 'Уведомления' })).toBeVisible();

		await expect
			.poll(() =>
				page.evaluate(
					() =>
						new Promise<string>((resolve) => {
							const open = indexedDB.open('keyval-store');
							open.onsuccess = () => {
								const read = open.result
									.transaction('keyval')
									.objectStore('keyval')
									.get('fanfan-query-cache');
								read.onsuccess = () => resolve(JSON.stringify(read.result ?? ''));
							};
						})
				)
			)
			.toContain('getCurrentUser');

		await page.evaluate(() => localStorage.setItem('fanfan:pending-logout', '1'));
		await page.reload();

		await expect(page).toHaveURL(/\/login\?next=%2Fnotifications$/);
	});
});
