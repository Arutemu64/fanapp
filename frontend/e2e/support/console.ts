import type { Page } from '@playwright/test';

import { expect } from '@playwright/test';

// Browser-level network noise, not an app JS error: an aborted or 404'd request —
// how the mocked tier drives offline states (`route.abort()`) and the "loud 404"
// a forgotten mock hits — makes Chromium log a resource-load error to the console.
// Tests already assert on the app's *handling* of those (the offline copy, the
// `api.unmatched` guard), so this transport noise is never what the guard watches
// for; only app-emitted errors and uncaught exceptions are.
const IGNORED_BY_DEFAULT: RegExp[] = [/Failed to load resource/i];

export interface ConsoleGuard {
	/**
	 * Permit console errors matching any of these patterns for the current test —
	 * for a spec that deliberately drives a path the app logs on. A string matches
	 * as a substring; a RegExp as a test. Keep the pattern tight so it excuses only
	 * the expected line, not every future error.
	 */
	allow(...patterns: Array<string | RegExp>): void;
}

function matches(text: string, pattern: string | RegExp): boolean {
	return typeof pattern === 'string' ? text.includes(pattern) : pattern.test(text);
}

/**
 * Collect browser console errors and uncaught exceptions for a page, and expose an
 * assertion that fails the test on any that weren't explicitly allowed. Wired as an
 * auto fixture (see fixtures.ts) so every spec is guarded without opting in.
 */
export function watchConsole(page: Page): { guard: ConsoleGuard; assertClean: () => void } {
	const collected: string[] = [];
	const allowed: Array<string | RegExp> = [];

	page.on('console', (message) => {
		if (message.type() === 'error') collected.push(message.text());
	});
	// An uncaught exception never reaches console.error, so `pageerror` is a
	// separate channel — a thrown-but-swallowed render error would slip past a
	// console-only guard.
	page.on('pageerror', (error) => collected.push(`pageerror: ${error.message}`));

	return {
		guard: {
			allow(...patterns) {
				allowed.push(...patterns);
			}
		},
		assertClean() {
			const unexpected = collected.filter(
				(text) => ![...IGNORED_BY_DEFAULT, ...allowed].some((pattern) => matches(text, pattern))
			);
			expect(unexpected, `Unexpected browser console errors:\n${unexpected.join('\n')}`).toEqual(
				[]
			);
		}
	};
}
