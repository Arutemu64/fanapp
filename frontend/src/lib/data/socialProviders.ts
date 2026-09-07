import type { components } from '$lib/api/schema';
import type { Component } from 'svelte';

import IconTelegram from '~icons/simple-icons/telegram';
import IconVk from '~icons/simple-icons/vk';

type SocialProvider = components['schemas']['SocialProvider'];

export interface SocialProviderPresentation {
	/** Brand name shown to users, e.g. "VK ID". All login/link copy derives from it. */
	name: string;
	/** Brand mark. */
	icon: Component;
	/** Tailwind text-colour class carrying the mark's brand colour (login buttons). */
	iconClass: string;
}

/**
 * Per-provider brand presentation, shared by the login screen and the profile's
 * account-linking card. Which providers are offered is a backend decision (see
 * `/auth/oauth/providers`); this only says how a known provider looks. Single
 * source of truth so its name, icon and brand colour can't drift between the two
 * surfaces — the user-facing sentences ("Войти через …", "Отвязать …?") are built
 * from `name` at each call site, where the surrounding copy differs.
 *
 * Keyed by every SocialProvider member, so adding one is a type error until its
 * brand is defined here.
 */
export const SOCIAL_PROVIDER_PRESENTATION: Record<SocialProvider, SocialProviderPresentation> = {
	vk: { name: 'VK ID', icon: IconVk, iconClass: 'text-[#0077FF]' },
	telegram: { name: 'Telegram', icon: IconTelegram, iconClass: 'text-[#26A5E4]' }
};
