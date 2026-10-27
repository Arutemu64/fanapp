import type { PublicConfigDto } from '#lib/api/generated/index.js';

export const FALLBACK_CONFIG: PublicConfigDto = {
	festival_start: '2027-03-13T11:30:00+03:00',
	festival_end: '2027-03-13T19:30:00+03:00',
	quest_enabled: false,
	quest_max_award: 100,
	schedule_changeover_seconds: 30
};
