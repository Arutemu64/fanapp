import type { components } from '$lib/api/schema';

export type PublicConfig = components['schemas']['PublicConfigDTO'];

// Shared across every viewer: config carries no per-user data, so it lives in the
// universal store — one entry serves guests and all accounts, surviving logout.
// The `-v2` suffix retires entries cached before `festival_end` replaced
// `festival_ended`: an upgraded client opening offline would otherwise read a
// legacy payload with no `festival_end`, and the hero could never reach its
// after phase. Missing the stale key falls back to FALLBACK_CONFIG instead.
export const CONFIG_CACHE_KEY = 'public-config-v2';

// Default used only on a complete cache miss — a first-ever visit made offline,
// before /config has ever been fetched. Once it has loaded once, its last synced
// copy is served instead, and a live response always wins over both. Mirrors the
// backend defaults (core AppSettings.DEFAULT_FESTIVAL_START / _END, Moscow time
// UTC+3).
export const FALLBACK_CONFIG: PublicConfig = {
	festival_start: '2026-08-22T11:30:00+03:00',
	festival_end: '2026-08-23T20:00:00+03:00'
};
