import type { PageLoad } from './$types';
import { client } from '$lib/api';

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

export const load: PageLoad = async ({ fetch, depends, url }) => {
	depends('app:push-subscriptions');
	depends('app:social-accounts');

	const [{ data: pushSubscriptions }, { data: socialAccounts }] = await Promise.all([
		client.GET('/push', { fetch }),
		client.GET('/me/connections', { fetch })
	]);

	return {
		telegramLinkError: getTelegramLinkErrorCode(url),
		pushSubscriptions: pushSubscriptions ?? [],
		socialAccounts: socialAccounts ?? []
	};
};
