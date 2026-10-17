import { m } from '#lib/paraglide/messages.js';
// The one place the role names live, so every screen says the same thing.
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

// Seams inside a username where a line may break: a lower-to-upper case change
// ("Лунный|Лис07") or the end of an underscore run ("sakura_|chan").
const USERNAME_SEAM = /(?<=\p{Ll})(?=\p{Lu})|(?<=_)(?=[^_])/u;

/**
 * Split a username at its word seams, so a narrow row can wrap the generated
 * «ЛунныйЛис07» as «Лунный» / «Лис07» instead of truncating away the digits
 * that tell two namesakes apart.
 */
export function splitUsernameWords(username: string): string[] {
	return username.split(USERNAME_SEAM);
}
