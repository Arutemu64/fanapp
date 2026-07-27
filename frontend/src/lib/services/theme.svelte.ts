export type ThemeMode = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'theme-mode';

function applyTheme(mode: ThemeMode): void {
	const isDark =
		mode === 'dark' ||
		(mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
	document.documentElement.classList.toggle('dark', isDark);
}

class ThemeService {
	mode = $state<ThemeMode>('system');

	constructor() {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored === 'light' || stored === 'dark' || stored === 'system') {
			this.mode = stored;
		}
		applyTheme(this.mode);

		window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
			if (this.mode === 'system') applyTheme('system');
		});
	}

	setMode(mode: ThemeMode): void {
		this.mode = mode;
		localStorage.setItem(STORAGE_KEY, mode);
		applyTheme(mode);
	}
}

// Module-global singleton (the odd one out vs. the createContext-based services).
// The no-module-singletons rule exists because a module outlives navigation and
// login/logout; theme is a device-wide preference backed by localStorage, not
// user-scoped state, so surviving a session change is the wanted behaviour rather
// than a leak. Kept global so any component can read/toggle the theme without
// threading context through every layout.
let instance: ThemeService | null = null;

export function setThemeService(): ThemeService {
	instance = new ThemeService();
	return instance;
}

export function getThemeService(): ThemeService {
	if (!instance) instance = new ThemeService();
	return instance;
}
