import { describe, expect, it } from 'vitest';

// The no-restricted-classes patterns live in the ESLint config (ADR-0030); this
// suite sits under src/ only because that is where Vitest looks.
import { RESTRICTION_GROUPS } from '../../eslint.tailwind.js';

type Group = keyof typeof RESTRICTION_GROUPS;

function restricted(group: Group, className: string): boolean {
	return RESTRICTION_GROUPS[group].some(({ pattern }) => new RegExp(pattern).test(className));
}

describe('type restrictions', () => {
	it.each([
		'sm:text-lg',
		'sm:text-base/relaxed',
		'sm:hover:text-base',
		'dark:md:text-sm',
		'@md:text-lg',
		'min-[25rem]:text-xs',
		'text-xl',
		'text-xl/8',
		'text-2xl',
		'hover:text-lg',
		'text-[13px]',
		'text-[13px]/6'
	])('rejects %s', (className) => {
		expect(restricted('type', className)).toBe(true);
	});

	it.each([
		'text-sm',
		'text-sm/6',
		'text-base',
		'text-xs',
		'text-body',
		'text-section',
		'hover:text-foreground',
		'sm:text-primary',
		'sm:text-left',
		'text-muted-foreground'
	])('allows %s', (className) => {
		expect(restricted('type', className)).toBe(false);
	});
});

describe('palette restrictions', () => {
	it.each([
		'text-red-500',
		'bg-gray-100/50',
		'dark:border-zinc-700',
		'text-[#fff]',
		'bg-[#fff]/50'
	])('rejects %s', (className) => {
		expect(restricted('palette', className)).toBe(true);
	});

	it.each(['text-primary', 'bg-primary-600', 'text-white', 'bg-muted', 'text-destructive'])(
		'allows %s',
		(className) => {
			expect(restricted('palette', className)).toBe(false);
		}
	);
});

describe('z-index restrictions', () => {
	it.each(['z-31', 'z-39', 'z-40', 'z-50', 'hover:z-100', 'z-[60]'])('rejects %s', (className) => {
		expect(restricted('zIndex', className)).toBe(true);
	});

	it.each(['z-0', 'z-10', 'z-30', '-z-10', 'z-(--z-overlay)', 'z-(--z-chrome)'])(
		'allows %s',
		(className) => {
			expect(restricted('zIndex', className)).toBe(false);
		}
	);
});
