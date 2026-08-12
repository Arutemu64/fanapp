import type { components } from '$lib/api/schema';

export type PublicConfig = components['schemas']['PublicConfigDTO'];

// Shared across every viewer: config carries no per-user data, so it lives in the
// universal store — one entry serves guests and all accounts, surviving logout.
export const CONFIG_CACHE_KEY = 'public-config';

// Default used only on a complete cache miss — a first-ever visit made offline,
// before /config has ever been fetched. Once it has loaded once, its last synced
// copy is served instead, and a live response always wins over both. Mirrors the
// backend defaults (core AppSettings.DEFAULT_FESTIVAL_START, Moscow time UTC+3).
export const FALLBACK_CONFIG: PublicConfig = {
	festival_start: '2026-08-22T11:30:00+03:00',
	festival_ended: false
};
