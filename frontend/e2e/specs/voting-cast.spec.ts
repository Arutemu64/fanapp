import type { ApiSchemas } from '../fixtures';

import { expect, json, loggedInAs, test } from '../fixtures';

const NOMINATION_CODE = 'best-cosplay';
const PARTICIPANT_ID = '01890000-0000-7000-8000-0000000000c1';
const VOTE_ID = '01890000-0000-7000-8000-0000000000d1';

const OPEN: ApiSchemas['GetVotingStateOutput'] = {
	can_vote: true,
	status: 'open',
	voting_start: null,
	voting_end: null
};

// The nomination detail as the backend would return it before and after the vote.
// The page refetches after casting (invalidate 'app:voting:nomination'), so the
// second read must carry the persisted ballot for the UI to settle into its
// "your vote" state.
function nomination(voted: boolean): ApiSchemas['GetVotingNominationOutput'] {
	return {
		id: '01890000-0000-7000-8000-0000000000b1',
		code: NOMINATION_CODE,
		title: 'Лучший косплей',
		works_url: null,
		participants_count: 1,
		user_vote: voted ? { id: VOTE_ID, participant_id: PARTICIPANT_ID } : null,
		participants: [
			{
				id: PARTICIPANT_ID,
				title: 'Косплей на Аи-тян',
				voting_number: 1,
				votes_count: voted ? 1 : 0,
				user_vote: voted ? { id: VOTE_ID } : null
			}
		]
	};
}

test.describe('voting — casting a ballot', { tag: '@critical' }, () => {
	test('casts a vote and reflects it after the refetch', async ({ page, api }) => {
		api.use(loggedInAs());
		api.use({
			'GET /voting/status': json(OPEN),
			// One key serves both the initial load and the post-vote refetch; branch on
			// whether the vote has landed to hand back the updated ballot.
			'GET /voting/nominations/best-cosplay': () =>
				json(nomination(api.countCalls('POST /voting/votes') > 0)),
			'POST /voting/votes': json<ApiSchemas['AddVoteOutput']>({ vote_id: VOTE_ID }, 201)
		});

		await page.goto('/voting/best-cosplay');

		const voteButton = page.getByRole('button', { name: 'Голосовать за Косплей на Аи-тян' });
		await expect(voteButton).toBeVisible();
		await voteButton.click();

		// The success toast confirms the POST was accepted...
		await expect(page.getByText('Голос учтён')).toBeVisible();
		// ...and the refetched card settles into the persisted "your vote" state.
		await expect(page.getByText('Твой голос')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Отменить голос' })).toBeVisible();

		expect(api.countCalls('POST /voting/votes')).toBe(1);
		expect(api.unmatched).toEqual([]);
	});
});
