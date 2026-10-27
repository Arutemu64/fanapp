import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import { cn } from './utils';

const appCss = readFileSync(new URL('../app.css', import.meta.url), 'utf8');
const textRoles = [...appCss.matchAll(/--text-([a-z0-9]+):/g)].map((match) => match[1]);

describe('cn', () => {
	it('finds the type roles in app.css', () => {
		expect(textRoles).toEqual(expect.arrayContaining(['headline', 'section', 'body']));
	});

	it.each(textRoles)('keeps text-%s beside a text colour', (role) => {
		expect(cn(`text-${role}`, 'text-foreground')).toBe(`text-${role} text-foreground`);
	});

	it.each(textRoles)('lets text-%s override a stock size', (role) => {
		expect(cn('text-sm', `text-${role}`)).toBe(`text-${role}`);
	});
});
