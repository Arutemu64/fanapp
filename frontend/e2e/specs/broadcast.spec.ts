import type { ApiSchemas } from '../fixtures';

import { expect, json, organizer, test } from '../fixtures';

const BODY = 'Скоро начнётся церемония открытия на главной сцене';

const SENDING: ApiSchemas['MailingDTO'] = {
	id: '01890000-0000-7000-8000-0000000000b1',
	status: 'sending',
	by_user_id: '01890000-0000-7000-8000-000000000001',
	body: BODY,
	roles: ['visitor'],
	sent_count: 3,
	total_count: 10,
	created_at: new Date().toISOString()
};

test.describe('broadcast history', { tag: '@critical' }, () => {
	test('organizer sees a sent broadcast and can cancel it', async ({ page, api }) => {
		api.use(organizer());
		api.use({
			'GET /notifications/broadcast': json<ApiSchemas['ListBroadcastsOutput']>({
				mailings: [SENDING]
			}),
			[`POST /notifications/broadcast/${SENDING.id}/cancel`]: json({}, 204)
		});

		await page.goto('/tools/broadcast');

		await expect(page.getByRole('heading', { name: 'История рассылок' })).toBeVisible();
		await expect(page.getByText(BODY)).toBeVisible();
		await expect(page.getByText('Отправляется')).toBeVisible();
		await expect(page.getByText('отправлено 3 из 10', { exact: false })).toBeVisible();

		// After cancel, the feed reloads (invalidate) — return the mailing cancelled.
		api.use({
			'GET /notifications/broadcast': json<ApiSchemas['ListBroadcastsOutput']>({
				mailings: [{ ...SENDING, status: 'cancelled' }]
			})
		});
		await page.getByRole('button', { name: 'Отменить' }).click();

		// Match the status badge exactly: the success toast that fires on cancel reads
		// "Рассылка отменена", which a substring match also catches — two hits trip
		// strict mode once the toast and the reloaded badge briefly coexist.
		await expect(page.getByText('Отменена', { exact: true })).toBeVisible();
		// The cancel action is gone for a terminal mailing.
		await expect(page.getByRole('button', { name: 'Отменить' })).toHaveCount(0);
		expect(api.unmatched).toEqual([]);
	});

	test('shows the empty state when nothing has been sent', async ({ page, api }) => {
		api.use(organizer());
		// Baseline has no broadcast handler; mock an empty history explicitly.
		api.use({
			'GET /notifications/broadcast': json<ApiSchemas['ListBroadcastsOutput']>({ mailings: [] })
		});

		await page.goto('/tools/broadcast');

		await expect(page.getByText('Пока ничего не отправлено')).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});
});
