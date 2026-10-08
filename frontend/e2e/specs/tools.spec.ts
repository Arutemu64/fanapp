import type { GetVotingDashboardOutput, OnlineUsersCountOutput } from '../../src/lib/api/generated';

import { expect, json, organizer, test } from '../fixtures';

test.describe('organizer tools', { tag: '@critical' }, () => {
	test('an organizer sees the toolbox', async ({ page, api }) => {
		api.use({
			...organizer(),
			// The hub renders the live online-users card, which polls this endpoint.
			'GET /users/online-count': json<OnlineUsersCountOutput>({ count: 5 })
		});
		await page.goto('/tools');

		await expect(
			page.getByText('Для работы организаторов фестиваля.', { exact: false })
		).toBeVisible();
		// The online-now card renders for every org, above the tool grid.
		await expect(page.getByText('сейчас в приложении')).toBeVisible();
		// A couple of the permission-gated tool cards render for a full-permission org.
		await expect(page.getByRole('link', { name: 'Пользователи' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Синхронизация' })).toBeVisible();

		expect(api.unmatched).toEqual([]);
	});

	test('a guest is bounced to login', async ({ page, api }) => {
		// No persona: the baseline /me/ is a 401 guest, and the protected guard
		// redirects a reachable guest to login, remembering where they were headed.
		await page.goto('/tools');

		await expect(page).toHaveURL(/\/login\?/);
		await expect(page.getByRole('heading', { level: 1, name: 'Вход' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});
});

test.describe('organizer voting tool', { tag: '@critical' }, () => {
	// A device far from the venue: the window must still read and save on the
	// venue clock (Moscow), the one visitors see.
	test.use({ timezoneId: 'Asia/Vladivostok' });

	const DASHBOARD: GetVotingDashboardOutput = {
		voting_start: '2026-08-22T08:00:00Z', // 11:00 in Moscow
		voting_end: '2026-08-23T15:00:00Z', // 18:00 in Moscow
		contest_pool_size: 0,
		nominations: []
	};

	test('edits the window on the venue clock and confirms switching voting off', async ({
		page,
		api
	}) => {
		const patches: unknown[] = [];
		api.use(organizer());
		api.use({
			'GET /voting/dashboard': json(DASHBOARD),
			'PATCH /voting/dashboard': (route) => {
				patches.push(route.request().postDataJSON() as unknown);
				return json({}, 204);
			}
		});

		await page.goto('/tools/voting');

		await expect(page.getByLabel('Начало (МСК)')).toHaveValue('2026-08-22T11:00');
		await expect(page.getByLabel('Конец (МСК)')).toHaveValue('2026-08-23T18:00');

		// An end before the start is caught on the page, under the field.
		await page.getByLabel('Конец (МСК)').fill('2026-08-22T10:00');
		await page.getByRole('button', { name: 'Сохранить' }).click();
		await expect(page.getByText('Конец должен быть позже начала')).toBeVisible();
		expect(patches).toEqual([]);

		await page.getByLabel('Конец (МСК)').fill('2026-08-22T19:30');
		await page.getByRole('button', { name: 'Сохранить' }).click();
		await expect(page.getByText('Период голосования сохранён')).toBeVisible();
		expect(patches.at(-1)).toEqual({
			voting_start: '2026-08-22T08:00:00.000Z',
			voting_end: '2026-08-22T16:30:00.000Z'
		});

		// Switching voting off waits for an explicit confirm.
		await page.getByRole('button', { name: 'Отключить голосование' }).click();
		const dialog = page.getByRole('alertdialog');
		await expect(dialog).toContainText('Отключить голосование?');
		await dialog.getByRole('button', { name: 'Отключить' }).click();

		await expect(page.getByText('Голосование отключено')).toBeVisible();
		expect(patches.at(-1)).toEqual({ voting_start: null, voting_end: null });
		await expect(page.getByLabel('Начало (МСК)')).toHaveValue('');
		await expect(page.getByRole('button', { name: 'Отключить голосование' })).toHaveCount(0);
		expect(api.unmatched).toEqual([]);
	});
});
