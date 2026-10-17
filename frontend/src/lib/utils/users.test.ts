import { describe, expect, it } from 'vitest';

import { buildSocialProfileUrl, getSocialProviderLabel, splitUsernameWords } from './users';

describe('buildSocialProfileUrl', () => {
	it('builds a public VK profile URL from the numeric id', () => {
		expect(buildSocialProfileUrl('vk', '12345')).toBe('https://vk.com/id12345');
	});

	it('builds a Telegram deep link from the numeric id', () => {
		expect(buildSocialProfileUrl('telegram', '987654321')).toBe('tg://user?id=987654321');
	});

	it('returns null for an unknown provider', () => {
		expect(buildSocialProfileUrl('myspace', '1')).toBeNull();
	});
});

describe('getSocialProviderLabel', () => {
	it('maps known providers to display names', () => {
		expect(getSocialProviderLabel('vk')).toBe('ВКонтакте');
		expect(getSocialProviderLabel('telegram')).toBe('Telegram');
	});

	it('falls back to the raw provider for unknown ones', () => {
		expect(getSocialProviderLabel('myspace')).toBe('myspace');
	});
});

describe('splitUsernameWords', () => {
	it('splits a generated name at its case change, keeping the digits on the noun', () => {
		expect(splitUsernameWords('ЛунныйЛис07')).toEqual(['Лунный', 'Лис07']);
	});

	it('splits after an underscore run', () => {
		expect(splitUsernameWords('sakura__chan')).toEqual(['sakura__', 'chan']);
	});

	it('leaves a name without seams whole', () => {
		expect(splitUsernameWords('ANNA2026')).toEqual(['ANNA2026']);
	});
});
