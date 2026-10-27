import type {
	ListTicketsOutput,
	SetTCloudEventRolesInput,
	SyncSourceStatusDto,
	TCloudEventRolesOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, json, organizer, test } from '../fixtures';

const HOLDER_ID = '01890000-0000-7000-8000-0000000000c1';

const TICKETS: ListTicketsOutput = {
	total: 2,
	next_cursor: null,
	tickets: [
		{
			id: '01890000-0000-7000-8000-0000000000d1',
			barcode: 'FAN-ABCD-1234',
			role: 'participant',
			used_by: { id: HOLDER_ID, username: 'ЛунныйКот42' },
			from_ticketscloud: false,
			revoked_at: null,
			created_at: new Date().toISOString()
		},
		{
			id: '01890000-0000-7000-8000-0000000000d2',
			barcode: '7700112233',
			role: 'visitor',
			used_by: null,
			from_ticketscloud: true,
			revoked_at: new Date().toISOString(),
			created_at: new Date().toISOString()
		}
	]
};

const SOURCES: SyncSourceStatusDto[] = [
	{ source: 'cosplay2', available: true, last_run: null },
	{ source: 'tcloud', available: true, last_run: null }
];

test.describe('tickets tool', () => {
	test('lists tickets with the user who linked each', async ({ page, api }) => {
		api.use(organizer());
		api.use({
			'GET /tickets': json<ListTicketsOutput>(TICKETS),
			'GET /tickets/tcloud-event-roles': json<TCloudEventRolesOutput>({
				available: true,
				event_roles: []
			}),
			'GET /sync/sources': json<SyncSourceStatusDto[]>(SOURCES)
		});

		await page.goto('/tools/tickets');

		await expect(page.getByText('2 билета')).toBeVisible();
		await expect(page.getByText('FAN-ABCD-1234')).toBeVisible();
		await expect(page.getByRole('link', { name: 'ЛунныйКот42' })).toHaveAttribute(
			'href',
			`/tools/users/${HOLDER_ID}`
		);
		await expect(page.getByText('Возврат', { exact: true })).toBeVisible();
	});

	test('saves the TicketsCloud event roles', async ({ page, api }) => {
		let saved: SetTCloudEventRolesInput | null = null;
		api.use(organizer());
		api.use({
			'GET /tickets': json<ListTicketsOutput>({ total: 0, next_cursor: null, tickets: [] }),
			'GET /tickets/tcloud-event-roles': json<TCloudEventRolesOutput>({
				available: true,
				event_roles: [{ event_id: 'event-volunteers', role: 'volunteer' }]
			}),
			'GET /sync/sources': json<SyncSourceStatusDto[]>(SOURCES),
			'PUT /tickets/tcloud-event-roles': (route) => {
				saved = route.request().postDataJSON() as SetTCloudEventRolesInput;
				return { status: 204 };
			}
		});

		await page.goto('/tools/tickets');
		await page.getByRole('tab', { name: 'TicketsCloud' }).click();

		await expect(page.getByRole('heading', { name: 'TicketsCloud' })).toBeVisible();

		await page.getByRole('button', { name: 'Добавить мероприятие' }).click();
		await page.getByRole('textbox', { name: 'ID мероприятия 2' }).fill('event-cosplay');
		await page.getByRole('button', { name: 'Сохранить' }).click();

		await expect(page.getByText('Роли сохранены')).toBeVisible();
		expect(saved).toEqual({
			event_roles: [
				{ event_id: 'event-volunteers', role: 'volunteer' },
				{ event_id: 'event-cosplay', role: 'participant' }
			]
		});
	});
});
