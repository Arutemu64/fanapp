import { error } from '@sveltejs/kit';

import type { BackTarget } from '#lib/types/navigation.js';

import { getApiErrorCode, isConnectionFailure, throwApiError } from '#lib/api/errors.js';
import { getVotingNominationOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import { queryForLoad } from '#lib/api/index.js';
import { m } from '#lib/paraglide/messages.js';
import { isReachable } from '#lib/services/reachability.js';

import type { PageLoad } from './$types';

const back = { href: 'voting', label: m.voting_nomination_back() } satisfies BackTarget;

export const load: PageLoad = async ({ params, parent }) => {
	// Online-only like the nominations list: the page shows no cached ballot
	// offline, so there is nothing to wait for. 'Голосование' names the navbar.
	if (!isReachable()) return { title: m.nav_voting(), back };

	// The nomination names the navbar, so a first visit waits for it; a revisit
	// answers from the cache and the page refetches it in the background.
	const { queryClient } = await parent();
	const nomination = await queryForLoad(queryClient, {
		...getVotingNominationOptions({ path: { nomination_code: params.nominationCode } }),
		staleTime: 'static'
	}).catch((apiError: unknown) => {
		if (getApiErrorCode(apiError) === 'NOMINATION_NOT_FOUND') {
			error(404, m.voting_nomination_not_found());
		}
		// A request that never got an answer leaves the page to its offline state.
		if (isConnectionFailure(apiError)) return undefined;
		return throwApiError(apiError, undefined, m.voting_nomination_load_failed());
	});

	return { title: nomination?.title ?? m.nav_voting(), back };
};
