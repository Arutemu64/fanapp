import assert from 'node:assert/strict';

import type { ScheduleDto } from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, organizer, test } from '../fixtures';

function scheduleWithEvents(eventCount: number): ScheduleDto['entries'] {
	return [
		{ type: 'block_start', id: 'block-1', title: 'Блок 1' },
		...Array.from({ length: eventCount }, (_, index) => {
			const number = index + 1;
			return {
				type: 'event' as const,
				id: `event-${number}`,
				number,
				title: `Выступление ${number}`,
				duration_seconds: 180,
				is_skipped: false,
				nomination_title: 'Одиночное дефиле',
				position: number
			};
		})
	];
}

const schedule = scheduleWithEvents(2);

test.describe('schedule', { tag: '@critical' }, () => {
	test('shows the program while identity is loading and adds staff controls once it arrives', async ({
		page,
		api
	}) => {
		const identity = Promise.withResolvers<undefined>();
		api.use({
			...organizer(),
			'GET /schedule': json({ current_event_id: null, entries: schedule })
		});
		await page.route('**/api/me', async (route) => {
			await identity.promise;
			await route.fallback();
		});

		const now = Date.now();
		await page.clock.install({ time: now });
		// Hold the boot deadline while checking that the public request starts.
		await page.clock.pauseAt(now + 60_000);
		const scheduleResponse = page.waitForResponse('**/api/schedule');
		const changes = page.getByRole('link', { name: 'Изменения программы' });
		try {
			await page.goto('/schedule', { waitUntil: 'commit' });
			await scheduleResponse;
			await page.clock.resume();
			await expect(page.getByRole('heading', { name: 'Выступление 1' })).toBeVisible();
			await expect(changes).toHaveCount(0);
			expect(api.countCalls('GET /schedule/subscriptions')).toBe(0);
		} finally {
			identity.resolve(undefined);
		}
		await expect(changes).toHaveAttribute('href', '/schedule/changes');
	});

	test('jumps to the current event when a search hides it', async ({ page, api }) => {
		api.use({
			'GET /schedule': json({ current_event_id: 'event-1', entries: schedule })
		});
		await page.goto('/schedule');

		const search = page.getByRole('searchbox', { name: 'Поиск по программе' });
		const currentEvent = page.getByRole('heading', { name: 'Выступление 1', exact: true });
		const jump = page.getByRole('button', {
			name: /Сейчас на сцене.*Выступление 1/,
			includeHidden: true
		});
		const bar = jump.locator('..');

		await expect(currentEvent).toBeInViewport();
		await expect(bar).toHaveCSS('opacity', '0');
		await search.fill('Выступление 2');
		await expect(currentEvent).toHaveCount(0);
		await expect(bar).toHaveCSS('opacity', '1');

		await jump.click();
		await expect(search).toHaveValue('');
		await expect(currentEvent).toBeInViewport();
		await expect(bar).toHaveCSS('opacity', '0');
	});

	test('scrolls to the current event when its row is off-screen', async ({ page, api }) => {
		api.use({
			'GET /schedule': json({ current_event_id: 'event-12', entries: scheduleWithEvents(16) })
		});
		await page.goto('/schedule');

		const currentEvent = page.getByRole('heading', { name: 'Выступление 12', exact: true });
		const jump = page.getByRole('button', {
			name: /Сейчас на сцене.*Выступление 12/,
			includeHidden: true
		});
		const bar = jump.locator('..');

		await expect(currentEvent).toBeAttached();
		await expect(currentEvent).not.toBeInViewport();
		await expect(jump).toBeInViewport({ ratio: 1 });
		await expect(bar).toHaveCSS('opacity', '1');

		// Tap without Playwright scrolling the sticky button into view first.
		const bounds = await jump.boundingBox();
		assert(bounds, 'The current-event jump button has no bounding box');
		await page.touchscreen.tap(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
		await expect(currentEvent).toBeInViewport();
		await expect(bar).toHaveCSS('opacity', '0');
	});

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
