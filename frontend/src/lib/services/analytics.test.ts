import { describe, expect, it, vi } from 'vitest';

import { trackEvent, trackPageView, umamiScriptAttributes } from './analytics';

const config = {
	scriptUrl: 'https://stats.example.com/script.js',
	websiteId: 'b6f1c2d4-0000-4000-8000-000000000000',
	siteUrl: 'https://app.example.com'
};

describe('umamiScriptAttributes', () => {
	it('returns null without a script URL or website ID', () => {
		expect(umamiScriptAttributes({ ...config, scriptUrl: '' })).toBeNull();
		expect(umamiScriptAttributes({ ...config, websiteId: '' })).toBeNull();
	});

	it('limits tracking to the site host and drops query and hash', () => {
		expect(umamiScriptAttributes(config)).toEqual({
			src: config.scriptUrl,
			'data-website-id': config.websiteId,
			'data-do-not-track': 'true',
			'data-exclude-search': 'true',
			'data-exclude-hash': 'true',
			'data-domains': 'app.example.com'
		});
	});

	it('skips the domain filter when the site URL does not parse', () => {
		expect(umamiScriptAttributes({ ...config, siteUrl: '' })).not.toHaveProperty('data-domains');
	});
});

describe('trackEvent', () => {
	it('does nothing before the tracker loads', () => {
		expect(() => trackEvent('logout')).not.toThrow();
	});

	it('forwards the event and its data to Umami', () => {
		const track = vi.fn();
		vi.stubGlobal('umami', { track });

		trackEvent('login', { method: 'code' });

		expect(track).toHaveBeenCalledWith('login', { method: 'code' });
	});
});

describe('trackPageView', () => {
	it('sends the new URL without its query and hash', () => {
		const track = vi.fn();
		vi.stubGlobal('umami', { track });

		trackPageView(new URL('https://app.example.com/schedule?day=2#now'));

		const [buildPayload] = track.mock.calls[0] as [(defaults: object) => object];
		expect(buildPayload({ website: 'id', url: 'https://app.example.com/map' })).toEqual({
			website: 'id',
			url: 'https://app.example.com/schedule'
		});
	});
});
