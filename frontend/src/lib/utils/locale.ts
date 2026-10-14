import { getLocale, type Locale } from '#lib/paraglide/runtime.js';

// BCP 47 tags for `Intl`. English is en-GB, not en-US: the venue is in Russia,
// so dates read day-first and times on the 24-hour clock, as in the Russian UI.
const INTL_LOCALES: Record<Locale, string> = {
	ru: 'ru-RU',
	en: 'en-GB'
};

// Resolved once at import. Switching language reloads the page (Paraglide's
// default `setLocale`), so the value cannot go stale within a page load and the
// module-level `Intl` formatters can share it.
export const intlLocale = INTL_LOCALES[getLocale()];
