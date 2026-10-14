import type { BackTarget } from '#lib/types/navigation.js';

import { m } from '#lib/paraglide/messages.js';

import type { LayoutLoad } from './$types';

// Every settings page here returns to the /profile hub.
export const load: LayoutLoad = () => ({
	back: { href: 'profile', label: m.profile_back() } satisfies BackTarget
});
