import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import { MD_BREAKPOINT } from './layout';

describe('MD_BREAKPOINT', () => {
	it('matches --breakpoint-md in app.css', () => {
		const css = readFileSync(new URL('../../app.css', import.meta.url), 'utf8');
		const pinned = /--breakpoint-md:\s*([^;]+);/.exec(css)?.at(1)?.trim();
		expect(pinned).toBe(MD_BREAKPOINT);
	});
});
