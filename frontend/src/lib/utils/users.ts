// The one place the role names live, so every screen says the same thing.
const roleLabels: Record<string, string> = {
	visitor: 'Зритель',
	participant: 'Участник',
	helper: 'Волонтёр',
	org: 'Организатор'
};

export function getRoleLabel(role: string): string {
	return roleLabels[role] || role;
}

const socialProviderLabels: Record<string, string> = {
	telegram: 'Telegram',
	vk: 'ВКонтакте'
};

export function getSocialProviderLabel(provider: string): string {
	return socialProviderLabels[provider] || provider;
}

/**
 * Build a link to an external account from its provider and native id.
 *
 * VK exposes a stable public profile at vk.com/id<N>. Telegram has no public
 * web page keyed by numeric id (t.me needs a @username we don't store), so we
 * fall back to the tg://user?id=<N> deep link, which resolves inside a Telegram
 * client. Returns null when the provider is unknown.
 */
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
