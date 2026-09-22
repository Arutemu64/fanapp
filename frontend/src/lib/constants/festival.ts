import type { PublicConfigDto } from '$lib/api/generated';

// Default used only on a complete cache miss — a first-ever visit made offline,
// before /config has ever been fetched. Once it has loaded once, the persisted
// copy is served instead, and a live response always wins over both. Mirrors the
// backend defaults (core AppSettings.DEFAULT_FESTIVAL_START / _END, Moscow time
// UTC+3).
export const FALLBACK_CONFIG: PublicConfigDto = {
	festival_start: '2026-08-22T11:30:00+03:00',
	festival_end: '2026-08-23T20:00:00+03:00'
};
