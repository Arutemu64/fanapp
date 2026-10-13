import type { RouteRecordRaw } from 'vue-router';

// Filled in with the layouts and guards when the shell is ported.
export const shellRoutes: {
	authLayout: RouteRecordRaw;
	appLayout: RouteRecordRaw;
	protectedGuard: RouteRecordRaw;
	notFound: RouteRecordRaw;
} = {
	authLayout: { path: '/login', component: { render: () => null } },
	appLayout: { path: '/', component: { render: () => null } },
	protectedGuard: { path: '', component: { render: () => null } },
	notFound: { path: '/:pathMatch(.*)*', component: { render: () => null } }
};
