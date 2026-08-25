const roleLabels: Record<string, string> = {
	visitor: 'Посетитель',
	participant: 'Участник',
	helper: 'Волонтер',
	org: 'Организатор'
};

const roleColors: Record<string, 'gray' | 'blue' | 'green' | 'yellow'> = {
	visitor: 'gray',
	participant: 'blue',
	helper: 'green',
	org: 'yellow'
};

export function getRoleLabel(role: string): string {
	return roleLabels[role] || role;
}

export function getRoleColor(role: string): 'gray' | 'blue' | 'green' | 'yellow' {
	return roleColors[role] || 'gray';
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

// Build avatar initials from a username: two name parts -> two letters,
// otherwise the first two characters. Falls back to 'П' (Профиль) when blank.
export function getAvatarInitials(username: string | null | undefined): string {
	const name = username?.trim().replace(/^@/, '');

	if (!name) {
		return 'П';
	}

	const parts = name.split(/[\s._-]+/).filter(Boolean);

	if (parts.length >= 2) {
		const firstInitial = parts[0]?.[0] ?? '';
		const secondInitial = parts[1]?.[0] ?? '';

		return `${firstInitial}${secondInitial}`.toUpperCase();
	}

	return name.slice(0, 2).toUpperCase();
}
