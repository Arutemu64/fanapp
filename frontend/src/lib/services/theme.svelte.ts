import { Persisted } from './persisted.svelte';

export type ThemeMode = 'system' | 'light' | 'dark';

function parseThemeMode(raw: string): ThemeMode | undefined {
	return raw === 'light' || raw === 'dark' || raw === 'system' ? raw : undefined;
}

const THEME_COLOR_LIGHT = '#ffffff';
const THEME_COLOR_DARK = '#0a0a0a';

function applyTheme(mode: ThemeMode): void {
	const isDark =
		mode === 'dark' ||
		(mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
	document.documentElement.classList.toggle('dark', isDark);

	document.documentElement.style.colorScheme = isDark ? 'dark' : 'light';

	const meta = document.querySelector('meta[name="theme-color"]');
	if (meta) meta.setAttribute('content', isDark ? THEME_COLOR_DARK : THEME_COLOR_LIGHT);
}

class ThemeService {
	readonly #mode = new Persisted<ThemeMode>('theme-mode', 'system', { parse: parseThemeMode });

	get mode(): ThemeMode {
		return this.#mode.current;
	}

	constructor() {
		applyTheme(this.#mode.current);

		window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
			if (this.#mode.current === 'system') applyTheme('system');
		});
	}

	setMode(mode: ThemeMode): void {
		this.#mode.current = mode;
		applyTheme(mode);
	}
}

let instance: ThemeService | null = null;

export function setThemeService(): ThemeService {
	instance = new ThemeService();
	return instance;
}

export function getThemeService(): ThemeService {
	instance ??= new ThemeService();
	return instance;
}
