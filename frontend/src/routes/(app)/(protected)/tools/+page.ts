import type { BackTarget } from '#lib/types/navigation.js';

import type { PageLoad } from './$types';

// The org gate lives in +layout.ts. The hub is opened from the /profile menu, so
// its way back is the profile hub, the same as the profile settings pages.
export const load: PageLoad = () => {
	return {
		title: 'Инструменты',
		back: { href: 'profile', label: 'Назад в профиль' } satisfies BackTarget
	};
};
