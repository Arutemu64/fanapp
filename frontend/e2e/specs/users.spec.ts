import type {
	ListUsersOutput,
	UserDetailsDto,
	UserListItemDto
} from '../../src/lib/api/generated/types.gen';

import { expect, json, organizer, test } from '../fixtures';

const ANNA: UserListItemDto = {
	id: '01890000-0000-7000-8000-0000000000a1',
	username: 'anna_cosplay',
	role: 'participant',
	email: 'anna@example.com',
	ticket_number: 'FAN-ABC123',
	created_at: '2026-10-10T12:00:00Z'
};

const BORIS: UserListItemDto = {
	id: '01890000-0000-7000-8000-0000000000b2',
	username: 'boris',
	role: 'visitor',
	email: null,
	ticket_number: null,
	created_at: '2026-10-09T12:00:00Z'
};

const ANNA_DETAILS: UserDetailsDto = {
	...ANNA,
	social_links: [],
	permissions: ['feedback:read']
};

test.describe('organizer user directory', () => {
	test('filters the list through the URL and loads more', async ({ page, api }) => {
		const listRequests: URLSearchParams[] = [];
		api.use({
			...organizer(),
			'GET /users/': (route) => {
				const params = new URL(route.request().url()).searchParams;
				listRequests.push(params);
				if (params.get('role') === 'participant') {
					return json<ListUsersOutput>({ users: [ANNA], total: 1, next_cursor: null });
				}
				if (params.get('cursor') === 'next') {
					return json<ListUsersOutput>({ users: [BORIS], total: 2, next_cursor: null });
				}
				return json<ListUsersOutput>({ users: [ANNA], total: 2, next_cursor: 'next' });
			},
			// SvelteKit preloads a row's card when the pointer passes over its link.
			[`GET /users/${BORIS.id}`]: json<UserDetailsDto>({
				...BORIS,
				social_links: [],
				permissions: []
			})
		});
		await page.goto('/tools/users');

		await expect(page.getByRole('link', { name: /anna_cosplay/ })).toBeVisible();
		await page.getByRole('button', { name: 'Показать ещё' }).click();
		await expect(page.getByRole('link', { name: /boris/ })).toBeVisible();

		await page.getByRole('button', { name: 'Роль' }).click();
		await page.getByRole('option', { name: 'Участник' }).click();

		await expect(page).toHaveURL(/role=participant/);
		// Scoped to <main>: the shell's connection banner is a status region too.
		await expect(page.getByRole('main').getByRole('status')).toHaveText('1 пользователь');
		await expect(page.getByRole('link', { name: /boris/ })).toBeHidden();
		expect(listRequests.at(-1)?.get('role')).toBe('participant');
		expect(api.unmatched).toEqual([]);
	});

	test('a superuser grants a permission from the user card', async ({ page, api }) => {
		let details = ANNA_DETAILS;
		let grants = 0;
		api.use({
			...organizer(),
			[`GET /users/${ANNA.id}`]: () => json<UserDetailsDto>(details),
			// The client percent-encodes the colon in the path segment.
			[`PUT /users/${ANNA.id}/permissions/users%3Aread`]: () => {
				grants += 1;
				details = { ...details, permissions: [...details.permissions, 'users:read'] };
				return { status: 204, body: '' };
			}
		});
		await page.goto(`/tools/users/${ANNA.id}`);

		const usersRead = page.getByRole('switch', { name: 'Просмотр пользователей' });
		await expect(usersRead).not.toBeChecked();
		await usersRead.click();

		await expect(usersRead).toBeChecked();
		expect(grants).toBe(1);
		expect(api.unmatched).toEqual([]);
	});

	test('an organizer unlinks a ticket and is told the role stays', async ({ page, api }) => {
		let details = ANNA_DETAILS;
		api.use({
			...organizer(),
			[`GET /users/${ANNA.id}`]: () => json<UserDetailsDto>(details),
			[`DELETE /users/${ANNA.id}/ticket`]: () => {
				details = { ...details, ticket_number: null };
				return { status: 204, body: '' };
			}
		});
		await page.goto(`/tools/users/${ANNA.id}`);

		await page.getByRole('button', { name: 'Отвязать билет' }).click();
		await page.getByRole('alertdialog').getByRole('button', { name: 'Отвязать' }).click();

		await expect(
			page.getByText(
				'Билет отвязан, голоса удалены. Роль не менялась — если нужно, смени её вручную.'
			)
		).toBeVisible();
		await expect(page.getByRole('button', { name: 'Отвязать билет' })).toBeHidden();
		expect(api.unmatched).toEqual([]);
	});
});
