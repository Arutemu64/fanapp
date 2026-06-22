import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { createApiClient } from '$lib/api';
import { fetchWithCache } from '$lib/utils/offlineCache';
import type { UserSocialAccountDTO } from '$lib/types/user';

type ProfileConnections = {
	socialAccounts: UserSocialAccountDTO[];
};

const TELEGRAM_LINK_ERROR_QUERY_PARAM = 'telegramLinkError';
const TELEGRAM_LINK_ERROR_CODES = [
	'linked_to_another_account',
	'user_already_has_telegram'
] as const;

type TelegramLinkErrorCode = (typeof TELEGRAM_LINK_ERROR_CODES)[number];

function getTelegramLinkErrorCode(url: URL): TelegramLinkErrorCode | null {
	const errorCode = url.searchParams.get(TELEGRAM_LINK_ERROR_QUERY_PARAM);

	if (errorCode && TELEGRAM_LINK_ERROR_CODES.includes(errorCode as TelegramLinkErrorCode)) {
		return errorCode as TelegramLinkErrorCode;
	}

	return null;
}

export const load: PageLoad = async ({ fetch, depends, url, parent }) => {
	depends('app:social-accounts');

	const { user } = await parent();
	// Per-user key: connections are the viewer's own.
	const cacheKey = `profile-connections:${user?.id ?? 'guest'}`;

	const client = createApiClient();

	const { data, stale, cachedAt } = await fetchWithCache<ProfileConnections>({
		key: cacheKey,
		fetcher: async ({ signal }) => {
			const { data: socialAccounts } = await client.GET('/me/connections/', { fetch, signal });
			return {
				socialAccounts: socialAccounts ?? []
			};
		}
	});

	// Complete miss (errored/offline with nothing cached): hard failure.
	if (data === undefined) {
		error(503, 'Не удалось загрузить профиль');
	}

	return {
		title: 'Профиль',
		telegramLinkError: getTelegramLinkErrorCode(url),
		socialAccounts: data.socialAccounts,
		stale,
		cachedAt
	};
};
