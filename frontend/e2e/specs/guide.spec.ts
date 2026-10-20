import { expect, json, test } from '../fixtures';

test.describe('guide on Home', () => {
	test('a Home row opens its article', async ({ page }) => {
		await page.goto('/');

		await page.getByRole('link', { name: /Ярмарка/ }).click();

		await expect(page).toHaveURL('/guide/fair');
		await expect(page.getByText('Почти 500', { exact: false })).toBeVisible();
	});

	test('the back arrow leads Home even when the article is opened directly', async ({ page }) => {
		await page.goto('/guide/fair');

		await page.getByRole('link', { name: 'Назад на главную', exact: true }).click();

		await expect(page).toHaveURL('/');
	});

	test('the old guide address lands on Home', async ({ page }) => {
		await page.goto('/guide');

		await expect(page).toHaveURL('/');
		await expect(page.getByRole('heading', { name: 'Чем заняться' })).toBeVisible();
	});

	test('the date and start time follow the saved festival settings', async ({ page, api }) => {
		api.use({
			'GET /config': json({
				festival_start: '2027-04-01T09:00:00+03:00',
				festival_end: '2027-04-01T19:00:00+03:00',
				quest_enabled: false,
				quest_max_award: 100
			})
		});

		// The hero lists them while it counts down, so the clock sits before the start.
		await page.clock.setFixedTime(new Date('2027-03-01T12:00:00+03:00'));
		await page.goto('/');

		await expect(page.getByText('1 апреля 2027, четверг')).toBeVisible();
		await expect(page.getByText('Начало в 09:00')).toBeVisible();
	});

	test('an unknown article shows the error page', async ({ page }) => {
		await page.goto('/guide/no-such-article');

		await expect(page.getByRole('heading', { name: 'Страница не найдена' })).toBeVisible();
	});
});
