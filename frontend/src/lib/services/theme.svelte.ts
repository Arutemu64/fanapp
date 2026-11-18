import { readStorage, removeStorage, writeStorage } from '#lib/utils/safeStorage.js';

import { trackEvent } from './analytics';

export type ThemeMode = 'system' | 'light' | 'dark';

const THEME_MODE_KEY = 'theme-mode';
const THEME_COLOR_LIGHT = '#ffffff';
const THEME_COLOR_DARK = '#0a0a0a';

function readThemeMode(): ThemeMode {
	const stored = readStorage('local', THEME_MODE_KEY);
	return stored === 'light' || stored === 'dark' ? stored : 'system';
}

function applyTheme(mode: ThemeMode, prefersDark: boolean): void {
	const isDark = mode === 'dark' || (mode === 'system' && prefersDark);
	document.documentElement.classList.toggle('dark', isDark);

	document
		.querySelector('meta[name="color-scheme"]')
		?.setAttribute('content', mode === 'system' ? 'light dark' : mode);
	document
		.querySelector('meta[name="theme-color"]')
		?.setAttribute('content', isDark ? THEME_COLOR_DARK : THEME_COLOR_LIGHT);
}

class ThemeService {
	readonly #prefersDark: MediaQueryList;
	#mode = $state(readThemeMode());

	get mode(): ThemeMode {
		return this.#mode;
	}

	constructor() {
		this.#prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
		applyTheme(this.#mode, this.#prefersDark.matches);

		this.#prefersDark.addEventListener('change', ({ matches }) => {
			if (this.#mode === 'system') applyTheme(this.#mode, matches);
		});
		window.addEventListener('storage', ({ key }) => {
			if (key !== THEME_MODE_KEY && key !== null) return;
			const stored = readThemeMode();
			if (stored === this.#mode) return;
			this.#mode = stored;
			applyTheme(stored, this.#prefersDark.matches);
		});
	}

	setMode(mode: ThemeMode): void {
		this.#mode = mode;
		if (mode === 'system') {
			removeStorage('local', THEME_MODE_KEY);
		} else {
			writeStorage('local', THEME_MODE_KEY, mode);
		}
		applyTheme(mode, this.#prefersDark.matches);
		trackEvent('theme-change', { mode });
	}
}

let instance: ThemeService | null = null;

export function getThemeService(): ThemeService {
	instance ??= new ThemeService();
	return instance;
}
