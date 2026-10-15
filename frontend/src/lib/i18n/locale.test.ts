import { beforeEach, describe, expect, it, vi } from 'vitest';

// Each test needs a fresh Paraglide runtime and locale module: the resolved locale
// is memoised, and the setup file has already pinned this worker's copy to Russian.
async function loadLocale(options: { languages: string[]; saved?: string }) {
	vi.resetModules();
	vi.stubGlobal('navigator', { languages: options.languages });
	const setItem = vi.fn();
	vi.stubGlobal('localStorage', {
		getItem: (key: string) => (key === 'locale' ? (options.saved ?? null) : null),
		setItem,
		removeItem: vi.fn()
	});
	await import('./locale.js');
	return { ...(await import('#lib/paraglide/runtime.js')), setItem };
}

describe('locale strategy', () => {
	beforeEach(() => {
		vi.resetModules();
	});

	it('uses Russian for a Russian browser', async () => {
		const runtime = await loadLocale({ languages: ['ru-RU', 'en-US'] });
		expect(runtime.getLocale()).toBe('ru');
	});

	it('uses English for a browser without Russian', async () => {
		const runtime = await loadLocale({ languages: ['de-DE', 'fr'] });
		expect(runtime.getLocale()).toBe('en');
	});

	it('takes the first language the app has copy for', async () => {
		const runtime = await loadLocale({ languages: ['uk', 'ru', 'en'] });
		expect(runtime.getLocale()).toBe('ru');
	});

	it('lets the saved choice win over the browser language', async () => {
		const runtime = await loadLocale({ languages: ['ru-RU'], saved: 'en' });
		expect(runtime.getLocale()).toBe('en');
	});

	it('ignores a saved value that is not a locale', async () => {
		const runtime = await loadLocale({ languages: ['ru-RU'], saved: 'klingon' });
		expect(runtime.getLocale()).toBe('ru');
	});

	it('persists the choice', async () => {
		const runtime = await loadLocale({ languages: ['ru-RU'] });
		await runtime.setLocale('en', { reload: false });
		expect(runtime.setItem).toHaveBeenCalledWith('locale', 'en');
		expect(runtime.getLocale()).toBe('en');
	});
});
