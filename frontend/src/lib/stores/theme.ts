import { defineStore } from 'pinia';

import { usePersisted } from '#lib/composables/usePersisted.js';

export type ThemeMode = 'system' | 'light' | 'dark';

function parseThemeMode(raw: string): ThemeMode | undefined {
	return raw === 'light' || raw === 'dark' || raw === 'system' ? raw : undefined;
}

// Browser-UI tints (address/status bar). Must match index.html: the light value is
// the watermelon pink, the dark value app.css's dark --background
// (oklch(0.145 0 0) = #0a0a0a). The inline boot script in index.html seeds
// <meta name="theme-color"> with the same two values before paint; keep all
// three in sync.
const THEME_COLOR_LIGHT = '#d61450';
const THEME_COLOR_DARK = '#0a0a0a';

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

/**
 * Device-wide theme preference, persisted through safeStorage. Unlike user- or
 * session-scoped state it is meant to survive login/logout, and the Pinia store
 * (created once per app) holds only that persisted ref, never anything tied to a
 * session. Created on first use; the root component reads it at boot so the
 * saved theme is applied before the first screen.
 */
export const useThemeStore = defineStore('theme', () => {
	const mode = usePersisted<ThemeMode>('theme-mode', 'system', { parse: parseThemeMode });

	applyTheme(mode.value);

	window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
		if (mode.value === 'system') applyTheme('system');
	});

	function setMode(next: ThemeMode): void {
		mode.value = next;
		applyTheme(next);
	}

	return { mode, setMode };
});
