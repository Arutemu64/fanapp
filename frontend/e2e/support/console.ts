import type { Page } from '@playwright/test';

import { expect } from '@playwright/test';

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
	if (typeof pattern === 'string') return text.includes(pattern);
	// A caller could hand us a global/sticky RegExp, whose lastIndex persists
	// between .test() calls and would misclassify a later error — reset it first.
	pattern.lastIndex = 0;
	return pattern.test(text);
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
		if (message.type() !== 'error') return;
		const text = message.text();
		// A resource-load failure against the mocked backend is expected noise, not an
		// app error: the API double answers 401 for a guest, a loud 404 for a route
		// nobody mocked (asserted separately via `api.unmatched`), and offline specs
		// abort `/api` reads outright. Ignore those by resource URL — but never a
		// failed *app* asset (a missing script or stylesheet is a real regression the
		// guard must still catch).
		const url = message.location()?.url ?? '';
		if (/Failed to load resource/i.test(text) && url.includes('/api/')) return;
		collected.push(text);
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
				(text) => !allowed.some((pattern) => matches(text, pattern))
			);
			expect(unexpected, `Unexpected browser console errors:\n${unexpected.join('\n')}`).toEqual(
				[]
			);
		}
	};
}
