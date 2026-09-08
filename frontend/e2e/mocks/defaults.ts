import type { ApiSchemas, Handlers } from './api';

import { json } from './api';

// A festival window a couple of days out, so the home countdown and before/during
// /after phase logic have real dates to run against without any test caring.
const DAY_MS = 86_400_000;
const now = Date.now();

// The boot-critical endpoints every page load hits, mocked for a logged-out
// visitor. Observed from a real build: on boot the app requests /me/, /config,
// /debug/health and /schedule/ (the SSE /events stream is handled by the
// EventSource double, so it never reaches the network). Log a user in by layering
// a persona from personas.ts over `GET /me/`.
export const baselineHandlers: Handlers = {
	// Reachability probe (reachability.ts). Must succeed or the app paints the
	// offline banner and every test fights it.
	'GET /debug/health': json<ApiSchemas['HealthCheckResponse']>({ status: 'healthy' }),
	'GET /config': json<ApiSchemas['PublicConfigDTO']>({
		festival_start: new Date(now + DAY_MS).toISOString(),
		festival_end: new Date(now + 3 * DAY_MS).toISOString()
	}),
	// Guest by default; personas.ts overrides this with a 200 user.
	'GET /me/': json({ code: 'unauthorized' }, 401),
	'GET /schedule/': json<ApiSchemas['GetScheduleOutput']>({ schedule: [] }),
	'GET /schedule/subscriptions/': json({ subscriptions: [] }),
	'GET /notifications/': json<ApiSchemas['ListUserNotificationOutput']>({ notifications: [] }),
	'GET /notifications/unread-count': json<ApiSchemas['UnreadNotificationsCountOutput']>({
		count: 0
	}),
	// Not a boot request, but the login surface fetches it on mount — and any test
	// that lands on /login (e.g. a protected route bouncing a guest) would otherwise
	// hit the loud 404 and trip the console guard. Empty = email-only login.
	'GET /auth/oauth/providers': json<ApiSchemas['OAuthProvidersResponse']>({ providers: [] })
};
