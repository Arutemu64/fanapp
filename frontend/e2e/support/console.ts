import type { Page } from '@playwright/test';

import { expect } from '@playwright/test';

export interface ConsoleGuard {
	allow: (...patterns: (string | RegExp)[]) => void;
}

function matches(text: string, pattern: string | RegExp): boolean {
	if (typeof pattern === 'string') return text.includes(pattern);
	pattern.lastIndex = 0;
	return pattern.test(text);
}

export function watchConsole(page: Page): { guard: ConsoleGuard; assertClean: () => void } {
	const collected: string[] = [];
	const allowed: (string | RegExp)[] = [];

	page.on('console', (message) => {
		if (message.type() !== 'error') return;
		const text = message.text();
		const url = message.location().url;
		if (/Failed to load resource/i.test(text) && url.includes('/api/')) return;
		collected.push(text);
	});
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
