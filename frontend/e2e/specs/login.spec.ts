import type { Page } from '@playwright/test';

import { expect, json, test } from '../fixtures';

async function openEmailStep(page: Page) {
	await page.goto('/login');
	await page.getByRole('button', { name: 'Войти по почте' }).click();
	return page.getByLabel('Эл. почта');
}

test.describe('email login', () => {
	test('validates on submit, not while typing', async ({ page }) => {
		const email = await openEmailStep(page);
		await expect(email).toBeFocused();

		// A half-typed address is not a mistake yet.
		await email.pressSequentially('ann');
		await expect(page.getByRole('alert')).toHaveCount(0);

		await email.press('Enter');
		await expect(page.getByRole('alert')).toHaveText('Введи адрес в формате name@example.com');
		await expect(email).toHaveAttribute('aria-invalid', 'true');
	});

	test('the back gesture steps back through the flow, keeping the address', async ({
		page,
		api
	}) => {
		api.use({ 'POST /auth/request-login-code': json(null) });
		const email = await openEmailStep(page);
		await email.fill('ann@example.com');
		await email.press('Enter');

		const code = page.getByLabel('Код подтверждения');
		await expect(code).toBeFocused();
		await expect(page.getByRole('status')).toContainText('ann@example.com');

		await page.goBack();
		await expect(email).toHaveValue('ann@example.com');
		await expect(email).toBeFocused();

		await page.goBack();
		await expect(page).toHaveURL('/login');
		await expect(page.getByRole('button', { name: 'Войти по почте' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});

	test('the on-screen back returns focus to the control that opened the step', async ({ page }) => {
		await openEmailStep(page);
		await page.getByRole('button', { name: 'Назад' }).click();

		await expect(page.getByRole('button', { name: 'Войти по почте' })).toBeFocused();
	});

	test('a rejected code is cleared and announced, with focus kept in the field', async ({
		page,
		api
	}) => {
		api.use({
			'POST /auth/request-login-code': json(null),
			'POST /auth/login-with-code': json({ code: 'INVALID_OTP_CODE', details: {} }, 400)
		});
		const email = await openEmailStep(page);
		await email.fill('ann@example.com');
		await email.press('Enter');

		const code = page.getByLabel('Код подтверждения');
		await expect(code).toBeFocused();

		// Digits only: a stray letter never reaches the field.
		await code.pressSequentially('a12b3456');

		await expect(page.getByRole('alert')).toHaveText('Неверный или устаревший код');
		await expect(code).toHaveValue('');
		await expect(code).toBeFocused();
		expect(api.unmatched).toEqual([]);
	});
});

test('password login offers the code as the way out', async ({ page }) => {
	const email = await openEmailStep(page);
	await email.fill('ann@example.com');
	await page.getByRole('button', { name: 'Войти с паролем' }).click();

	// The address carries over, so focus lands on the field still to fill.
	await expect(page.getByLabel('Пароль', { exact: true })).toBeFocused();

	await page.getByRole('button', { name: 'Войти по коду без пароля' }).click();
	await expect(email).toHaveValue('ann@example.com');
});

test(
	'the email and code steps have no WCAG A/AA violations',
	{ tag: '@a11y' },
	async ({ page, api, makeAxeBuilder }) => {
		api.use({ 'POST /auth/request-login-code': json(null) });
		const email = await openEmailStep(page);
		await email.press('Enter');
		await expect(page.getByRole('alert')).toBeVisible();
		expect((await makeAxeBuilder().analyze()).violations).toEqual([]);

		await email.fill('ann@example.com');
		await email.press('Enter');
		await expect(page.getByLabel('Код подтверждения')).toBeFocused();
		expect((await makeAxeBuilder().analyze()).violations).toEqual([]);
	}
);
