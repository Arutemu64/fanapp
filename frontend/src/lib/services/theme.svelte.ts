import { browser } from '$app/environment';

export type ThemeMode = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'theme-mode';

function applyTheme(mode: ThemeMode): void {
	if (!browser) return;
	const isDark =
		mode === 'dark' ||
		(mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
	document.documentElement.classList.toggle('dark', isDark);
}

class ThemeService {
	mode = $state<ThemeMode>('system');

	constructor() {
		if (browser) {
			const stored = localStorage.getItem(STORAGE_KEY);
			if (stored === 'light' || stored === 'dark' || stored === 'system') {
				this.mode = stored;
			}
			applyTheme(this.mode);

			window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
				if (this.mode === 'system') applyTheme('system');
			});
		}
	}

	setMode(mode: ThemeMode): void {
		this.mode = mode;
		if (browser) {
			localStorage.setItem(STORAGE_KEY, mode);
			applyTheme(mode);
		}
	}
}

let instance: ThemeService | null = null;

export function setThemeService(): ThemeService {
	instance = new ThemeService();
	return instance;
}

export function getThemeService(): ThemeService {
	if (!instance) instance = new ThemeService();
	return instance;
}
