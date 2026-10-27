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
			'GET /notifications/broadcasts': json<ListBroadcastsOutput>({
				next_cursor: null,
				mailings: [FINISHED]
			}),
			[`POST /notifications/broadcasts/${FINISHED.id}/cancel`]: json({}, 204)
		});

		await page.goto('/tools/broadcast');

		await expect(page.getByRole('heading', { name: 'История рассылок' })).toBeVisible();
		await expect(page.getByText(BODY)).toBeVisible();
		await expect(page.getByText('Отправлена', { exact: true })).toBeVisible();
		await expect(page.getByText('10 получателей', { exact: false })).toBeVisible();

		api.use({
			'GET /notifications/broadcasts': json<ListBroadcastsOutput>({
				next_cursor: null,
				mailings: [{ ...FINISHED, status: 'cancelled' }]
			})
		});
		await page.getByRole('button', { name: 'Отозвать', exact: true }).click();
		const dialog = page.getByRole('alertdialog', { name: 'Отозвать рассылку?' });
		await expect(dialog.getByText('отозвать не получится', { exact: false })).toBeVisible();
		await dialog.getByRole('button', { name: 'Отозвать рассылку' }).click();
		await expect(dialog).toBeHidden();

		await expect(page.getByText('Отозвана', { exact: true })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Отозвать', exact: true })).toHaveCount(0);
	});

	test('shows the empty state when nothing has been sent', async ({ page, api }) => {
		api.use(organizer());
		api.use({
			'GET /notifications/broadcasts': json<ListBroadcastsOutput>({
				next_cursor: null,
				mailings: []
			})
		});

		await page.goto('/tools/broadcast');

		await expect(page.getByText('Пока ничего не отправлено')).toBeVisible();
	});
});
