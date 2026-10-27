import type { SocialProvider } from '#lib/api/generated/index.js';
import type { ThemeMode } from '#lib/services/theme.svelte.js';

// Umami custom events and their data. Names stay within Umami's 50-character limit,
// and data never carries personal details (https://docs.umami.is/docs/track-events).
interface AnalyticsEvents {
	login: { method: 'code' | 'password' };
	'login-social-start': { provider: SocialProvider };
	logout: undefined;
	'event-subscribe': undefined;
	'event-unsubscribe': undefined;
	vote: undefined;
	'vote-cancel': undefined;
	'push-enable': undefined;
	'push-disable': undefined;
	'ticket-link': undefined;
	'feedback-send': undefined;
	'pwa-install-open': undefined;
	'pwa-install': undefined;
	'theme-change': { mode: ThemeMode };
}

type AnalyticsEvent = keyof AnalyticsEvents;

type UmamiPayload = Record<string, unknown>;

interface UmamiTracker {
	track: {
		(event: string, data?: object): void;
		(payload: (defaults: UmamiPayload) => UmamiPayload): void;
	};
}

declare global {
	// Set by the tracker script; `var` is what puts it on `globalThis`.
	var umami: UmamiTracker | undefined;
}

export interface UmamiConfig {
	scriptUrl: string;
	websiteId: string;
	siteUrl: string;
}

function hostnameOf(url: string): string | null {
	try {
		return new URL(url).hostname;
	} catch {
		return null;
	}
}

// Tracker options: https://docs.umami.is/docs/tracker-configuration
export function umamiScriptAttributes(config: UmamiConfig): Record<string, string> | null {
	if (!config.scriptUrl || !config.websiteId) return null;

	const attributes: Record<string, string> = {
		src: config.scriptUrl,
		'data-website-id': config.websiteId,
		'data-do-not-track': 'true',
		// OAuth callbacks carry codes in the query and Telegram in the hash.
		'data-exclude-search': 'true',
		'data-exclude-hash': 'true'
	};
	// Keeps local and preview builds that share the DSN out of the stats.
	const domain = hostnameOf(config.siteUrl);
	if (domain) attributes['data-domains'] = domain;
	return attributes;
}

export function startAnalytics(config: UmamiConfig): void {
	const attributes = umamiScriptAttributes(config);
	if (!attributes) return;

	const script = document.createElement('script');
	script.defer = true;
	for (const [name, value] of Object.entries(attributes)) {
		script.setAttribute(name, value);
	}
	document.head.append(script);
}

// A no-op until the tracker loads, and forever when analytics is off or blocked.
export function trackEvent<E extends AnalyticsEvent>(
	...[event, data]: AnalyticsEvents[E] extends undefined ? [E] : [E, AnalyticsEvents[E]]
): void {
	globalThis.umami?.track(event, data);
}

// The tracker counts views only on pushState and replaceState, which Back and Forward skip.
// Its own URL is stale then, so pass the new one without the query and hash.
export function trackPageView(url: URL): void {
	globalThis.umami?.track((defaults) => ({ ...defaults, url: url.origin + url.pathname }));
}
