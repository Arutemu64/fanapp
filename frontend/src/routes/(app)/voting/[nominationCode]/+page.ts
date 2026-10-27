import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { getApiErrorCode, isConnectionFailure, throwApiError } from '#lib/api/errors.js';
import { getVotingNominationOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { m } from '#lib/paraglide/messages.js';
import { isReachable } from '#lib/services/reachability.js';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, parent }) => {
	const back = { href: 'voting', label: m.voting_back_to_nominations() } satisfies BackTarget;

	if (!isReachable()) return { title: m.nav_voting(), back };

	const { queryClient } = await parent();
	const nomination = await queryForLoad(queryClient, {
		...getVotingNominationOptions({ path: { nomination_code: params.nominationCode } }),
		staleTime: 'static'
	}).catch((apiError: unknown) => {
		if (getApiErrorCode(apiError) === 'NOMINATION_NOT_FOUND') {
			error(404, m.voting_nomination_not_found());
		}
		if (isConnectionFailure(apiError)) return undefined;
		return throwApiError(apiError, m.voting_nomination_load_failed());
	});

	return { title: nomination?.title ?? m.nav_voting(), back };
};
