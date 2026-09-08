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

/**
 * Every known provider, in display order. The login screen falls back to this when
 * it could not reach `/auth/oauth/providers` — showing all of them fails open so a
 * social-only account (whose one button is its only way in) is never hidden by a
 * network hiccup. A provider disabled on this deployment is still rejected by its
 * start endpoint, so an extra button degrades to a handled error, never a lockout.
 * Derived from the presentation record's keys so it stays complete by construction.
 */
export const ALL_SOCIAL_PROVIDERS = Object.keys(SOCIAL_PROVIDER_PRESENTATION) as SocialProvider[];
