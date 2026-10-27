import type { Component } from 'svelte';

import IconTelegram from '~icons/simple-icons/telegram';
import IconVk from '~icons/simple-icons/vk';

import type { SocialProvider } from '#lib/api/generated/index.js';

export interface SocialProviderPresentation {
	name: string;
	icon: Component;
	iconClass: string;
}

export const SOCIAL_PROVIDER_PRESENTATION: Record<SocialProvider, SocialProviderPresentation> = {
	vk: { name: 'VK ID', icon: IconVk, iconClass: 'text-[#0077FF]' },
	telegram: { name: 'Telegram', icon: IconTelegram, iconClass: 'text-[#26A5E4]' }
};

export const ALL_SOCIAL_PROVIDERS = Object.keys(SOCIAL_PROVIDER_PRESENTATION) as SocialProvider[];
