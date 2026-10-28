import type {
	CaptchaChallengeDto,
	GetVotingStatusOutput,
	HealthCheckOutput,
	ListUserNotificationsOutput,
	OAuthProvidersOutput,
	PublicConfigDto,
	ScheduleDto,
	UnreadNotificationsCountOutput
} from '../../src/lib/api/generated/types.gen';
import type { Handlers } from './api';

import { json, problem } from './api';

const DAY_MS = 86_400_000;
const now = Date.now();

export const baselineHandlers: Handlers = {
	'GET /debug/health': json<HealthCheckOutput>({ status: 'healthy' }),
	'GET /config': json<PublicConfigDto>({
		festival_starts_at: new Date(now + DAY_MS).toISOString(),
		festival_ends_at: new Date(now + 3 * DAY_MS).toISOString(),
		quest_enabled: false,
		quest_max_award: 100,
		schedule_changeover_seconds: 30
	}),
	'GET /me': problem('USER_NOT_AUTHENTICATED', 401),
	'GET /schedule': json<ScheduleDto>({ current_event_id: null, entries: [] }),
	'GET /schedule/subscriptions': json({ subscriptions: [] }),
	'GET /voting/status': json<GetVotingStatusOutput>({
		can_vote: false,
		status: 'not_authenticated',
		voting_starts_at: null,
		voting_ends_at: null
	}),
	'GET /notifications': json<ListUserNotificationsOutput>({ next_cursor: null, notifications: [] }),
	'GET /notifications/unread-count': json<UnreadNotificationsCountOutput>({
		count: 0
	}),
	'GET /auth/oauth/providers': json<OAuthProvidersOutput>({ providers: [] }),
	'GET /auth/captcha-challenge': json<CaptchaChallengeDto>({ challenge: null })
};
