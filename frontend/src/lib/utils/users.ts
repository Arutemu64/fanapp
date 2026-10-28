import type { CurrentUserDto } from '#lib/api/generated/index.js';

import { m } from '#lib/paraglide/messages.js';

type ChannelOwner = Pick<CurrentUserDto, 'settings' | 'social_identities'>;

/** Whether a linked Telegram or VK account has its notifications on. */
export function hasMessengerNotifications(user: ChannelOwner): boolean {
	const providers = user.social_identities.map((identity) => identity.provider);
	const telegramOn = providers.includes('telegram') && user.settings.receive_telegram_notifications;
	const vkOn = providers.includes('vk') && user.settings.receive_vk_notifications;
	return telegramOn || vkOn;
}
const roleLabels: Record<string, () => string> = {
	visitor: m.role_visitor,
	participant: m.role_participant,
	volunteer: m.role_volunteer,
	organizer: m.role_organizer
};

export function getRoleLabel(role: string): string {
	return roleLabels[role]?.() || role;
}

const socialProviderLabels: Record<string, () => string> = {
	telegram: () => 'Telegram',
	vk: m.social_vk
};

export function getSocialProviderLabel(provider: string): string {
	return socialProviderLabels[provider]?.() || provider;
}

export function buildSocialProfileUrl(provider: string, id: string): string | null {
	switch (provider) {
		case 'vk':
			return `https://vk.com/id${id}`;
		case 'telegram':
			return `tg://user?id=${id}`;
		default:
			return null;
	}
}

const USERNAME_SEAM = /(?<=\p{Ll})(?=\p{Lu})|(?<=_)(?=[^_])/u;

export function splitUsernameWords(username: string): string[] {
	return username.split(USERNAME_SEAM);
}
