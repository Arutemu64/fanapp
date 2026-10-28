import { expect, json, test } from '../fixtures';

test.describe('guide articles', () => {
	test('a row on Home opens its article', async ({ page }) => {
		await page.goto('/');

		await page.getByRole('link', { name: /Ярмарка/ }).click();

		await expect(page).toHaveURL('/guide/fair');
		await expect(page.getByText('Почти 500', { exact: false })).toBeVisible();
	});

	test('«Важное» leads with the entry rules, and the hero links the venue to maps', async ({
		page
	}) => {
		await page.goto('/');

		await expect(page.getByRole('link', { name: /ДК ГАЗ/ })).toHaveAttribute(
			'href',
			/yandex\.ru\/maps/
		);
		await page.getByRole('link', { name: /Вход и правила/ }).click();

		await expect(page).toHaveURL('/guide/entry');
		await expect(page.getByRole('heading', { name: 'Досмотр на входе' })).toBeVisible();
	});

	test('the back arrow leads Home even when the article is opened directly', async ({ page }) => {
		await page.goto('/guide/fair');

		await page.getByRole('link', { name: 'На главную', exact: true }).click();

		await expect(page).toHaveURL('/');
	});

	test('the Home hero spells out the date and start time from the saved festival settings', async ({
		page,
		api
	}) => {
		api.use({
			'GET /config': json({
				festival_starts_at: '2027-04-01T09:00:00+03:00',
				festival_ends_at: '2027-04-01T19:00:00+03:00',
				quest_enabled: false,
				quest_max_award: 100,
				schedule_changeover_seconds: 30
			})
		});

		await page.goto('/');

		await expect(page.getByText('1 апреля 2027, четверг', { exact: true })).toBeVisible();
		await expect(page.getByText('Вход с 10:30 · начало в 09:00', { exact: true })).toBeVisible();
	});

	test('after the festival Home keeps only the ways to stay in touch', async ({ page, api }) => {
		api.use({
			'GET /config': json({
				festival_starts_at: '2020-04-01T09:00:00+03:00',
				festival_ends_at: '2020-04-01T19:00:00+03:00',
				quest_enabled: false,
				quest_max_award: 100,
				schedule_changeover_seconds: 30
			})
		});

		await page.goto('/');

		await expect(page.getByRole('heading', { name: 'Фестиваль завершён' })).toBeVisible();
		await expect(page.getByRole('link', { name: /Telegram/ })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Чем заняться' })).toHaveCount(0);
	});

	test('an unknown article shows the error page', async ({ page }) => {
		await page.goto('/guide/no-such-article');

		await expect(page.getByRole('heading', { name: 'Страница не найдена' })).toBeVisible();
	});
});
