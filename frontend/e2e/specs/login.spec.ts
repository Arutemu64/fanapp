import type { Page } from '@playwright/test';

import type {
	CaptchaChallengeDto,
	OAuthProvidersOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, json, test } from '../fixtures';

// A real deterministic ALTCHA challenge at the API's own difficulty, pinned to
// counter 750. The browser never checks the signatures (only the API does), and
// with no expiresAt it never goes stale. Nothing here is secret: keyPrefix is the
// public difficulty target every client sees, which gitleaks' entropy rule
// mistakes for an API key.
const CAPTCHA_CHALLENGE = {
	parameters: {
		algorithm: 'PBKDF2/SHA-256',
		cost: 5000,
		keyLength: 32,
		keyPrefix: '687afc72cc05a84c0d4dd5ded62b86ed', // gitleaks:allow
		nonce: '1d8fa1307004e5bf19a024e955438c3e',
		salt: 'eb91ea0efa8c99bcbf08a8cd17d95e62',
		keySignature: 'cf27fc8a37aca2adec2a919739effb46e4873301fd81de1b3b0f6ab0612487f6'
	},
	signature: 'f43d43a355226d46303581c2f1b09278be5b5e1482d291efd5c799387c6f058e'
};

async function openEmailStep(page: Page) {
	await page.goto('/login');
	await page.getByRole('button', { name: 'Войти по почте' }).click();
	return page.getByLabel('Почта');
}

test.describe('email login', { tag: '@critical' }, () => {
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
	});

	test('solves the captcha in the background and sends its proof with the request', async ({
		page,
		api
	}) => {
		let sentToken: unknown;
		api.use({
			'GET /auth/captcha-challenge': json<CaptchaChallengeDto>({ challenge: CAPTCHA_CHALLENGE }),
			'POST /auth/request-login-code': (route) => {
				sentToken = (route.request().postDataJSON() as { captcha_token: unknown }).captcha_token;
				return json(null);
			}
		});
		const email = await openEmailStep(page);
		await email.fill('ann@example.com');
		await email.press('Enter');
		await expect(page.getByLabel('Код подтверждения')).toBeFocused();

		// The token is the ALTCHA payload: the challenge as issued plus the one
		// solution its prefix pins.
		expect(typeof sentToken).toBe('string');
		const payload = JSON.parse(atob(sentToken as string)) as {
			challenge: unknown;
			solution: { counter: number; derivedKey: string };
		};
		expect(payload.challenge).toEqual(CAPTCHA_CHALLENGE);
		expect(payload.solution.counter).toBe(750);
		expect(payload.solution.derivedKey.startsWith(CAPTCHA_CHALLENGE.parameters.keyPrefix)).toBe(
			true
		);
	});

	test('a rate-limited captcha says when to retry', async ({ page, api }) => {
		// Venue NAT can put many visitors behind one IP, so the challenge cap is
		// reachable; its retry_after must survive the captcha layer.
		api.use({
			'GET /auth/captcha-challenge': json(
				{
					code: 'TOO_MANY_LOGIN_CODE_REQUESTS',
					retry_after: 42
				},
				429
			)
		});
		const email = await openEmailStep(page);
		await email.fill('ann@example.com');
		await email.press('Enter');

		await expect(page.getByRole('alert')).toHaveText('Попробуй ещё раз через 42 сек.');
	});

	test('the on-screen back returns focus to the control that opened the step', async ({ page }) => {
		await openEmailStep(page);
		await page.getByRole('button', { name: 'Назад' }).click();

		await expect(page.getByRole('button', { name: 'Войти по почте' })).toBeFocused();
	});

	test('a code that lands after leaving the step does not reopen the flow', async ({
		page,
		api
	}) => {
		let deliver = () => {};
		const delivered = new Promise<void>((resolve) => (deliver = resolve));
		let requested = () => {};
		const requestSeen = new Promise<void>((resolve) => (requested = resolve));
		api.use({
			'POST /auth/request-login-code': async () => {
				requested();
				await delivered;
				return json(null);
			}
		});
		const email = await openEmailStep(page);
		await email.fill('ann@example.com');
		await email.press('Enter');
		await requestSeen;

		await page.getByRole('button', { name: 'Назад' }).click();
		await expect(page.getByRole('button', { name: 'Войти по почте' })).toBeVisible();
		// Listen before releasing it, so a fast response can't slip past the wait.
		const lateResponse = page.waitForResponse('**/auth/request-login-code');
		deliver();
		await lateResponse;
		await expect(page.getByLabel('Код подтверждения')).toHaveCount(0);
		await expect(page.getByRole('button', { name: 'Войти по почте' })).toBeVisible();
	});

	test('offers the guest exit on the options screen only', async ({ page }) => {
		await page.goto('/login');
		const leave = page.getByRole('button', { name: 'Продолжить без входа' });
		await expect(leave).toBeVisible();

		await page.getByRole('button', { name: 'Войти по почте' }).click();
		await expect(page.getByLabel('Почта')).toBeFocused();
		await expect(leave).toHaveCount(0);
	});

	test('a rejected code is cleared and announced, with focus kept in the field', async ({
		page,
		api
	}) => {
		api.use({
			'POST /auth/request-login-code': json(null),
			'POST /auth/login-with-code': json({ code: 'INVALID_OTP_CODE' }, 400)
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
	'the options, email and code steps have no WCAG A/AA violations',
	{ tag: '@a11y' },
	async ({ page, api, expectAccessible }) => {
		api.use({
			'GET /auth/oauth/providers': json<OAuthProvidersOutput>({ providers: ['vk', 'telegram'] }),
			'POST /auth/request-login-code': json(null)
		});
		await page.goto('/login');
		await expect(page.getByRole('link', { name: 'Войти через VK ID' })).toBeVisible();
		await expectAccessible();

		await page.getByRole('button', { name: 'Войти по почте' }).click();
		const email = page.getByLabel('Почта');
		await email.press('Enter');
		await expect(page.getByRole('alert')).toBeVisible();
		await expectAccessible();

		await email.fill('ann@example.com');
		await email.press('Enter');
		await expect(page.getByLabel('Код подтверждения')).toBeFocused();
		// The address sits inside a tag of the markup message.
		await expect(page.getByText('Код отправлен на ann@example.com.')).toBeVisible();
		await expectAccessible();
	}
);
