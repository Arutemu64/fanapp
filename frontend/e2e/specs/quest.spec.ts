import type {
	AwardQuestPointsInput,
	FindQuestPlayersOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, test } from '../fixtures';
import { QUEST, QUEST_AWARDS, QUEST_HISTORY, questConfig, questPlayer } from '../mocks/quest';

const volunteer = () =>
	loggedInAs({ role: 'volunteer', username: 'ЛовкийСтраж12', permissions: ['quest:award'] });

test.describe('quest', { tag: '@critical' }, () => {
	test('a player sees their score, code and place', async ({ page, api }) => {
		api.use({
			...questConfig(),
			...loggedInAs(),
			'GET /quest': json(QUEST),
			'GET /quest/history': json(QUEST_HISTORY)
		});

		await page.goto('/profile');
		await expect(page.getByRole('link', { name: /Квест/ })).toContainText('35 баллов');

		await page.getByRole('link', { name: /Квест/ }).click();
		await expect(page.locator('dl')).toContainText(/Баллы\s*35/);
		await expect(page.locator('dl')).toContainText(/Место\s*23/);
		await expect(page.getByRole('img', { name: 'QR-код игрока @ЛунныйЛис07' })).toBeVisible();

		await page.getByRole('tab', { name: 'Лидеры' }).click();
		await expect(page.getByRole('img', { name: 'QR-код игрока @ЛунныйЛис07' })).toHaveCount(0);
		// The top ten, then the player's own row below the gap.
		await expect(page.getByRole('listitem')).toHaveCount(11);
		await expect(page.locator('li[aria-current="true"]')).toContainText('@ЛунныйЛис07');
	});

	test('a failed score load shows its retry on the badge tab', async ({ page, api }) => {
		api.use({
			...questConfig(),
			...loggedInAs(),
			'GET /quest': json({ detail: 'Ошибка' }, 500),
			'GET /quest/history': json(QUEST_HISTORY)
		});

		await page.goto('/profile/quest');
		const badge = page.getByRole('tabpanel', { name: 'Бейдж' });
		await expect(badge.getByRole('img', { name: 'QR-код игрока @ЛунныйЛис07' })).toBeVisible();
		await expect(badge.getByRole('button', { name: 'Попробовать снова' })).toBeVisible();
	});

	test('offline, the saved score and history stay on screen', async ({ page, api }) => {
		api.use({
			...questConfig(),
			...loggedInAs(),
			'GET /quest': json(QUEST),
			'GET /quest/history': json(QUEST_HISTORY)
		});
		await page.clock.install();
		await page.goto('/profile/quest');
		const badge = page.getByRole('tabpanel', { name: 'Бейдж' });
		await expect(badge.locator('dl')).toContainText(/Баллы\s*35/);

		// Dispatched by hand, as in offline.spec.ts: context.setOffline would also fail
		// the build's chunk loads, and the aborted health check keeps the probes down.
		api.use({ 'GET /debug/health': (route) => route.abort() });
		await page.evaluate(() => window.dispatchEvent(new Event('offline')));

		await expect(badge.getByText(/Синхронизировано сегодня/)).toBeVisible();
		await expect(badge.locator('dl')).toContainText(/Баллы\s*35/);

		await page.getByRole('tab', { name: 'Лидеры' }).click();
		const leaderboard = page.getByRole('tabpanel', { name: 'Лидеры' });
		// A fresh copy gets a quiet line; past half an hour the standings have likely
		// moved, and the notice turns into the warning.
		await expect(leaderboard.getByText(/Обновлено сегодня/)).toBeVisible();
		await expect(leaderboard.getByText('Показаны сохранённые баллы и места.')).toHaveCount(0);
		await page.clock.fastForward('31:00');
		await expect(leaderboard.getByText(/Показаны сохранённые баллы и места\./)).toBeVisible();
		await expect(leaderboard.locator('li[aria-current="true"]')).toContainText('@ЛунныйЛис07');

		await page.getByRole('tab', { name: 'История' }).click();
		const history = page.getByRole('tabpanel', { name: 'История' });
		await expect(history.getByRole('listitem')).toHaveCount(3);
	});

	test('a player sees the awards they received', async ({ page, api }) => {
		api.use({
			...questConfig(),
			...loggedInAs(),
			'GET /quest': json(QUEST),
			'GET /quest/history': json(QUEST_HISTORY)
		});

		await page.goto('/profile/quest');
		await page.getByRole('tab', { name: 'История' }).click();

		const panel = page.getByRole('tabpanel', { name: 'История' });
		await expect(panel.getByRole('listitem')).toHaveCount(3);
		await expect(panel.getByRole('listitem').first()).toContainText('Косплей-фотозона');
		await expect(panel.getByRole('listitem').last()).toContainText('Отменено');
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
		await page.getByLabel('Или найди по имени пользователя').fill('Рыж');
		await page.getByRole('button', { name: /@РыжийКот09/ }).click();
		await page.getByLabel('Баллы').fill('15');
		await page.getByLabel('За что').fill('Викторина');
		await page.getByRole('button', { name: 'Начислить' }).click();

		await expect(page.getByText('@РыжийКот09: +15 баллов')).toBeVisible();
		expect(awarded).toMatchObject({ user_number: player.number, amount: 15, message: 'Викторина' });

		// Back at the picker with focus on the scan button, and the next player starts
		// from the same award: a station hands out one task over and over.
		await expect(page.getByRole('button', { name: 'Сканировать код игрока' })).toBeFocused();
		await page.getByLabel('Или найди по имени пользователя').fill('Рыж');
		await page.getByRole('button', { name: /@РыжийКот09/ }).click();
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
		await page.getByLabel('Или найди по имени пользователя').fill('Рыж');
		await page.getByRole('button', { name: /@РыжийКот09/ }).click();
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
		await page.getByLabel('Или найди по имени пользователя').fill('Рыж');
		await page.getByRole('button', { name: /@РыжийКот09/ }).click();
		await page.getByLabel('Баллы').fill('15');
		await page.getByLabel('За что').fill('Викторина');
		await page.getByRole('button', { name: 'Начислить' }).click();

		await expect(page.getByLabel('За что')).toBeFocused();
		await expect(page.getByLabel('За что')).toHaveAttribute('aria-invalid', 'true');
	});
});
