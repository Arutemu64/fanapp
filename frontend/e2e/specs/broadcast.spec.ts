import type { ListBroadcastsOutput, MailingDto } from '../../src/lib/api/generated/types.gen';

import { expect, json, organizer, test } from '../fixtures';

const BODY = 'Скоро начнётся церемония открытия на главной сцене';

const FINISHED: MailingDto = {
	id: '01890000-0000-7000-8000-0000000000b1',
	status: 'finished',
	created_by: { id: '01890000-0000-7000-8000-000000000001', username: 'ЯркийФеникс7' },
	body: BODY,
	roles: ['visitor'],
	total_count: 10,
	created_at: new Date().toISOString()
};

test.describe('broadcast history', { tag: '@critical' }, () => {
	test('organizer sees a sent broadcast and can recall it', async ({ page, api }) => {
		api.use(organizer());
		api.use({
			'GET /notifications/broadcast': json<ListBroadcastsOutput>({
				next_cursor: null,
				mailings: [FINISHED]
			}),
			[`POST /notifications/broadcast/${FINISHED.id}/cancel`]: json({}, 204)
		});

		await page.goto('/tools/broadcast');

		await expect(page.getByRole('heading', { name: 'История рассылок' })).toBeVisible();
		await expect(page.getByText(BODY)).toBeVisible();
		await expect(page.getByText('Отправлена', { exact: true })).toBeVisible();
		await expect(page.getByText('10 получателей', { exact: false })).toBeVisible();

		// A finished broadcast is stored, not necessarily delivered, so it can still
		// be recalled. After the recall, the feed reloads (invalidate) — return the mailing cancelled.
		api.use({
			'GET /notifications/broadcast': json<ListBroadcastsOutput>({
				next_cursor: null,
				mailings: [{ ...FINISHED, status: 'cancelled' }]
			})
		});
		await page.getByRole('button', { name: 'Отозвать', exact: true }).click();
		// The recall is confirmed first: what a channel delivered stays delivered.
		const dialog = page.getByRole('alertdialog', { name: 'Отозвать рассылку?' });
		await expect(dialog.getByText('отозвать не получится', { exact: false })).toBeVisible();
		await dialog.getByRole('button', { name: 'Отозвать рассылку' }).click();
		await expect(dialog).toBeHidden();

		// Match the status badge exactly: the success toast that fires on recall reads
		// "Рассылка отозвана", which a substring match also catches — two hits trip
		// strict mode once the toast and the reloaded badge briefly coexist.
		await expect(page.getByText('Отозвана', { exact: true })).toBeVisible();
		// The recall action is gone for a cancelled mailing.
		await expect(page.getByRole('button', { name: 'Отозвать', exact: true })).toHaveCount(0);
	});

	test('shows the empty state when nothing has been sent', async ({ page, api }) => {
		api.use(organizer());
		// Baseline has no broadcast handler; mock an empty history explicitly.
		api.use({
			'GET /notifications/broadcast': json<ListBroadcastsOutput>({
				next_cursor: null,
				mailings: []
			})
		});

		await page.goto('/tools/broadcast');

		await expect(page.getByText('Пока ничего не отправлено')).toBeVisible();
	});
});
