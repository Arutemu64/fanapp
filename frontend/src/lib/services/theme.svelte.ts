import { Persisted } from './persisted.svelte';

export type ThemeMode = 'system' | 'light' | 'dark';

function parseThemeMode(raw: string): ThemeMode | undefined {
	return raw === 'light' || raw === 'dark' || raw === 'system' ? raw : undefined;
}

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

	// Declare the resolved scheme so Chromium's Auto Dark Theme (Android Chrome/Brave)
	// doesn't force-darken a light app under a dark OS. Without a color-scheme signal
	// the browser can't tell the app themes itself and darkens both the page and the
	// shell tint, ignoring the light <meta name="theme-color"> below. Resolved rather
	// than a static "light dark" because the app overrides the OS: a manual light
	// choice must stay light even on a dark OS.
	// https://developer.chrome.com/blog/auto-dark-theme
	document.documentElement.style.colorScheme = isDark ? 'dark' : 'light';

	// Drive the shell tint from the resolved theme, not the OS preference. A single
	// media-less <meta name="theme-color"> is updated here so a manual toggle that
	// overrides the system scheme (e.g. dark app on a light OS) tints the browser
	// chrome to match the app, not the OS.
	const meta = document.querySelector('meta[name="theme-color"]');
	if (meta) meta.setAttribute('content', isDark ? THEME_COLOR_DARK : THEME_COLOR_LIGHT);
}

class ThemeService {
	// Device-wide preference, persisted through safeStorage (see the singleton
	// note below for why surviving login/logout is wanted here, not a leak).
	#mode = new Persisted<ThemeMode>('theme-mode', 'system', { parse: parseThemeMode });

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
