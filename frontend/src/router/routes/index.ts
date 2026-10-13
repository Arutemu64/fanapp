import type { RouteRecordRaw } from 'vue-router';

import { authRoutes } from './auth.js';
import { homeRoutes } from './home.js';
import { mapRoutes } from './map.js';
import { notificationsRoutes } from './notifications.js';
import { profileRoutes } from './profile.js';
import { scheduleRoutes } from './schedule.js';
import { shellRoutes } from './shell.js';
import { toolsRoutes } from './tools.js';
import { votingRoutes } from './voting.js';

// The route tree. Each area owns one file and exports plain records; the groups
// that used to be SvelteKit layout groups are composed here:
//   - `shellRoutes.appLayout` wraps the public tabs and the protected group;
//   - `shellRoutes.protectedGuard` is the component-less `(protected)` record
//     whose loader sends guests to /login;
//   - `shellRoutes.authLayout` wraps the guests-only login.
export const routes: RouteRecordRaw[] = [
	{
		...shellRoutes.authLayout,
		children: authRoutes
	},
	{
		...shellRoutes.appLayout,
		children: [
			...homeRoutes,
			...scheduleRoutes.public,
			...votingRoutes,
			...mapRoutes,
			...profileRoutes.hub,
			{
				...shellRoutes.protectedGuard,
				children: [
					...scheduleRoutes.protected,
					...notificationsRoutes,
					...profileRoutes.settings,
					...toolsRoutes
				]
			}
		]
	},
	shellRoutes.notFound
];
