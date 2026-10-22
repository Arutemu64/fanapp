import type { PublicConfigDto } from '#lib/api/generated/index.js';

// Default used only on a complete cache miss — a first-ever visit made offline,
// before /config has ever been fetched. Once it has loaded once, its cached copy
// is served instead, and a live response always wins over both. Mirrors the
// backend defaults (core AppSettings.DEFAULT_FESTIVAL_START / _END, Moscow time
// UTC+3).
export const FALLBACK_CONFIG: PublicConfigDto = {
	festival_start: '2027-03-13T11:30:00+03:00',
	festival_end: '2027-03-13T19:30:00+03:00',
	quest_enabled: false,
	quest_max_award: 100,
	schedule_changeover_seconds: 30
};
