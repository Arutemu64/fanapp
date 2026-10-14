import { Persisted } from './persisted.svelte';

export type ThemeMode = 'system' | 'light' | 'dark';

function parseThemeMode(raw: string): ThemeMode | undefined {
	return raw === 'light' || raw === 'dark' || raw === 'system' ? raw : undefined;
}

// Brand watermelon is the default; the rest re-point app.css's --color-primary-*
// scale via :root[data-accent]. The ids are mirrored in app.css and in the boot
// script in app.html, which sets data-accent before first paint.
export const ACCENTS = [
	{ id: 'default', label: 'Арбузный' },
	{ id: 'teal', label: 'Бирюзовый' },
	{ id: 'violet', label: 'Фиолетовый' },
	{ id: 'blue', label: 'Синий' },
	{ id: 'green', label: 'Зелёный' },
	{ id: 'orange', label: 'Оранжевый' }
] as const;

export type ThemeAccent = (typeof ACCENTS)[number]['id'];

function parseThemeAccent(raw: string): ThemeAccent | undefined {
	return ACCENTS.find((accent) => accent.id === raw)?.id;
}

// Browser-UI tints (address/status bar). The dark value is app.css's dark
// --background (oklch(0.145 0 0) = #0a0a0a); the light value is the default
// accent's --primary (watermelon pink), used only until the live --primary can be
// read. The inline boot script in app.html seeds <meta name="theme-color"> with
// the dark value before paint; keep all three in sync.
const THEME_COLOR_LIGHT = '#d61450';
const THEME_COLOR_DARK = '#0a0a0a';

function applyTheme(mode: ThemeMode, accent: ThemeAccent): void {
	const isDark =
		mode === 'dark' ||
		(mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
	document.documentElement.classList.toggle('dark', isDark);

	if (accent === 'default') delete document.documentElement.dataset.accent;
	else document.documentElement.dataset.accent = accent;

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
	// In light mode the shell wears the accent, read back from the live --primary so
	// the colour has one source (app.css) instead of a hex table here.
	const lightColor =
		getComputedStyle(document.documentElement).getPropertyValue('--primary').trim() ||
		THEME_COLOR_LIGHT;
	const meta = document.querySelector('meta[name="theme-color"]');
	if (meta) meta.setAttribute('content', isDark ? THEME_COLOR_DARK : lightColor);
}

class ThemeService {
	// Device-wide preference, persisted through safeStorage (see the singleton
	// note below for why surviving login/logout is wanted here, not a leak).
	#mode = new Persisted<ThemeMode>('theme-mode', 'system', { parse: parseThemeMode });

	#accent = new Persisted<ThemeAccent>('theme-accent', 'default', { parse: parseThemeAccent });

	get mode(): ThemeMode {
		return this.#mode.current;
	}

	get accent(): ThemeAccent {
		return this.#accent.current;
	}

	constructor() {
		applyTheme(this.#mode.current, this.#accent.current);

		window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
			if (this.#mode.current === 'system') applyTheme('system', this.#accent.current);
		});
	}

	setMode(mode: ThemeMode): void {
		this.#mode.current = mode;
		applyTheme(mode, this.#accent.current);
	}

	setAccent(accent: ThemeAccent): void {
		this.#accent.current = accent;
		applyTheme(this.#mode.current, accent);
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
