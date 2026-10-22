import type {
	GetScheduleOutput,
	GetVotingStateOutput,
	PublicConfigDto,
	UnreadNotificationsCountOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, test } from '../fixtures';
import { json } from '../mocks/api';
import { loggedInAs } from '../mocks/personas';

test.describe('offline', { tag: '@critical' }, () => {
	test('voting shows the online-only state when the network is down', async ({ page, api }) => {
		// Voting is uncached and online-only, so a dead network must yield the honest
		// "online only" state, not a generic error. Simulate the dead network by
		// aborting its reads — `context.setOffline` can't, because a mocked route
		// still fulfils under it.
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

		// The app trusts an `offline` event at once. Dispatched by hand rather than via
		// context.setOffline, which would also fail the build's own chunk loads (and a
		// mocked route still fulfils under it); the aborted health check keeps the
		// app's probes from recovering under the test.
		api.use({ 'GET /debug/health': (route) => route.abort() });
		await page.evaluate(() => window.dispatchEvent(new Event('offline')));
		await expect(page.getByRole('status').getByText('Нет связи с сервером')).toBeAttached();

		// The strip holds for at least 4s, so the button is still there even if the
		// background poll happens to win the race to the healthy endpoint.
		api.use({ 'GET /debug/health': json({ status: 'healthy' }) });
		await page.getByRole('button', { name: 'Повторить' }).click();

		// Shown once the offline wording has had its minimum time on screen.
		await expect(page.getByRole('status').getByText('Связь восстановлена')).toBeAttached({
			timeout: 10_000
		});
		await expect(page.getByRole('button', { name: 'Повторить' })).toHaveCount(0);
	});

	test('after reconnecting, the banner says it is updating until the screen has reloaded', async ({
		page,
		api
	}) => {
		// Every API response marks the backend reachable, so a first-load response
		// still on its way into the page when the `offline` event fires flips the app
		// straight back online, and the banner never offers «Повторить». The heading
		// renders before Home's data does, so wait for something each of Home's
		// queries puts on screen instead: the act on stage (/config + /schedule/),
		// the voting card (/voting/status) and the guest's account step (/me/).
		const hour = 3_600_000;
		api.use({
			'GET /config': json<PublicConfigDto>({
				festival_start: new Date(Date.now() - hour).toISOString(),
				festival_end: new Date(Date.now() + 24 * hour).toISOString(),
				quest_enabled: false,
				quest_max_award: 100,
				schedule_changeover_seconds: 30
			}),
			'GET /schedule': json<GetScheduleOutput>({
				schedule: [
					{
						type: 'event',
						id: 'event-1',
						number: 1,
						title: 'Одиночное дефиле',
						duration: 300,
						order: 1,
						is_current: true,
						is_skipped: false,
						nomination_title: null,
						position: 1
					}
				]
			}),
			'GET /voting/status': json<GetVotingStateOutput>({
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

		// Past the 60s staleTime, so reconnecting refetches what Home shows, and past
		// the offline wording's minimum time on screen.
		await page.clock.fastForward('01:05');

		// The installed clock keeps running after the fast-forward, so the 3s recovery
		// poll can reach a healthy endpoint before the click and take «Повторить»
		// away. Holding the health check until the click is made keeps the button.
		let reconnect = () => {};
		const reconnected = new Promise<void>((resolve) => (reconnect = resolve));
		// Hold one of Home's refetches open to watch the catch-up state.
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
		// A boot or warm-up response the page handles after the `offline` event marks
		// the backend reachable again, so let the signed-in warm-up land first.
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

		// Should a late response still flip the app online, the send gets no answer
		// and pauses once the probe's confirm window runs out: slower, same outcome.
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
			'GET /schedule': json({ schedule: [] }),
			'PATCH /me/settings': () => {
				patched = true;
				return json({});
			}
		});
		await page.goto('/schedule');
		await page.getByRole('button', { name: 'Настроить уведомления' }).click();
		const allAnnouncements = page.getByRole('switch', { name: 'Все анонсы', exact: true });
		await expect(allAnnouncements).toBeChecked();
		// Every API response the app handles marks the backend reachable, and the
		// switch renders before the bell's unread count has answered: handled after
		// the `offline` event below, it would flip the app back online. Waiting for
		// the request to finish isn't enough on WebKit, where the page can handle the
		// response later still; the count in the bell's name shows it has been handled.
		await expect(
			page.getByRole('link', { name: 'Открыть уведомления, непрочитанных: 1' })
		).toBeVisible();

		api.use({ 'GET /debug/health': (route) => route.abort() });
		await page.evaluate(() => window.dispatchEvent(new Event('offline')));
		await expect(allAnnouncements).toHaveAttribute('aria-disabled', 'true');

		// Dimmed, not disabled: it still takes focus and the press, and says why nothing
		// happens. Driven from the keyboard because Playwright won't click (or click the
		// label of) an aria-disabled control.
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
		// The identity check runs before the API interceptors exist, so only the root
		// load's own probe tells the protected guard that a failed /me/ means
		// "offline" rather than "guest".
		api.use({
			'GET /me': (route) => route.abort(),
			'GET /debug/health': (route) => route.abort()
		});
		await page.goto('/notifications');

		// The device still reports a network, so the probe sits out its 5s offline
		// confirm window before giving a verdict.
		await expect(page.getByRole('main').getByText('Нет связи с сервером')).toBeVisible({
			timeout: 10_000
		});
		await expect(page).toHaveURL('/notifications');
	});

	test('a pending offline logout outlives a cache that still holds the user', async ({
		page,
		api
	}) => {
		// The session cookie is still valid until the queued logout reaches the server,
		// so /me/ keeps answering with the user.
		api.use({ ...loggedInAs(), 'POST /auth/logout': json({}) });
		await page.goto('/notifications');
		await expect(page.getByRole('heading', { name: 'Уведомления' })).toBeVisible();

		// The persister saves on a throttle, so wait until the user is on disk
		// (idb-keyval's default store, under `QUERY_CACHE_KEY` in queryPersister.ts).
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

		// What an offline logout leaves when the app closes before the next save.
		await page.evaluate(() => localStorage.setItem('fanfan:pending-logout', '1'));
		await page.reload();

		await expect(page).toHaveURL(/\/login\?next=%2Fnotifications$/);
	});
});
