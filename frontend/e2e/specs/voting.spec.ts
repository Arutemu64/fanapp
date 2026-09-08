import type { ApiSchemas } from '../fixtures';

import { expect, json, test } from '../fixtures';

const CLOSED: ApiSchemas['GetVotingStateOutput'] = {
	can_vote: false,
	status: 'disabled',
	voting_start: null,
	voting_end: null
};

const OPEN: ApiSchemas['GetVotingStateOutput'] = {
	can_vote: true,
	status: 'open',
	voting_start: null,
	voting_end: null
};

const NOMINATION: ApiSchemas['NominationVotingDTO'] = {
	id: '01890000-0000-7000-8000-0000000000aa',
	code: 'best-cosplay',
	title: 'Лучший косплей',
	works_url: null,
	participants_count: 3,
	user_vote: null
};

test.describe('voting', () => {
	test('shows the closed banner when voting is disabled', async ({ page, api }) => {
		api.use({
			'GET /voting/status': json(CLOSED),
			'GET /voting/nominations': json<ApiSchemas['ListVotingNominationsOutput']>({
				nominations: []
			})
		});
		await page.goto('/voting');

		await expect(page.getByText('Голосование сейчас закрыто.')).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});

	test('lists nominations when voting is open', async ({ page, api }) => {
		api.use({
			'GET /voting/status': json(OPEN),
			'GET /voting/nominations': json<ApiSchemas['ListVotingNominationsOutput']>({
				nominations: [NOMINATION]
			})
		});
		await page.goto('/voting');

		await expect(page.getByText('Лучший косплей')).toBeVisible();
		// Open voting hides the status banner.
		await expect(page.getByText('Голосование сейчас закрыто.')).toHaveCount(0);
		expect(api.unmatched).toEqual([]);
	});
});
