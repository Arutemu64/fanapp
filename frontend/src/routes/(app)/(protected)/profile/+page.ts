import type { PageLoad } from './$types';

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

// Social accounts now arrive with the current user from the root layout's `/me/`
// load, so this page fetches nothing — it only reads the one-time Telegram link
// error code off the URL.
export const load: PageLoad = ({ url }) => {
	return {
		title: 'Профиль',
		telegramLinkError: getTelegramLinkErrorCode(url)
	};
};
