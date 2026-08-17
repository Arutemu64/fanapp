export type ThemeMode = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'theme-mode';

// Browser-UI tints (address/status bar). Must match app.html: the light value is
// the watermelon pink, the dark value the gray-900 shell background. The inline
// boot script in app.html seeds <meta name="theme-color"> with the same two
// values before paint; keep all three in sync.
const THEME_COLOR_LIGHT = '#d61450';
const THEME_COLOR_DARK = '#111827';

function applyTheme(mode: ThemeMode): void {
	const isDark =
		mode === 'dark' ||
		(mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
	document.documentElement.classList.toggle('dark', isDark);

	// Drive the shell tint from the resolved theme, not the OS preference. A single
	// media-less <meta name="theme-color"> is updated here so a manual toggle that
	// overrides the system scheme (e.g. dark app on a light OS) tints the browser
	// chrome to match the app, not the OS.
	const meta = document.querySelector('meta[name="theme-color"]');
	if (meta) meta.setAttribute('content', isDark ? THEME_COLOR_DARK : THEME_COLOR_LIGHT);
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
