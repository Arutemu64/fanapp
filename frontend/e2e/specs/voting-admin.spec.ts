import type { Route } from '@playwright/test';

import type {
	GetVotingDashboardOutput,
	UpdateNominationData,
	VotingDashboardNominationDto
} from '../../src/lib/api/generated/types.gen';

import { expect, json, organizer, problem, test } from '../fixtures';

const SOLO: VotingDashboardNominationDto = {
	id: '01890000-0000-7000-8000-0000000000c1',
	code: 'A1',
	title: 'Косплей-соло',
	is_votable: true,
	total_votes: 12,
	leader: {
		participant_id: '01890000-0000-7000-8000-0000000000d1',
		title: 'Рем — Re:Zero',
		votes_count: 7
	}
};

const KARAOKE: VotingDashboardNominationDto = {
	id: '01890000-0000-7000-8000-0000000000c2',
	code: 'B2',
	title: 'Караоке',
	is_votable: false,
	total_votes: 0,
	leader: null
};

function dashboard(nominations: VotingDashboardNominationDto[]): GetVotingDashboardOutput {
	return { voting_starts_at: null, voting_ends_at: null, contest_pool_size: 4, nominations };
}

test.describe('organizer voting tool', () => {
	test('switches a nomination into voting', async ({ page, api }) => {
		let karaoke = KARAOKE;
		const patches: UpdateNominationData['body'][] = [];
		api.use({
			...organizer(),
			'GET /voting/dashboard': () => json(dashboard([SOLO, karaoke])),
			[`PATCH /voting/nominations/${KARAOKE.id}`]: (route: Route) => {
				const body = route.request().postDataJSON() as UpdateNominationData['body'];
				patches.push(body);
				karaoke = { ...karaoke, is_votable: body.is_votable ?? karaoke.is_votable };
				return { status: 204 };
			}
		});
		await page.goto('/tools/voting');

		const karaokeSwitch = page.getByRole('switch', { name: 'Караоке' });
		await expect(page.getByRole('switch', { name: 'Косплей-соло' })).toBeChecked();
		await expect(karaokeSwitch).not.toBeChecked();

		await karaokeSwitch.click();

		await expect(karaokeSwitch).toBeChecked();
		await expect(karaokeSwitch).toBeEnabled();
		expect(patches).toEqual([{ is_votable: true }]);
	});

	test('a failed switch goes back and says why', async ({ page, api }) => {
		api.use({
			...organizer(),
			'GET /voting/dashboard': json(dashboard([SOLO])),
			[`PATCH /voting/nominations/${SOLO.id}`]: problem('NOMINATION_NOT_FOUND', 404)
		});
		await page.goto('/tools/voting');

		const soloSwitch = page.getByRole('switch', { name: 'Косплей-соло' });
		await soloSwitch.click();

		await expect(page.getByText('Не удалось изменить номинацию')).toBeVisible();
		await expect(soloSwitch).toBeChecked();
	});
});
