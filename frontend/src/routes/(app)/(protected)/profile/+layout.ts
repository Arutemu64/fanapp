import type { BackTarget } from '#lib/types/navigation.js';

import type { LayoutLoad } from './$types';

// Every settings page here returns to the /profile hub.
export const load: LayoutLoad = () => ({
	back: { href: 'profile', label: 'Назад в профиль' } satisfies BackTarget
});
