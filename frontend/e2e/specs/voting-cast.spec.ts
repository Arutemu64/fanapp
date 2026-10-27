import type {
	AddVoteOutput,
	GetVotingNominationOutput,
	GetVotingStatusOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, test } from '../fixtures';

const NOMINATION_CODE = 'best-cosplay';
const PARTICIPANT_ID = '01890000-0000-7000-8000-0000000000c1';
const VOTE_ID = '01890000-0000-7000-8000-0000000000d1';

const OPEN: GetVotingStatusOutput = {
	can_vote: true,
	status: 'open',
	voting_start: null,
	voting_end: null
};

function nomination(voted: boolean): GetVotingNominationOutput {
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
			'GET /voting/nominations/best-cosplay': () =>
				json(nomination(api.countCalls('POST /voting/votes') > 0)),
			'POST /voting/votes': json<AddVoteOutput>({ vote_id: VOTE_ID }, 201)
		});

		await page.goto('/voting/best-cosplay');

		const voteButton = page.getByRole('button', { name: 'Голосовать за Косплей на Аи-тян' });
		await expect(voteButton).toBeVisible();
		await voteButton.click();

		await expect(page.getByText('Голос учтён')).toBeVisible();
		await expect(page.getByText('Твой голос')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Отменить голос' })).toBeVisible();

		expect(api.countCalls('POST /voting/votes')).toBe(1);
	});

	test('holds the counted vote until the refetch lands', async ({ page, api }) => {
		let release = () => {};
		const released = new Promise<void>((resolve) => (release = resolve));
		api.use(loggedInAs());
		api.use({
			'GET /voting/status': json(OPEN),
			'GET /voting/nominations/best-cosplay': async () => {
				const voted = api.countCalls('POST /voting/votes') > 0;
				if (voted) await released;
				return json(nomination(voted));
			},
			'POST /voting/votes': json<AddVoteOutput>({ vote_id: VOTE_ID }, 201)
		});

		await page.goto('/voting/best-cosplay');

		const voteButton = page.getByRole('button', { name: 'Голосовать за Косплей на Аи-тян' });
		const voteAnswered = page.waitForResponse('**/voting/votes');
		await voteButton.click();
		await voteAnswered;

		await expect(page.getByText('1 голос', { exact: true })).toBeVisible();
		await expect(voteButton).toBeDisabled();

		release();
		await expect(page.getByText('Твой голос')).toBeVisible();
		await expect(page.getByText('1 голос', { exact: true })).toBeVisible();
		expect(api.countCalls('POST /voting/votes')).toBe(1);
	});
});

test.describe('voting — taking a vote back', { tag: '@critical' }, () => {
	const OTHER_ID = '01890000-0000-7000-8000-0000000000c2';

	function votedNomination(voted: boolean): GetVotingNominationOutput {
		const base = nomination(voted);
		return {
			...base,
			participants_count: 2,
			participants: [
				...base.participants,
				{
					id: OTHER_ID,
					title: 'Косплей на Мику',
					voting_number: 2,
					votes_count: 0,
					user_vote: null
				}
			]
		};
	}

	test('cancels from the notice even when search hides the voted participant', async ({
		page,
		api
	}) => {
		api.use(loggedInAs());
		api.use({
			'GET /voting/status': json(OPEN),
			'GET /voting/nominations/best-cosplay': () =>
				json(votedNomination(api.countCalls(`DELETE /voting/votes/${VOTE_ID}`) === 0)),
			[`DELETE /voting/votes/${VOTE_ID}`]: { status: 204 }
		});

		await page.goto('/voting/best-cosplay');
		await expect(page.getByText('Твой выбор')).toBeVisible();

		await page.getByRole('searchbox', { name: 'Поиск участников в номинации' }).fill('Мику');
		await expect(page.getByText('Показано 1 из 2')).toBeVisible();

		await page.getByRole('button', { name: 'Отменить голос' }).click();

		await expect(page.getByText('Голос отменён')).toBeVisible();
		await expect(page.getByText('Твой выбор')).toHaveCount(0);
		await expect(page.getByRole('button', { name: 'Голосовать за Косплей на Мику' })).toBeVisible();

		expect(api.countCalls(`DELETE /voting/votes/${VOTE_ID}`)).toBe(1);
	});
});
