import type {
	AwardQuestPointsInput,
	FindQuestPlayersOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, test } from '../fixtures';
import { QUEST, QUEST_AWARDS, questConfig, questPlayer } from '../mocks/quest';

const volunteer = () =>
	loggedInAs({ role: 'volunteer', username: 'test_volunteer', permissions: ['quest:award'] });

test.describe('quest', { tag: '@critical' }, () => {
	test('a player sees their score, code and place', async ({ page, api }) => {
		api.use({ ...questConfig(), ...loggedInAs(), 'GET /quest': json(QUEST) });

		await page.goto('/profile');
		await expect(page.getByRole('link', { name: /Квест/ })).toContainText('35 баллов');

		await page.getByRole('link', { name: /Квест/ }).click();
		await expect(page.locator('dl')).toContainText(/Баллы\s*35/);
		await expect(page.locator('dl')).toContainText(/Место\s*23/);
		await expect(page.getByRole('img', { name: 'QR-код игрока @test_visitor' })).toBeVisible();
		// The top ten, then the player's own row below the gap.
		await expect(page.getByRole('listitem')).toHaveCount(11);
		await expect(page.locator('li[aria-current="true"]')).toContainText('@test_visitor');
	});

	test('the quest row is hidden while the quest is off', async ({ page, api }) => {
		api.use(loggedInAs());

		await page.goto('/profile');
		await expect(page.getByRole('link', { name: 'Билет' })).toBeVisible();
		await expect(page.getByRole('link', { name: /Квест/ })).toHaveCount(0);
	});

	test('a volunteer finds a player and awards points', async ({ page, api }) => {
		let awarded: AwardQuestPointsInput | undefined;
		const player = questPlayer(0, 240);
		api.use({
			...questConfig(),
			...volunteer(),
			'GET /quest/awards': json(QUEST_AWARDS),
			'GET /quest/players': json<FindQuestPlayersOutput>({ players: [player] }),
			'POST /quest/awards': (route) => {
				awarded = route.request().postDataJSON() as AwardQuestPointsInput;
				return json({ award_id: awarded.award_id }, 201);
			}
		});

		await page.goto('/tools');
		// A volunteer sees only the tools they hold.
		await expect(page.getByRole('link', { name: /Квест/ })).toBeVisible();
		await expect(page.getByRole('link', { name: /Пользователи/ })).toHaveCount(0);

		await page.getByRole('link', { name: /Квест/ }).click();
		await page.getByLabel('Или найди по имени пользователя').fill('kits');
		await page.getByRole('button', { name: /@kitsune_mika/ }).click();
		await page.getByLabel('Баллы').fill('15');
		await page.getByLabel('За что').fill('Викторина');
		await page.getByRole('button', { name: 'Начислить' }).click();

		await expect(page.getByText('@kitsune_mika: +15 баллов')).toBeVisible();
		expect(awarded).toMatchObject({ user_id: player.id, amount: 15, message: 'Викторина' });

		// Back at the picker with focus on the scan button, and the next player starts
		// from the same award: a station hands out one task over and over.
		await expect(page.getByRole('button', { name: 'Сканировать код игрока' })).toBeFocused();
		await page.getByLabel('Или найди по имени пользователя').fill('kits');
		await page.getByRole('button', { name: /@kitsune_mika/ }).click();
		await expect(page.getByLabel('Баллы')).toHaveValue('15');
		await expect(page.getByLabel('За что')).toHaveValue('Викторина');
	});

	test('an amount above the cap is refused before sending', async ({ page, api }) => {
		api.use({
			...questConfig(),
			...volunteer(),
			'GET /quest/awards': json(QUEST_AWARDS),
			'GET /quest/players': json<FindQuestPlayersOutput>({ players: [questPlayer(0, 240)] })
		});

		await page.goto('/tools/quest');
		await page.getByLabel('Или найди по имени пользователя').fill('kits');
		await page.getByRole('button', { name: /@kitsune_mika/ }).click();
		await page.getByLabel('Баллы').fill('500');
		await page.getByLabel('За что').fill('Опечатка');
		await page.getByRole('button', { name: 'Начислить' }).click();

		await expect(page.getByText('Введи целое число от 1 до 100')).toBeVisible();
		await expect(page.getByLabel('Баллы')).toBeFocused();
		expect(api.countCalls('POST /quest/awards')).toBe(0);
	});

	test('a field the server refuses gets the focus', async ({ page, api }) => {
		api.use({
			...questConfig(),
			...volunteer(),
			'GET /quest/awards': json(QUEST_AWARDS),
			'GET /quest/players': json<FindQuestPlayersOutput>({ players: [questPlayer(0, 240)] }),
			'POST /quest/awards': json(
				{
					code: 'VALIDATION_ERROR',
					details: { errors: [{ loc: ['body', 'message'], type: 'string_too_long' }] }
				},
				422
			)
		});

		await page.goto('/tools/quest');
		await page.getByLabel('Или найди по имени пользователя').fill('kits');
		await page.getByRole('button', { name: /@kitsune_mika/ }).click();
		await page.getByLabel('Баллы').fill('15');
		await page.getByLabel('За что').fill('Викторина');
		await page.getByRole('button', { name: 'Начислить' }).click();

		await expect(page.getByLabel('За что')).toBeFocused();
		await expect(page.getByLabel('За что')).toHaveAttribute('aria-invalid', 'true');
	});
});
