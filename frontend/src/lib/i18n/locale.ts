import {
	defineCustomClientStrategy,
	getLocale,
	type Locale,
	locales
} from '#lib/paraglide/runtime.js';
import { readStorage, writeStorage } from '#lib/utils/safeStorage.js';

export const LOCALE_STORAGE_KEY = 'locale';

// Browser language tag → what Intl formats dates with. `en-GB`, not `en-US`: the
// venue runs on a 24-hour clock and "8 October" reads as the day-first dates the
// rest of the programme uses.
const INTL_LOCALES: Record<Locale, string> = { ru: 'ru-RU', en: 'en-GB' };

function isLocale(value: string | null | undefined): value is Locale {
	return locales.some((locale) => locale === value);
}

// The first language the browser lists that the app has copy for, else English.
// Not Paraglide's `preferredLanguage` strategy: that falls through to the base
// locale (ru) for a German or Japanese browser, but the base locale is the
// editorial source, not the default for visitors who don't read it.
function detectBrowserLocale(): Locale {
	const languages = typeof navigator === 'undefined' ? [] : navigator.languages;
	for (const tag of languages) {
		const language = tag.toLowerCase().split('-')[0];
		if (isLocale(language)) return language;
	}
	return 'en';
}

let resolved: Locale | undefined;

// A custom strategy rather than Paraglide's `localStorage` one: that reads
// `localStorage` unguarded, and in-app webviews throw on the access itself
// (safeStorage.ts). Memoised because every `m.*()` call resolves the locale.
// The saved choice always wins over the browser's language. The service worker has
// no `localStorage`, so it follows the browser's language.
defineCustomClientStrategy('custom-appLocale', {
	getLocale: () => {
		const saved = readStorage('local', LOCALE_STORAGE_KEY);
		resolved ??= isLocale(saved) ? saved : detectBrowserLocale();
		return resolved;
	},
	setLocale: (locale) => {
		resolved = isLocale(locale) ? locale : undefined;
		writeStorage('local', LOCALE_STORAGE_KEY, locale);
	}
});

/** The BCP 47 tag `Intl` formatters should use for the active UI language. */
export function intlLocale(): string {
	return INTL_LOCALES[getLocale()];
}
