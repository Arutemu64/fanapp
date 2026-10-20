import { expect, test } from '../fixtures';

test.describe('map', () => {
	test('a place picked in the list lights up and is named under the plan', async ({ page }) => {
		await page.goto('/map');
		const row = page.getByRole('button', { name: /Женский туалет/ });

		await row.click();

		await expect(row).toHaveAttribute('aria-pressed', 'true');
		await expect(page.getByRole('status').filter({ hasText: 'Женский туалет' })).toBeVisible();

		await row.click();
		await expect(row).toHaveAttribute('aria-pressed', 'false');
	});

	test('switching floors swaps the plan and its list', async ({ page }) => {
		await page.goto('/map');
		await expect(page.getByRole('img', { name: 'Карта 1 этажа' })).toBeVisible();

		await page.getByRole('radio', { name: '2 и 3 этажи' }).click();

		await expect(page.getByRole('img', { name: 'Карта 2 и 3 этажа' })).toBeVisible();
		await expect(page.getByRole('button', { name: /Just Dance/ })).toBeVisible();
		await expect(page.getByRole('button', { name: /Женский туалет/ })).toHaveCount(0);
	});

	test('tapping a zone lights every zone with its number, and tapping again clears it', async ({
		page
	}) => {
		await page.goto('/map');
		await page.getByRole('radio', { name: '2 и 3 этажи' }).click();
		const plan = page.getByRole('img', { name: 'Карта 2 и 3 этажа' });
		const photoZones = plan.locator('[data-point="7"]');
		await expect(photoZones).toHaveCount(4);

		await photoZones.first().click();

		await expect(plan.locator('[data-selected]')).toHaveCount(4);
		await expect(plan.locator('[data-point="7"][data-selected]')).toHaveCount(4);
		await expect(page.getByRole('status').filter({ hasText: 'Фотозона' })).toBeVisible();
		await expect(page.getByRole('button', { name: /Фотозона/ })).toHaveAttribute(
			'aria-pressed',
			'true'
		);

		await photoZones.last().click();
		await expect(plan.locator('[data-selected]')).toHaveCount(0);
	});

	test('a search finds a place on the other floor and switches the plan there', async ({
		page
	}) => {
		await page.goto('/map');

		await page.getByRole('searchbox', { name: 'Поиск по карте' }).fill('туалет');

		// Both toilets, one per floor, each naming where it is.
		const results = page.getByRole('main').getByRole('listitem');
		await expect(results).toHaveCount(2);
		await expect(page.getByRole('status').filter({ hasText: 'Показано 2 из' })).toBeVisible();

		const mens = page.getByRole('button', { name: /Мужской туалет/ });
		await expect(mens).toContainText('2 и 3 этажи');
		await mens.click();

		await expect(page.getByRole('img', { name: 'Карта 2 и 3 этажа' })).toBeVisible();
		await expect(page.getByRole('radio', { name: '2 и 3 этажи' })).toBeChecked();
		await expect(mens).toHaveAttribute('aria-pressed', 'true');
		await expect(page.getByRole('status').filter({ hasText: 'Мужской туалет' })).toBeVisible();
	});

	test('a search with no match says so, and clearing it brings the list back', async ({ page }) => {
		await page.goto('/map');
		const search = page.getByRole('searchbox', { name: 'Поиск по карте' });

		await search.fill('бассейн');
		await expect(page.getByText('Ничего не нашлось')).toBeVisible();

		await page.getByRole('button', { name: 'Очистить поиск' }).click();
		await expect(search).toHaveValue('');
		await expect(page.getByRole('button', { name: /Женский туалет/ })).toBeVisible();
	});
});
