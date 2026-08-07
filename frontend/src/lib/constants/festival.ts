// Fallback festival start used when GET /config is unreachable (offline or a cold
// PWA load), so the home-page countdown still renders. Mirrors the backend default
// (core AppSettings.DEFAULT_FESTIVAL_START, Moscow time UTC+3) — keep the two in
// sync. Whenever the /config request succeeds, the server value wins over this.
export const FALLBACK_FESTIVAL_START = '2026-08-22T11:30:00+03:00';
